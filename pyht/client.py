import asyncio
import concurrent.futures
import queue
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import AsyncGenerator, Iterable, Optional, Tuple

import requests
from grpc import Channel, insecure_channel, secure_channel, ssl_channel_credentials

from .lease import Lease
from .protos import api_pb2, api_pb2_grpc
from .protos.api_pb2 import Format


def threaded_sync_to_async(sync_gen, q):
    try:
        for item in sync_gen:
            q.put(item)
        q.put(StopIteration())
    except Exception as e:
        q.put(e)


async def async_generator(sync_gen):
    q = queue.Queue()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(threaded_sync_to_async, sync_gen, q)

        while True:
            item = await asyncio.to_thread(q.get)  # type: ignore[reportGeneralTypeIssues]

            if isinstance(item, StopIteration):
                return
            elif isinstance(item, Exception):
                raise item
            else:
                yield item


@dataclass
class TTSOptions:
    voice: str
    format: Format = Format.FORMAT_WAV
    sample_rate: int = 24000
    quality: str = "faster"
    temperature: float = 0.5
    top_p: float = 0.5


class Client:
    @dataclass
    class AdvancedOptions:
        api_url: str = "https://api.play.ht/api"
        grpc_addr: Optional[str] = None
        insecure: bool = False

    def __init__(
        self,
        user_id: str,
        api_key: str,
        auto_connect: bool = True,
        advanced: Optional["Client.AdvancedOptions"] = None,
    ):
        assert user_id, "user_id is required"
        assert api_key, "api_key is required"

        if advanced is None:
            advanced = Client.AdvancedOptions()

        auth_header = f"Bearer {api_key}" if not api_key.startswith(
            "Bearer ") else api_key
        self._api_url = advanced.api_url
        self._api_headers = {
            "X-User-Id": user_id,
            "Authorization": auth_header}
        self._grpc_addr = advanced.grpc_addr
        self._insecure = advanced.insecure
        self._lease: Optional[Lease] = None
        self._rpc: Optional[Tuple[str, Channel]] = None
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        if auto_connect:
            self._refresh_lease()

    def _get_lease(self) -> Lease:
        response = requests.post(
            f"{self._api_url}/v2/leases",
            headers=self._api_headers,
            timeout=10)
        response.raise_for_status()

        data = response.content
        lease = Lease(data)

        assert lease.expires > datetime.now(
        ), "Got an expired lease, is your system clock correct?"

        return lease

    def _refresh_lease(self):
        with self._lock:
            if self._lease and self._lease.expires > datetime.now() + timedelta(minutes=5):
                return
            self._lease = self._get_lease()
            grpc_addr = self._grpc_addr or self._lease.metadata["pigeon_url"]
            if self._rpc and self._rpc[0] != grpc_addr:
                self._rpc[1].close()
                self._rpc = None
            if not self._rpc:
                channel = (
                    insecure_channel(grpc_addr)
                    if self._insecure
                    else secure_channel(grpc_addr, ssl_channel_credentials())
                )
                self._rpc = (grpc_addr, channel)
            if self._timer:
                self._timer.cancel()
            refresh_in = (
                self._lease.expires -
                timedelta(
                    minutes=5) -
                datetime.now()).total_seconds()
            self._timer = threading.Timer(refresh_in, self._refresh_lease)
            self._timer.start()

    def tts(self, text: str, options: TTSOptions) -> Iterable[bytes]:
        self._refresh_lease()
        assert self._lease is not None and self._rpc is not None, "No connection"

        quality = options.quality.lower()

        # TODO: split text >350 chars into chunks on sentence boundaries

        params = api_pb2.TtsParams(
            text=[text],
            voice=options.voice,
            format=options.format,
            quality=api_pb2.QUALITY_DRAFT if quality == "faster" else api_pb2.QUALITY_MEDIUM,
            temperature=options.temperature,
            top_p=options.top_p,
            sample_rate=options.sample_rate,
        )
        request = api_pb2.TtsRequest(params=params, lease=self._lease.data)
        stub = api_pb2_grpc.TtsStub(self._rpc[1])
        response = stub.Tts(request)  # type: Iterable[api_pb2.TtsResponse]
        for item in response:
            yield item.data

    def tts_async(self, text: str,
                  options: TTSOptions) -> AsyncGenerator[bytes, None]:
        return async_generator(self.tts(text, options))

    def close(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._rpc:
            self._rpc[1].close()
            self._rpc = None

    def __del__(self):
        self.close()
