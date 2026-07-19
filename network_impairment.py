import random
import time
from logger import Logger

class NetworkImpairment:
    def __init__(
        self,
        loss_rate: float = 0.0,
        delay_ms: float = 0.0,
        jitter_ms: float = 0.0,
        enable_logging: bool = True
    ):
        self.loss_rate = loss_rate
        self.delay_ms = delay_ms
        self.jitter_ms = jitter_ms
        self.logger = Logger.get_logger(__name__, enable_logging)
        self.dropped_frames = 0
        self.delayed_frames = 0

    def apply_impairment(self) -> bool:
        """Return True if frame should be sent, False if dropped."""
        if self.loss_rate > 0 and random.random() < self.loss_rate:
            self.dropped_frames += 1
            self.logger.debug(f"Dropped frame (total: {self.dropped_frames})")
            return False
        if self.delay_ms > 0 or self.jitter_ms > 0:
            total_delay = self.delay_ms
            if self.jitter_ms > 0:
                jitter = random.uniform(-self.jitter_ms, self.jitter_ms)
                total_delay = max(0, self.delay_ms + jitter)
            if total_delay > 0:
                self.delayed_frames += 1
                time.sleep(total_delay / 1000.0)
        return True

    def get_stats(self):
        return {
            'dropped': self.dropped_frames,
            'delayed': self.delayed_frames,
            'loss_rate': self.loss_rate,
            'delay_ms': self.delay_ms,
            'jitter_ms': self.jitter_ms
        }
