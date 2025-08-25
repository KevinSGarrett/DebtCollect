import threading
import time


class TokenBucket:
    capacity: float
    tokens: float
    rate_per_sec: float
    def __init__(self, rate_per_sec: float, capacity: int) -> None:
        # Use floats internally to allow fractional refills
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.rate_per_sec = rate_per_sec
        self.lock = threading.Lock()
        self.timestamp = time.monotonic()

    def consume(self, num_tokens: int = 1) -> None:
        while True:
            # First, try to refill and see if we can consume now
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.timestamp
                if elapsed > 0:
                    refill = elapsed * self.rate_per_sec
                    if refill > 0:
                        self.tokens = min(self.capacity, self.tokens + refill)
                        self.timestamp = now

                if self.tokens >= num_tokens:
                    self.tokens -= num_tokens
                    return

                # Not enough tokens: compute how long to wait to accumulate the deficit
                needed = num_tokens - self.tokens
                wait_time = needed / self.rate_per_sec if self.rate_per_sec > 0 else 0.0

            # Sleep outside the lock so other threads can progress/refill
            time.sleep(max(0.0, wait_time))
