from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, AsyncIterable, AsyncIterator, Coroutine

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import io
import os
import sys
import tempfile

import filelock
import grpc
from grpc.aio import Channel, Call, insecure_channel, secure_channel, UnaryStreamCall
from grpc import ssl_channel_credentials, StatusCode


from .client import TTSOptions, CongestionCtrl, CLIENT_RETRY_OPTIONS
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
    LEASE_DATA: bytes | None = None
    LEASE_CACHE_PATH: str = os.path.join(tempfile.gettempdir(), 'playht.temporary.lease')
    LEASE_LOCK = asyncio.Lock()

    @dataclass
    class AdvancedOptions:
        api_url: str = "https://api.play.ht/api"
        grpc_addr: str | None = None
        insecure: bool = False
        fallback_enabled: bool = False
        auto_refresh_lease: bool = True
        disable_lease_disk_cache: bool = False
        congestion_ctrl: CongestionCtrl = CongestionCtrl.OFF

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

        async def lease_factory() -> Lease:
            _factory = LeaseFactory(user_id, api_key, self._advanced.api_url)
            if self._advanced.disable_lease_disk_cache:
                return await asyncio.to_thread(_factory)
            maybe_data = await self._lease_cache_read()
            if maybe_data is not None:
                lease = Lease(maybe_data)
                if lease.expires > datetime.now() + timedelta(minutes=5):
                    return lease
            lease = await asyncio.to_thread(_factory)
            await self._lease_cache_write(lease.data)
            return lease

        self._lease_factory = lease_factory
        self._lease: Lease | None = None
        self._rpc: tuple[str, Channel] | None = None
        self._fallback_rpc: tuple[str, Channel] | None = None
        self._lock = asyncio.Lock()
        self._stop_lease_loop = asyncio.Event()
        if self._advanced.auto_refresh_lease:
            self._lease_loop_future = asyncio.ensure_future(self._lease_loop())
        else:
            self._lease_loop_future = asyncio.Future()
            self._lease_loop_future.set_result(None)
        if auto_connect and not self._advanced.auto_refresh_lease:
            asyncio.ensure_future(self.refresh_lease())

    @classmethod
    async def _lease_cache_read(cls) -> bytes | None:
        def get_file():
            try:
                with filelock.FileLock(cls.LEASE_CACHE_PATH + '.lock'):
                    if not os.path.exists(cls.LEASE_CACHE_PATH):
                        return None
                    with open(cls.LEASE_CACHE_PATH, 'rb') as fp:
                        return fp.read()
            except IOError:
                return None

        async with cls.LEASE_LOCK:
            if cls.LEASE_DATA is None:
                cls.LEASE_DATA = await asyncio.to_thread(get_file)
            return cls.LEASE_DATA

    @classmethod
    async def _lease_cache_write(cls, data: bytes):
        def write_file():
            try:
                with filelock.FileLock(cls.LEASE_CACHE_PATH + '.lock'):
                    with open(cls.LEASE_CACHE_PATH, 'wb') as fp:
                        fp.write(data)
            except IOError:
                return

        async with cls.LEASE_LOCK:
            cls.LEASE_DATA = data
            await asyncio.to_thread(write_file)

    async def _lease_loop(self):
        refresh_time = timedelta(minutes=4, seconds=30)
        while not self._stop_lease_loop.is_set():
            await self.refresh_lease()
            await asyncio.sleep(refresh_time.total_seconds())

    async def refresh_lease(self):
        """Manually refresh credentials with Play.ht."""
        async with self._lock:
            if self._lease and self._lease.expires > datetime.now() + timedelta(minutes=5):
                # Lease is still valid for at least the next 5 minutes.
                return
            self._lease = await self._lease_factory()

            grpc_addr = self._advanced.grpc_addr or self._lease.metadata["inference_address"]

            if self._rpc and self._rpc[0] != grpc_addr:
                await self._rpc[1].close()
                self._rpc = None
            if self._rpc is None:
                insecure = self._advanced.insecure or "on-prem.play.ht" in grpc_addr
                channel = (
                    insecure_channel(grpc_addr, options=CLIENT_RETRY_OPTIONS) if insecure
                    else secure_channel(grpc_addr, ssl_channel_credentials(), options=CLIENT_RETRY_OPTIONS)
                )
                self._rpc = (grpc_addr, channel)

            # Maybe set up a fallback grpc client
            if self._advanced.fallback_enabled:
                # Choose the fallback address
                # For now, this always is the inference address in the lease, but we can extend in the future
                fallback_addr = self._lease.metadata["inference_address"]

                # Only do fallback if the fallback address is not the same as the primary address
                if grpc_addr != fallback_addr:
                    if self._fallback_rpc and self._fallback_rpc[0] != fallback_addr:
                        await self._fallback_rpc[1].close()
                        self._fallback_rpc = None
                    if self._fallback_rpc is None:
                        channel = (
                            insecure_channel(fallback_addr, options=CLIENT_RETRY_OPTIONS) if self._advanced.insecure
                            else secure_channel(fallback_addr, ssl_channel_credentials(), options=CLIENT_RETRY_OPTIONS)
                        )
                        self._fallback_rpc = (fallback_addr, channel)

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

        request = api_pb2.TtsRequest(params=options.tts_params(text, voice_engine), lease=lease_data)

        max_attempts = 1
        backoff = 0
        if self._advanced.congestion_ctrl == CongestionCtrl.STATIC_MAR_2023:
            max_attempts = 3
            backoff = 0.05

        for attempt in range(1, max_attempts + 1):
            try:
                stub = api_pb2_grpc.TtsStub(self._rpc[1])
                stream: TtsUnaryStream = stub.Tts(request)
                if context is not None:
                    context.assign(stream)
                async for response in stream:
                    yield response.data
                break
            except grpc.RpcError as e:
                error_code = getattr(e, "code")()
                logging.debug(f"Error: {error_code}")
                if error_code not in {StatusCode.RESOURCE_EXHAUSTED, StatusCode.UNAVAILABLE}:
                    raise

                if attempt < max_attempts:
                    logging.debug(f"Retrying in {backoff * 1000} sec ({attempt} attempts so far)... ({error_code})")
                    if backoff > 0:
                        await asyncio.sleep(backoff)
                    continue

                if self._fallback_rpc is None:
                    raise

                logging.info(f"Falling back to {self._fallback_rpc[0]} because {self._rpc[0]} threw: {error_code}")
                try:
                    stub = api_pb2_grpc.TtsStub(self._fallback_rpc[1])
                    stream: TtsUnaryStream = stub.Tts(request)
                    if context is not None:
                        context.assign(stream)
                    async for response in stream:
                        yield response.data
                    break
                except grpc.RpcError as fallback_e:
                    raise fallback_e from e

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
        if self._fallback_rpc is not None:
            await self._fallback_rpc[1].close()
            self._fallback_rpc = None

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
