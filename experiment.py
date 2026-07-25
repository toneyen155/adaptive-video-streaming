#!/usr/bin/env python3
"""
collect_training_data.py - Automatically collect data for ML training
"""

import time
from server import VideoCaptureServer

def run_experiment(loss_rate, delay_ms, jitter_ms, quality, scale, fps=30, duration=5):
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
        enable_collection=True
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
    experiments = []
    for loss in [0, 1, 2, 5, 10, 15, 20]:          # 7 values
        for delay in [0, 10, 25, 50, 100, 200, 300]: # 7 values
            for quality in [30, 50, 70, 90]:          # 4 values
                experiments.append((loss/100.0, delay, 0, quality, 0.5))
    
    results = []
    
    for i, (loss, delay, jitter, quality, scale) in enumerate(experiments, 1):
        print(f"\nExperiment {i}/{len(experiments)}")
        stats = run_experiment(loss, delay, jitter, quality, scale)
        if stats:
            results.append({
                'loss_rate': loss * 100,  # Convert to percentage
                'delay_ms': delay,
                'jitter_ms': jitter,
                'quality': quality,
                'scale': scale
            })
        time.sleep(1)  # Cooldown between experiments
    
    print("\n" + "=" * 60)
    print(f"Completed {len(results)} experiments")
    print("=" * 60)

if __name__ == "__main__":
    collect_all()