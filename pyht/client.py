from __future__ import annotations

from typing import Generator, Iterable, Iterator, List, Tuple

from dataclasses import dataclass
from datetime import datetime, timedelta
import io
import queue
import threading

import grpc
from grpc import Channel, insecure_channel, secure_channel, ssl_channel_credentials

from .lease import Lease, LeaseFactory
from .protos import api_pb2, api_pb2_grpc
from .protos.api_pb2 import Format
from .utils import ensure_sentence_end, normalize, split_text, SENTENCE_END_REGEX


@dataclass
class TTSOptions:
    voice: str
    format: Format = Format.FORMAT_WAV
    sample_rate: int = 24000
    quality: str = "faster"
    speed: float = 1.0
    temperature: float | None = None
    top_p: float | None = None
    text_guidance: float | None = None
    voice_guidance: float | None = None

    def tts_params(self, text: list[str], voice_engine: str | None) -> api_pb2.TtsParams:
        quality = self.quality.lower()
        _quality = api_pb2.QUALITY_DRAFT

        if voice_engine == "PlayHT2.0" and quality != "faster":
            _quality = api_pb2.QUALITY_MEDIUM

        params = api_pb2.TtsParams(
            text=text,
            voice=self.voice,
            format=self.format,
            quality=_quality,
            sample_rate=self.sample_rate,
            speed=self.speed,
        )
        # If the hyperparams are unset, let the proto fallback to default.
        if self.temperature is not None:
            params.temperature = self.temperature
        if self.top_p is not None:
            params.top_p = self.top_p
        if self.text_guidance is not None:
            params.text_guidance = self.text_guidance
        if self.voice_guidance is not None:
            params.voice_guidance = self.voice_guidance
        return params


class Client:
    @dataclass
    class AdvancedOptions:
        api_url: str = "https://api.play.ht/api"
        grpc_addr: str | None = None
        insecure: bool = False
        auto_refresh_lease: bool = True
        on_prem_endpoint: str | None = None
        on_prem_fallback: bool = True

    def __init__(
        self,
        user_id: str,
        api_key: str,
        auto_connect: bool = True,
        advanced: "Client.AdvancedOptions | None" = None,
    ):
        assert user_id, "user_id is required"
        assert api_key, "api_key is required"

        self._advanced = advanced or self.AdvancedOptions()

        self._lease_factory = LeaseFactory(user_id, api_key, self._advanced.api_url)
        self._lease: Lease | None = None
        self._rpc: Tuple[str, Channel] | None = None
        self._fallback_rpc: Tuple[str, Channel] | None = None
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        if auto_connect:
            self.refresh_lease()

    def _schedule_refresh(self):
        assert self._lock.locked
        if self._lease is None:
            refresh_in = timedelta(minutes=4, seconds=45).total_seconds()
        else:
            refresh_in = (
                self._lease.expires - timedelta(minutes=5) - datetime.now()
            ).total_seconds()
        self._timer = threading.Timer(refresh_in, self.refresh_lease)
        self._timer.start()

    def refresh_lease(self):
        """Manually refresh credentials with Play.ht."""
        with self._lock:
            if self._lease and self._lease.expires > datetime.now() + timedelta(minutes=5):
                if self._advanced.auto_refresh_lease and self._timer is None:
                    self._schedule_refresh()
                return
            self._lease = self._lease_factory()

            grpc_addr = (
                    self._advanced.on_prem_endpoint
                    or self._advanced.grpc_addr
                    or self._lease.metadata["inference_address"]
            )
            fallback_addr = self._lease.metadata["inference_address"]

            if self._rpc and self._rpc[0] != grpc_addr:
                self._rpc[1].close()
                self._rpc = None
            if not self._rpc:
                channel = (
                    insecure_channel(grpc_addr)
                    if self._advanced.on_prem_endpoint or self._advanced.insecure
                    else secure_channel(grpc_addr, ssl_channel_credentials())
                )
                self._rpc = (grpc_addr, channel)

            if self._advanced.on_prem_endpoint and self._advanced.on_prem_fallback and grpc_addr != fallback_addr:
                if self._fallback_rpc and self._fallback_rpc[0] != fallback_addr:
                    self._fallback_rpc[1].close()
                    self._fallback_rpc = None
                if not self._fallback_rpc:
                    channel = (
                        insecure_channel(fallback_addr)
                        if self._advanced.insecure
                        else secure_channel(fallback_addr, ssl_channel_credentials())
                    )
                    self._fallback_rpc = (fallback_addr, channel)

            if self._timer:
                self._timer.cancel()

            if self._advanced.auto_refresh_lease:
                self._schedule_refresh()

    def stream_tts_input(
        self,
        text_stream: Generator[str, None, None] | Iterable[str],
        options: TTSOptions,
        voice_engine: str | None = None
    ) -> Iterable[bytes]:
        """Stream input to Play.ht via the text_stream object."""
        buffer = io.StringIO()
        for text in text_stream:
            t = text.strip()
            buffer.write(t)
            buffer.write(" ")  # normalize word spacing.
            if SENTENCE_END_REGEX.match(t) is None:
                continue
            yield from self.tts(buffer.getvalue(), options, voice_engine)
            buffer = io.StringIO()
        # If text_stream closes, send all remaining text, regardless of sentence structure.
        if buffer.tell() > 0:
            yield from self.tts(buffer.getvalue(), options, voice_engine)

    def tts(
        self,
        text: str | List[str],
        options: TTSOptions,
        voice_engine: str | None = None
    ) -> Iterable[bytes]:
        self.refresh_lease()
        with self._lock:
            assert self._lease is not None and self._rpc is not None, "No connection"
            lease_data = self._lease.data

        if isinstance(text, str):
            text = split_text(normalize(text))
        else:
            text = [normalize(x) for x in text]
        text = ensure_sentence_end(text)

        request = api_pb2.TtsRequest(params=options.tts_params(text, voice_engine), lease=lease_data)
        try:
            stub = api_pb2_grpc.TtsStub(self._rpc[1])
            response = stub.Tts(request)  # type: Iterable[api_pb2.TtsResponse]
            for item in response:
                yield item.data
        except grpc.RpcError as e:
            error_code = getattr(e, "code")()
            should_fallback = (
                    error_code is grpc.StatusCode.RESOURCE_EXHAUSTED
                    or error_code is grpc.StatusCode.UNAVAILABLE
            )
            if should_fallback and self._fallback_rpc:
                stub = api_pb2_grpc.TtsStub(self._fallback_rpc[1])
                response = stub.Tts(request)  # type: Iterable[api_pb2.TtsResponse]
                for item in response:
                    yield item.data
            else:
                raise

    def get_stream_pair(
        self,
        options: TTSOptions,
        voice_engine: str | None = None
    ) -> Tuple['_InputStream', '_OutputStream']:
        """Get a linked pair of (input, output) streams.

        These stream objects are thread-aware and safe to use in separate threads.
        """
        shared_q = queue.Queue()
        return (
            _InputStream(self, options, shared_q, voice_engine),
            _OutputStream(shared_q)
        )

    def close(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._rpc:
            self._rpc[1].close()
            self._rpc = None
        if self._fallback_rpc:
            self._fallback_rpc[1].close()
            self._fallback_rpc = None

    def __del__(self):
        self.close()


class TextStream(Iterator[str]):
    def __init__(self, q: queue.Queue | None = None):
        super().__init__()
        self._q = q or queue.Queue()

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        value = self._q.get()
        if value is None:
            raise StopIteration()
        return value

    def __call__(self, *args: str):
        for a in args:
            self._q.put(a)

    def close(self):
        self._q.put(None)


class _InputStream:
    """Input stream handler for text.

    usage:
       input_stream('send', 'multiple', 'words', 'in', 'one', 'call.')
       input_stream += 'Add another sentence to the stream.'
       input_stream.done()
    """
    def __init__(self, client: Client, options: TTSOptions, q: queue.Queue[bytes | None], voice_engine: str | None):
        self._input = TextStream()

        def listen():
            for output in client.stream_tts_input(self._input, options, voice_engine):
                q.put(output)
            q.put(None)

        self._listener = threading.Thread(None, listen, 'listen-thread')
        self._listener.start()

    def __call__(self, *args: str):
        self._input(*args)

    def __iadd__(self, input: str):
        self._input(input)

    def done(self):
        self._input.close()
        self._listener.join()


class _OutputStream(Iterator[bytes]):
    """Iterator for output audio.

    usage:
       for audio in output_stream:
           <do stuff with audio bytes>
        output_stream.close()
    """
    def __init__(self, q: queue.Queue[bytes | None]):
        self._close = threading.Event()
        self._q = q

    def __iter__(self) -> Iterator[bytes]:
        return self

    def __next__(self) -> bytes:
        while True:
            try:
                value = self._q.get(timeout=0.05)
                break
            except queue.Empty as e:
                if self._close.is_set():
                    raise StopIteration() from e
                continue
        if value is None:
            raise StopIteration()
        return value

    def close(self):
        self._close.set()
