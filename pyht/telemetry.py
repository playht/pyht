from __future__ import annotations

import time


def measure(operation: str, fn: callable, *args, **kwargs):
    metrics = Metrics()
    metrics.start(operation)
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        metrics.increment("error")
        metrics.append("error.reason", str(e))
        metrics.finish("error")
        raise e
    finally:
        metrics.increment("ok")
        metrics.finish("ok")


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
            "vocode-000000000000002a.on-prem.play.ht:11045"
          ],
          "text": "This is a test.  This is the second sentence."
        },
        "timers": {
          "time-to-first-audio": {
            "duration": 0.149,
            "count": 1
          },
          "tts-request": {
            "duration": 0.679,
            "count": 1
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
        print(f"Start {operation} @ {self.start_time}")
        return self

    def increment(self, counter: str, count: int = 1) -> Metrics:
        if counter not in self.counters:
            self.counters[counter] = 0
        self.counters[counter] += count
        return self

    def start_timer(self, name: str, auto_finish: bool = True) -> Metrics:
        if name not in self.timers:
            self.timers[name] = Timer(name, auto_finish)
        self.timers[name].start(time.time())
        return self

    def finish_timer(self, name: str) -> Metrics:
        if name not in self.timers:
            return self
        self.timers[name].finish(time.time())
        return self

    def append(self, key: str, value: any) -> Metrics:
        if key not in self.attributes:
            self.attributes[key] = []

        self.attributes[key].append(str(value))
        return self

    def finish_ok(self):
        self.increment("ok")
        self.finish("ok")

    def finish_error(self, reason: str):
        self.increment("error")
        self.append("error.reason", reason)
        self.finish("error")

    def finish(self, status: str):
        now = time.time()
        self.status = status
        self.end_time = now
        self.duration = now - self.start_time

        for timer in self.timers.values():
            if timer.pending() and timer.auto_finish:
                timer.finish(now)

        print(f"Finish {self.operation} @ {self.end_time} duration: {self.duration}")

    def __repr__(self):
        return repr(self.__dict__)


class Timer:
    def __init__(self, name: str, auto_finish: bool):
        self.name = name
        self.auto_finish = auto_finish

        self.depth = 0
        self.last_time = 0
        self.count = 0
        self.duration = 0

    def start(self, now: int):
        if self.depth > 0:
            self.duration += self.depth * (now - self.last_time)
        self.last_time = now
        self.depth += 1

    def finish(self, now: int):
        if self.depth < 1:
            return
        self.duration += self.depth * (now - self.last_time)
        self.last_time = now
        self.count += 1
        self.depth -= 1

    def pending(self) -> bool:
        return self.depth > 0

    def add_time(self, elapsed_time):
        self.add(elapsed_time, 1)

    def add(self, elapsed_time: int, count: int):
        self.count += count
        self.duration += elapsed_time

    def get_count(self):
        return self.count

    def get_duration(self):
        return self.duration

    def format(self):
        return f"{self.name}:{self.duration}/{self.count}"

    def __str__(self):
        return self.format()

    def __repr__(self):
        return repr({'duration': self.duration, 'count': self.count})
