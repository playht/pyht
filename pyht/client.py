import json
import threading
from datetime import datetime, timedelta
from typing import Iterable, Optional, Tuple

import requests
from grpc import Channel, insecure_channel, secure_channel, ssl_channel_credentials

from .lease import Lease
from .protos import api_pb2, api_pb2_grpc


class Client:
    def __init__(
        self,
        user_id: str,
        api_key: str,
        _api_url: str = "https://play.ht/api",
        _grpc_addr: Optional[str] = None,
        _insecure: bool = False,
    ):
        assert user_id, "user_id is required"
        assert api_key, "api_key is required"

        auth_header = f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
        self._api_url = _api_url
        self._api_headers = {"X-User-Id": user_id, "Authorization": auth_header}
        self._grpc_addr = _grpc_addr
        self._insecure = _insecure
        self._lease: Optional[Lease] = None
        self._rpc: Optional[Tuple[str, Channel]] = None
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def _get_lease(self) -> Lease:
        response = requests.post(f"{self._api_url}/v2/leases", headers=self._api_headers, timeout=10)
        response.raise_for_status()

        data = response.content
        lease = Lease(data)

        assert lease.expires > datetime.now(), "Got an expired lease, is your system clock correct?"

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
            refresh_in = (self._lease.expires - timedelta(minutes=5) - datetime.now()).total_seconds()
            self._timer = threading.Timer(refresh_in, self._refresh_lease)
            self._timer.start()

    def tts(self, text: str, voice: str) -> Iterable[bytes]:
        self._refresh_lease()
        assert self._lease is not None and self._rpc is not None, "No connection"
        params = api_pb2.TtsParams(
            text=[text],
            voice=voice,
            format=api_pb2.FORMAT_UNSPECIFIED,
            temperature=0.5,
            top_p=0.5,
            other=json.dumps({"diffuser": True}),
        )
        request = api_pb2.TtsRequest(params=params, lease=self._lease.data)
        stub = api_pb2_grpc.TtsStub(self._rpc[1])
        response = stub.Tts(request)  # type: Iterable[api_pb2.TtsResponse]
        for item in response:
            yield item.data

    def close(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        if self._rpc:
            self._rpc[1].close()
            self._rpc = None

    def __del__(self):
        self.close()
