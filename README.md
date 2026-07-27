# ML Adaptive Video Streaming

A real‑time adaptive video streaming system that uses machine learning to dynamically adjust video quality (bitrate, resolution, and frame rate) based on network conditions. Built with Python, OpenCV, and Flask, this system simulates network impairments and adapts the stream to maintain optimal Quality of Experience (QoE).
## Features

- Python network impairment simulation

- ML‑based adaptation – A RandomForest/ExtraTrees model predicts optimal (quality, scale, fps) based on current network conditions. Based on the paper 

- Web dashboard – Flask‑based web UI displays the live video stream with real‑time stats (frames, FPS, quality).

- Automatic reconnection – Client automatically reconnects if the server restarts or network drops.

![Architecture graph](data/arch-graph "Architecture graph")

## System Requirements

- Linux/Windows hosts
- Camera or video as fallback

## Clone and install dependencies
```
git clone https://github.com/notama958/adaptive-video-streaming.git
cd adaptive-video-streaming

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
- Create ENV

Create `.env` in the root
```
SERVER_IP=server_ip
SERVER_PORT=server_port
CLIENT_IP=client_ip
CLIENT_PORT=client_web_port
```
Ensure server and client can access each others
```
$ netstat -an | grep -E '9999|5555'
tcp        0      0 0.0.0.0:5555            0.0.0.0:*               LISTEN     
tcp        0      0 0.0.0.0:9999            0.0.0.0:*               LISTEN     
```

## Data Collection

The experiment runs as

| Sweep | Experiments |
|-------|-------------|
| Loss Sweep | 7 |
| Delay Sweep | 7 |
| Quality Sweep | 4 |
| Scale Sweep | 4 |
| FPS Sweep | 4 |
| Combined | 54 |
| **Total** | **80** |

Total: 80 × 11 = 880 seconds = ~15 minutes

Log per‑frame metrics to data/training_data.csv.


```
(.venv) $ ./experiment.py
============================================================
Training Data Collection
============================================================

Experiment 1/80

Running: loss=0%, delay=0ms, quality=60
An error occurred: [Errno 17] File exists: 'data'
2026-07-31 22:31:15,366 - server - DEBUG - DEBUG: Server logger initialized
[ WARN:0@0.087] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
[video4linux2,v4l2 @ 0x16b3f6f0] Not a video capture device.
[video4linux2,v4l2 @ 0x16b3f6f0] Not a video capture device.
[video4linux2,v4l2 @ 0x16b3f6f0] Not a
```

Client is run as in `4. Examples`

## Performance Metrics

- Frames per second (FPS) – Target vs actual.
- Bitrate – Computed from frame size and FPS.
- Drop rate – Percentage of frames dropped.
- QoE score – Weighted combination of quality, drop rate, bitrate, and latency.

## Research & Credits

This project is based on the paper:

> Benchmarking Learning‑based Bitrate Ladder Prediction Methods for Adaptive Video Streaming
Ahmed Telili, Wassim Hamidouche, Sid Ahmed Fezza, and Luce Morin (2022)

The ML component uses ExtraTrees Regressor (ranked #1) and RandomForest Regressor (ranked #2) from the benchmark.

## Train the ML Model
```
./train.py
```

- Train a multi‑output RandomForest model.
- Save the model to data/quality_predictor.pkl.

## Examples

Tested by a video file, with conditions:
camera_index=0,
host=SERVER_IP,
port=SERVER_PORT,
quality=80,
scale=0.5,
fps=30,
use_ml=False, # adjust this + MODEL_PATH : once model is ready
enable_logging=True

```
(.venv) $ ./server.py
An error occurred: [Errno 17] File exists: 'data'
2026-07-31 22:18:16,043 - data_collection - INFO - Data collection initialized: data/20260731_221816.csv
2026-07-31 22:18:16,044 - __main__ - DEBUG - DEBUG: Server logger initialized
[ WARN:0@0.089] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] Not a video capture device.
[video4linux2,v4l2 @ 0xd3b7a70] ioctl(VIDIOC_G_INPUT): Inappropriate ioctl for device
[ERROR:0@0.090] global obsensor_uvc_stream_channel.cpp:163 getStreamChannelGroup Camera index out of range
2026-07-31 22:18:16,045 - __main__ - ERROR - Failed to open camera 0
2026-07-31 22:18:16,180 - __main__ - INFO - Video file opened successfully

```
cliebthost=SERVER_IP, 
port=SERVER_PORT,
web_port=CLIENT_PORT,
enable_logging=True

```
(.venv) $ ./client.py
2026-07-31 19:18:17,420 - __main__ - INFO - Receiver thread started
2026-07-31 19:18:17,420 - __main__ - INFO - Starting web server at http://localhost:8080
2026-07-31 19:18:17,421 - __main__ - INFO - Stream page: http://localhost:8080/stream
 * Serving Flask app 'client'
 * Debug mode: off
2026-07-31 19:18:17,435 - __main__ - INFO - Connected to server 192.168.0.253:9999
2026-07-31 19:18:17,436 - __main__ - INFO - Starting video stream
WARNING: This is a development server. Do not use it in a production deployment. Use a   production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://10.0.2.15:8080

```
After that the web UI will be available at:

http://localhost:8080 (or your CLIENT_PORT)

## Licenses

MIT License