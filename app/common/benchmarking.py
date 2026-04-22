from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


def now() -> float:
    return perf_counter()


def elapsed_ms(start: float, end: float | None = None) -> float:
    finish = perf_counter() if end is None else end
    return (finish - start) * 1000.0


@dataclass
class BenchmarkReport:
    timings_ms: dict[str, float] = field(default_factory=dict)
    counters: dict[str, int | float | str] = field(default_factory=dict)

    def add_duration(self, name: str, start: float, end: float | None = None) -> float:
        duration = elapsed_ms(start, end)
        self.timings_ms[name] = duration
        return duration

    def set_duration_ms(self, name: str, duration_ms: float) -> None:
        self.timings_ms[name] = duration_ms

    def increment_duration_ms(self, name: str, duration_ms: float) -> None:
        self.timings_ms[name] = self.timings_ms.get(name, 0.0) + duration_ms

    def set_counter(self, name: str, value: int | float | str) -> None:
        self.counters[name] = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "timings_ms": {key: round(value, 3) for key, value in self.timings_ms.items()},
            "counters": self.counters,
        }
