import json
from datetime import datetime

EPOCH = 1519257480


class Lease:
    def __init__(self, data: bytes):
        self.data = data
        self.created = int.from_bytes(self.data[64:68], byteorder="big")
        self.duration = int.from_bytes(self.data[68:72], byteorder="big")
        self.metadata = json.loads(self.data[72:].decode())

    @property
    def expires(self) -> datetime:
        return datetime.fromtimestamp(self.created + self.duration + EPOCH)
