import csv
from datetime import datetime
from logger import Logger
import os

class DataCollection:
    dir : str = "data"
    def __init__(
        self,
        output_file: str = None,
        experiment_id: str = None,
        enable_logging: bool = True
    ):
        self.experiment_id = experiment_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            os.mkdir(dir)
            print(f"Directory '{self.dir}' created successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")
        self.output_file = output_file or f"{self.dir}/data_{self.experiment_id}.csv"
        self.logger = Logger.get_logger(__name__, enable_logging)
        self.buffer = []  # temporary buffer for batching
        self._init_csv()

    def _init_csv(self):
        self.fieldnames = [
            'timestamp',
            'frame_id',
            'loss_rate',
            'delay_ms',
            'jitter_ms',
            'quality',
            'scale',
            'fps',
            'frame_size_bytes',
            'encode_time_ms',
            'send_time_ms',
            'was_dropped',
            'was_delayed',
            'cumulative_frames_sent',
            'cumulative_bytes_sent',
            'cumulative_dropped',
            'cumulative_delayed'
        ]
        with open(self.output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()
        self.logger.info(f"Data collection initialized: {self.output_file}")

    def record_frame(self, **kwargs):
        """Record a single frame's data."""
        frame_id = kwargs.get('frame_id', 0)
        self.logger.debug(f"Record frame {frame_id}")
        data = {
            'timestamp': datetime.now().isoformat(),
            'frame_id': frame_id,
            'loss_rate': kwargs.get('loss_rate', 0.0) * 100,  # to percentage
            'delay_ms': kwargs.get('delay_ms', 0),
            'jitter_ms': kwargs.get('jitter_ms', 0),
            'quality': kwargs.get('quality', 0),
            'scale': kwargs.get('scale', 0),
            'fps': kwargs.get('fps', 0),
            'frame_size_bytes': kwargs.get('frame_size', 0),
            'encode_time_ms': kwargs.get('encode_time', 0),
            'send_time_ms': kwargs.get('send_time', 0),
            'was_dropped': kwargs.get('was_dropped', False),
            'was_delayed': kwargs.get('was_delayed', False),
            'cumulative_frames_sent': kwargs.get('cumulative_frames', 0),
            'cumulative_bytes_sent': kwargs.get('cumulative_bytes', 0),
            'cumulative_dropped': kwargs.get('cumulative_dropped', 0),
            'cumulative_delayed': kwargs.get('cumulative_delayed', 0)
        }
        self.buffer.append(data)
        if len(self.buffer) >= 10:
            self._flush()

    def _flush(self):
        if not self.buffer:
            return
        with open(self.output_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writerows(self.buffer)
        self.buffer.clear()

    def close(self):
        self._flush()
        self.logger.info(f"Data saved to {self.output_file}")