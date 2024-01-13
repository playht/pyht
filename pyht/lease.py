from __future__ import annotations

from datetime import datetime
import json
import requests


EPOCH = 1519257480
DEFAULT_API_URL = "https://api.play.ht/api"
DEFAULT_GRPC_URL = "prod.turbo.play.ht:443"


class Lease:
    def __init__(self, data: bytes):
        self.data = data
        self.created = int.from_bytes(self.data[64:68], byteorder="big")
        self.duration = int.from_bytes(self.data[68:72], byteorder="big")
        self.metadata = json.loads(self.data[72:].decode())

    @classmethod
    def _get(cls, user_id: str, api_key: str, api_url: str, _retry=True) -> bytes:
        auth_header = (
            f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
        )
        api_headers = {"X-User-Id": user_id, "Authorization": auth_header}
        with requests.post(
            f"{api_url}/v2/leases",
            headers=api_headers,
            timeout=60
        ) as response:
            try:
                response.raise_for_status()
                return response.content
            except requests.HTTPError as e:
                if _retry and e.response.status_code >= 500:
                    return cls._get(user_id, api_key, api_url, _retry=False)
                raise e

    @classmethod
    def get(cls, user_id: str, api_key: str, api_url: str = DEFAULT_API_URL) -> "Lease":
        data = cls._get(user_id, api_key, api_url)
        lease = Lease(data)

        assert (
            lease.expires > datetime.now()
        ), "Got an expired lease, is your system clock correct?"

        return lease

    @property
    def expires(self) -> datetime:
        return datetime.fromtimestamp(self.created + self.duration + EPOCH)

    @property
    def grpc_addr(self) -> str | None:
        return self.metadata.get("inference_address")


class LeaseFactory:
    def __init__(self, user_id: str, api_key: str, api_url: str = DEFAULT_API_URL):
        self._user = user_id
        self._key = api_key
        self._url = api_url

    def __call__(self) -> Lease:
        return Lease.get(self._user, self._key, self._url)
