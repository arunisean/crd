import time
import logging
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class StatsManager:
    """A manager to collect and report operational statistics."""
    def __init__(self):
        self.counters = defaultdict(int)
        self.timings = defaultdict(lambda: {'count': 0, 'total_time': 0.0})
        self._start_time = time.time()

    def increment(self, name, count=1):
        """Increment a named counter."""
        self.counters[name] += count

    def record_time(self, name, duration):
        """Record a timing for a named operation."""
        self.timings[name]['count'] += 1
        self.timings[name]['total_time'] += duration

    @contextmanager
    def time_block(self, name):
        """A context manager to time a block of code."""
        start = time.time()
        yield
        self.record_time(name, time.time() - start)

    def report(self):
        """Print a formatted report of all collected statistics."""
        total_duration = time.time() - self._start_time
        print("\n--- CRD Pipeline Statistics ---")
        print(f"Total Execution Time: {total_duration:.2f} seconds")
        print("\nCounters:")
        for name, value in sorted(self.counters.items()):
            print(f"  - {name}: {value}")

        print("\nTimings:")
        for name, data in sorted(self.timings.items()):
            avg_time = data['total_time'] / data['count'] if data['count'] > 0 else 0
            print(f"  - {name}: {data['count']} calls, {data['total_time']:.2f}s total, {avg_time:.2f}s avg")
        print("-----------------------------\n")