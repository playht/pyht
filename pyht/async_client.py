from __future__ import annotations
from typing import Any, AsyncGenerator, AsyncIterable, AsyncIterator, Coroutine

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import io
import sys

from grpc.aio import Channel, Call, insecure_channel, secure_channel, UnaryStreamCall
from grpc import ssl_channel_credentials


from .client import TTSOptions
from .lease import Lease, LeaseFactory
from .protos import api_pb2, api_pb2_grpc
from .utils import ensure_sentence_end, normalize, split_text, SENTENCE_END_REGEX


TtsUnaryStream = UnaryStreamCall[api_pb2.TtsRequest, api_pb2.TtsResponse]


# asyncio.to_thread was not added until Python 3.8+, so we make our own here.
if sys.version_info >= (3, 9):
    to_thread = asyncio.to_thread
else:
    import contextvars
    import functools

    async def to_thread(func, /, *args, **kwargs):
        loop = asyncio.get_running_loop()
        ctx = contextvars.copy_context()
        func_call = functools.partial(ctx.run, func, *args, **kwargs)
        return await loop.run_in_executor(None, func_call)


class AsyncClient:
    @dataclass
    class AdvancedOptions:
        api_url: str = "https://api.play.ht/api"
        grpc_addr: str | None = None
        insecure: bool = False
        auto_refresh_lease: bool = True

    def __init__(
        self,
        user_id: str,
        api_key: str,
        auto_connect: bool = True,
        advanced: "AsyncClient.AdvancedOptions | None" = None,
    ):
        assert user_id, "user_id is required"
        assert api_key, "api_key is required"
        self._advanced = advanced or self.AdvancedOptions()

        self._lease_factory = LeaseFactory(user_id, api_key, self._advanced.api_url)
        self._lease: Lease | None = None
        self._rpc: tuple[str, Channel] | None = None
        self._lock = asyncio.Lock()
        self._stop_lease_loop = asyncio.Event()
        if self._advanced.auto_refresh_lease:
            self._lease_loop_future = asyncio.ensure_future(self._lease_loop())
        else:
            self._lease_loop_future = asyncio.Future()
            self._lease_loop_future.set_result(None)
        if auto_connect and not self._advanced.auto_refresh_lease:
            asyncio.ensure_future(self.refresh_lease())

    async def _lease_loop(self):
        refresh_time = timedelta(minutes=4, seconds=30)
        while not self._stop_lease_loop.is_set():
            await self.refresh_lease()
            await asyncio.sleep(refresh_time.total_seconds())

    async def refresh_lease(self):
        """Manually refresh credentials with Play.ht."""
        async with self._lock:
            if self._lease and self._lease.expires > datetime.now() - timedelta(minutes=5):
                # Lease is still valid for at least the next 5 minutes.
                return
            self._lease = await to_thread(self._lease_factory)
            grpc_addr = self._advanced.grpc_addr or self._lease.metadata["inference_address"]
            if self._rpc and self._rpc[0] != grpc_addr:
                await self._rpc[1].close()
                self._rpc = None
            if self._rpc is None:
                channel = (
                    insecure_channel(grpc_addr) if self._advanced.insecure
                    else secure_channel(grpc_addr, ssl_channel_credentials())
                )
                self._rpc = (grpc_addr, channel)

    async def stream_tts_input(
        self,
        text_stream: AsyncGenerator[str, None] | AsyncIterable[str],
        options: TTSOptions,
        voice_engine: str | None = None,
    ):
        """Stream input to Play.ht via the text_stream object."""
        buffer = io.StringIO()
        async for text in text_stream:
            t = text.strip()
            buffer.write(t)
            buffer.write(" ")  # normalize word spacing.
            if SENTENCE_END_REGEX.match(t) is None:
                continue
            async for data in self.tts(buffer.getvalue(), options, voice_engine):
                yield data
            buffer = io.StringIO()
        # If text_stream closes, send all remaining text, regardless of sentence structure.
        if buffer.tell() > 0:
            async for data in self.tts(buffer.getvalue(), options, voice_engine):
                yield data

    async def tts(
        self,
        text: str | list[str],
        options: TTSOptions,
        voice_engine: str | None = None,
        context: AsyncContext | None = None
    ) -> AsyncIterable[bytes]:
        await self.refresh_lease()
        async with self._lock:
            assert self._lease is not None and self._rpc is not None
            lease_data = self._lease.data

        if isinstance(text, str):
            text = split_text(normalize(text))
        else:
            text = [normalize(x) for x in text]
        text = ensure_sentence_end(text)

        quality = options.quality.lower()
        _quality = api_pb2.QUALITY_DRAFT

        if voice_engine == "PlayHT2.0" and quality != "faster":
            _quality = api_pb2.QUALITY_MEDIUM

        params = api_pb2.TtsParams(
            text=text,
            voice=options.voice,
            format=options.format,
            quality=_quality,
            temperature=options.temperature,
            top_p=options.top_p,
            sample_rate=options.sample_rate,
            speed=options.speed,
        )
        # If the guidances are unset, let the proto fallback to default.
        if options.text_guidance is not None:
            params.text_guidance = options.text_guidance
        if options.voice_guidance is not None:
            params.voice_guidance = options.voice_guidance
        request = api_pb2.TtsRequest(params=params, lease=lease_data)
        stub = api_pb2_grpc.TtsStub(self._rpc[1])
        stream: TtsUnaryStream = stub.Tts(request)
        if context is not None:
            context.assign(stream)
        async for response in stream:
            yield response.data

    def get_stream_pair(
        self,
        options: TTSOptions,
        voice_engine: str | None = None
    ) -> tuple['_InputStream', '_OutputStream']:
        """Get a linked pair of (input, output) streams.

        These stream objects ARE NOT thread-safe. Coroutines using these stream objects must
        run on the same thread.
        """
        shared_q = asyncio.Queue()
        return (
            _InputStream(self, options, shared_q, voice_engine),
            _OutputStream(shared_q)
        )

    async def close(self):
        self._stop_lease_loop.set()
        if not self._lease_loop_future.done():
            self._lease_loop_future.cancel()
        if self._rpc is not None:
            await self._rpc[1].close()
            self._rpc = None

    def __del__(self):
        try:
            asyncio.get_running_loop()
            asyncio.ensure_future(self.close())
        except RuntimeError:
            asyncio.run(self.close())


class UnaryStreamRendezvous(AsyncIterator[api_pb2.TtsResponse], Call):
    pass


class AsyncContext:
    def __init__(self):
        self._stream: asyncio.Future[TtsUnaryStream] = asyncio.Future()

    def assign(self, stream: TtsUnaryStream):
        self._stream.set_result(stream)

    def cancel(self):
        self._stream.add_done_callback(lambda s: s.result().cancel())
        if not self._stream.cancel():
            self._stream.result().cancel()

    def cancelled(self) -> bool:
        if self._stream.done():
            return self._stream.result().cancelled()
        return False

    def done(self) -> bool:
        if self._stream.done():
            return self._stream.result().done()
        return False


class TextStream(AsyncIterator[str]):
    def __init__(self, q: asyncio.Queue[str | None] | None = None):
        super().__init__()
        self._q = q or asyncio.Queue()
        self._futures = []

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
        value = await self._q.get()
        if value is None:
            raise StopAsyncIteration()
        return value

    async def __call__(self, *args: str):
        await asyncio.gather(*(self._q.put(a) for a in args))

    async def close(self):
        await self._q.put(None)


class _InputStream:
    """Input stream handler for text.

    usage:
       input_stream('send', 'multiple', 'words', 'in', 'one', 'call.')
       input_stream += 'Add another sentence to the stream.'
       input_stream.done()
    """
    def __init__(
        self,
        client: AsyncClient,
        options: TTSOptions,
        q: asyncio.Queue[bytes | None],
        voice_engine: str | None,
    ):
        self._input = TextStream()

        async def listen():
            async for output in client.stream_tts_input(self._input, options, voice_engine):
                await q.put(output)
            await q.put(None)

        self._listener = asyncio.ensure_future(listen())

    def __call__(self, *args: str) -> Coroutine[Any, Any, None]:
        return self._input(*args)

    def __iadd__(self, input: str) -> Coroutine[Any, Any, None]:
        return self._input(input)

    async def done(self):
        await self._input.close()
        await asyncio.wait_for(self._listener, 10)


class _OutputStream(AsyncIterator[bytes]):
    """Iterator for output audio.

    usage:
       for audio in output_stream:
           <do stuff with audio bytes>
        output_stream.close()
    """
    def __init__(self, q: asyncio.Queue[bytes | None]):
        self._close = asyncio.Event()
        self._q = q

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self

    async def __anext__(self) -> bytes:
        while True:
            try:
                value = await asyncio.wait_for(self._q.get(), timeout=0.05)
                break
            except asyncio.TimeoutError as e:
                if self._close.is_set():
                    raise StopAsyncIteration() from e
                continue
        if value is None:
            raise StopAsyncIteration()
        else:
            return value

    def close(self):
        self._close.set()
