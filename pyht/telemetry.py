from __future__ import annotations

import time


class Telemetry:
    def __init__(self, buffer_size: int = 1000):
        self._metrics = []
        self._buffer_size = buffer_size

    def start(self, operation: str) -> Metrics:
        metrics = Metrics()
        metrics.start(operation)
        if len(self._metrics) >= self._buffer_size:
            self._metrics.pop(0)
        self._metrics.append(metrics)
        return metrics

    def metrics(self) -> list[Metrics]:
        return self._metrics


class Metrics:
    """
      {
        "operation": "tts-request",
        "status": "ok",
        "startTime": 1712937515393,
        "endTime": 1712937515442,
        "duration": 0.679,
        "counters": {
          "chunk": 10,
          "ok": 1,
          "error": 0
        },
        "attributes": {
          "endpoint": [
            "test-0000000000000001.on-prem.play.ht:11045"
          ],
          "text": "This is a test.  This is the second sentence."
        },
        "timers": {
          "time-to-first-audio": {
            "duration": 0.149
          },
          "tts-request": {
            "duration": 0.679
          }
        }
      }
    """

    def __init__(self):
        self.operation = None
        self.status = None
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.counters = {}
        self.attributes = {}
        self.timers = {}

    def start(self, operation: str) -> Metrics:
        self.operation = operation
        self.start_time = time.time()
        self.start_timer(operation)
        return self

    def inc(self, counter: str, count: int = 1) -> Metrics:
        self.counters[counter] = self.counters.get(counter, 0) + count
        return self

    def start_timer(self, name: str) -> Metrics:
        timer = self.timers.setdefault(name, Timer(name))
        timer.start()
        return self

    def finish_timer(self, name: str) -> Metrics:
        timer = self.timers.get(name)
        if timer is None:
            raise ValueError(f"Timer not started: {name}.")
        timer.finish()
        return self

    def set_timer(self, name: str, duration: float) -> Metrics:
        self.timers[name] = Timer(name, duration)
        return self

    def append(self, key: str, value: str) -> Metrics:
        self.attributes.setdefault(key, []).append(value)
        return self

    def finish_ok(self):
        self.inc("ok")
        self.finish("ok")

    def finish_error(self, reason: str):
        self.inc("error")
        self.append("error.reason", reason)
        self.finish("error")

    def finish(self, status: str):
        now = time.time()
        self.status = status
        if self.start_time is None:
            self.start_time = now
        self.end_time = now
        self.duration = now - self.start_time

        # finish all timers - finishing is idempotent so it's okay if a timer was finished before
        for timer in self.timers.values():
            timer.finish()

    def __repr__(self):
        return repr(self.__dict__)


class Timer:
    def __init__(self, name: str, duration: float = 0):
        self.name = name
        self.last_start = None
        self.duration = duration

    def start(self):
        self.last_start = time.perf_counter()

    def add(self, duration: float):
        self.duration += duration

    def finish(self):
        if self.last_start is None:
            return
        self.duration += (time.perf_counter() - self.last_start)
        self.last_start = None

    def format(self) -> str:
        return f"{self.name}:{self.duration}"

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return repr({'duration': self.duration})
