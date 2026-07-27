#!/usr/bin/env python3
"""
collect_training_data.py - Automatically collect data for ML training
"""

import time
from server import VideoCaptureServer

def run_experiment(loss_rate, delay_ms, jitter_ms, quality, scale, fps=30, duration=10):
    """Run one experiment with given parameters."""
    print(f"\n Running: loss={loss_rate*100}%, delay={delay_ms}ms, quality={quality}")
    
    # Create server with specific impairment settings
    server = VideoCaptureServer(
        camera_index=0,
        quality=quality,
        scale=scale,
        fps=fps,
        output_file="training_data",
        repeat=False,
        enable_logging=False, 
        enable_impairment=True,
        enable_collection=True,
        use_ml=False
    )
    
    # Override impairment settings
    if server.network_impairment:
        server.network_impairment.loss_rate = loss_rate
        server.network_impairment.delay_ms = delay_ms
        server.network_impairment.jitter_ms = jitter_ms
    
    # Wait for client
    if not server.wait_for_client(timeout=30):
        server.stop()
        return None
    
    # Stream for duration
    print(f"Streaming for {duration} seconds...")
    server.stream(max_frames=duration * fps)
    
    # Get stats
    stats = server.get_stats()
    server.stop()
    
    return stats

def collect_all():
    """Run all experiments."""
    print("=" * 60)
    print("Training Data Collection")
    print("=" * 60)
    
    # Define experiment parameters
    # Define experiment parameters
    experiments = []
    
    # Loss sweep (with fixed quality, scale, fps)
    for loss in [0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]:
        experiments.append((loss, 0, 0, 60, 0.5, 30))

    # Delay sweep (fixed quality, scale, fps)
    for delay in [0, 10, 25, 50, 100, 200, 300]:
        experiments.append((0.0, delay, 0, 60, 0.5, 30))

    # Quality sweep (fixed loss, delay, scale, fps)
    for quality in [30, 50, 70, 90]:
        experiments.append((0.05, 100, 0, quality, 0.5, 30))

    # Scale sweep (fixed loss, delay, quality, fps)
    for scale in [0.25, 0.5, 0.75, 1.0]:
        experiments.append((0.05, 100, 0, 60, scale, 30))

    # FPS sweep (fixed loss, delay, quality, scale)
    for fps in [10, 15, 20, 30]:
        experiments.append((0.05, 100, 0, 60, 0.5, fps))

    # Combined conditions (loss + delay + different scale/fps)
    for loss in [0.01, 0.05, 0.10]:
        for delay in [50, 100, 200]:
            for scale in [0.5, 1.0]:
                for quality in [50, 70, 90]:
                    experiments.append((loss, delay, 0, quality, scale, 30))
    
    results = []
    
    for i, (loss, delay, jitter, quality, scale,fps) in enumerate(experiments, 1):
        print(f"\nExperiment {i}/{len(experiments)}")
        stats = run_experiment(loss, delay, jitter, quality, scale, fps)
        if stats:
            results.append({
                'loss_rate': loss * 100,  # Convert to percentage
                'delay_ms': delay,
                'jitter_ms': jitter,
                'quality': quality,
                'scale': scale,
                'fps': fps
            })
        time.sleep(1)  # Cooldown between experiments
    
    print("\n" + "=" * 60)
    print(f"Completed {len(results)} experiments")
    print("=" * 60)

if __name__ == "__main__":
    collect_all()