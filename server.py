#!/usr/bin/env python3

import cv2
import socket
import struct
import time
from logger import Logger
from typing import Optional, Tuple
from network_impairment import NetworkImpairment
from data_collection import DataCollection
from dotenv import load_dotenv
import os
import joblib

load_dotenv() 
SERVER_IP= os.getenv("SERVER_IP") 
SERVER_PORT= os.getenv("SERVER_PORT") 

MODEL_PATH = "data/quality_predictor.pkl"

class VideoCaptureServer:
    def __init__(
        self,
        camera_index: int = 0,
        host: str = '0.0.0.0',
        port: int = 9999,
        quality: int = 90,
        scale: float = 1.0,
        fps: int = 30,
        max_connections: int = 1,
<<<<<<< Updated upstream
        use_ml: bool = False,
        repeat: bool = True,
        enable_logging: bool = True,
        enable_impairment: bool = True,
        enable_collection: bool = True,
=======
        repeat: bool = False,
        enable_logging: bool = False,
        enable_impairment: bool = False,
        enable_collection: bool = False,
>>>>>>> Stashed changes
        output_file : str = None,
    ):
        """
        Initialize the video streaming server.
        
        Args:
            camera_index: Camera device index (0 for default)
            host: IP address to bind to
            port: Port to listen on
            quality: JPEG compression quality (1-100)
            scale: Resolution scale factor (0.1-1.0)
            fps: Target frames per second
            max_connections: Maximum client connections
            enable_logging: Enable debug logging
            repeat: Loop video
            enable_impairment: Enable network impairment
            enable_collection: Enable data collection
        """
        # Configuration
        self.host = host
        self.port = int(port)
        self.quality = quality  # ML will change this
        self.scale = scale      # ML will change this
        self.fps = fps          # ML might change this
        self.max_connections = max_connections
        self.repeat = repeat
        if enable_impairment:
            self.network_impairment = NetworkImpairment(
                enable_logging= enable_logging
            )
        if enable_collection:
            self.data_collection = DataCollection(
                output_file=output_file,
                enable_logging= enable_logging
            )
        # State
        self.is_running = False
        self.connection_count = 0
        self.frame_count = 0
        self.start_time = None
        self.is_video_file = False
        self.bytes_sent = 0
        # Setup logging
        self.logger = Logger.get_logger(__name__, enable_logging=True)
        self.logger.debug("DEBUG: Server logger initialized")
        self.client_socket = None
        self.client_address = None
        self.adaptation_interval = 30
        #
        self.use_ml = use_ml
        self.model = None
        
        if self.use_ml:
            try:
                self.model = joblib.load(MODEL_PATH)
                self.logger.info("ML model loaded successfully")
            except Exception as e:
                self.logger.warning(f"Failed to load model: {e}")
                self.use_ml = False
        # Initialize components
        try:
            self.video_capture = self._init_video(camera_index)
            self.server_socket = self._init_server()
            
            self.network_impairment = NetworkImpairment(
                loss_rate = 0.5,
                delay_ms = 100.0,
                jitter_ms = 100.0,
                enable_logging=enable_logging) if enable_impairment else None
            self.data_collection = DataCollection(enable_logging=enable_logging, output_file=output_file) if enable_collection else None
            
            self.logger.info(f"Server initialized on {host}:{port}")
            self.logger.info(f"Initial quality: {quality}, scale: {scale}, fps: {fps}")
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise
        
    
    def _init_video(self, camera_index: int) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            self.logger.error(f"Failed to open camera {camera_index}")
            # default fallback to internal video source
            cap = cv2.VideoCapture("data/video1.mp4")
            if cap.isOpened():
                self.logger.info("Video file opened successfully")
                self.is_video_file = True
                return cap
            
            # Both failed
            self.logger.error("No video source available")
            raise RuntimeError("Could not open camera or video file")
        # Get camera properties
        self.is_video_file = False
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.logger.info(f"Camera initialized: {width}x{height}")
        
        return cap
    
    def _init_server(self) -> socket.socket:
        """Initialize server socket with error handling."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Allow reuse of address (helps with quick restarts)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server.bind((self.host, self.port))
            server.listen(self.max_connections)
            server.settimeout(1.0)  # Non-blocking for graceful shutdown
        except Exception as e:
            server.close()
            raise RuntimeError(f"Failed to bind to {self.host}:{self.port} - {e}")
        
        return server
    
    def wait_for_client(self, timeout: float = None) -> bool:
        """
        Wait for a client connection.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
        
        Returns:
            bool: True if client connected, False if timeout/error
        """
        self.logger.info(f"Waiting for client connection on {self.host}:{self.port}...")
        
        try:
            if timeout:
                self.server_socket.settimeout(timeout)
            
            self.client_socket, self.client_address = self.server_socket.accept()
            self.connection_count += 1
            
            self.logger.info(f"Client connected from {self.client_address}")
            self.logger.info(f"Active connections: {self.connection_count}")
            return True
            
        except socket.timeout:
            self.logger.warning(f"Client connection timeout after {timeout}s")
            return False
        except Exception as e:
            self.logger.error(f"Client connection failed: {e}")
            return False
    
    def _get_frame(self) -> Optional[Tuple[bool, cv2.Mat]]:
        """
        Capture and process a frame.
        
        Returns:
            Tuple of (success, frame) or (False, None) on failure
        """
        ret, frame = self.video_capture.read()
        if not ret:
            if self.is_video_file and self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
            # It's a video file, rewind
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.video_capture.read()
                if ret:
                    self.logger.info("Video looped")
                    return True, frame
            self.logger.warning("Failed to capture frame")
            return False, None
        
        # Apply scaling if needed
        if self.scale != 1.0:
            h, w = frame.shape[:2]
            new_w = int(w * self.scale)
            new_h = int(h * self.scale)
            frame = cv2.resize(frame, (new_w, new_h))
        
        return True, frame
    
    def _encode_frame(self, frame: cv2.Mat) -> Optional[bytes]:
        """
        Encode frame with current quality settings.
        
        Returns:
            Encoded frame as bytes or None on failure
        """
        try:
            # Encode with JPEG compression
            encode_start = time.perf_counter()
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            ret, jpeg = cv2.imencode('.jpg', frame, encode_param)
            if not ret:
                self.logger.warning("Failed to encode frame")
                return None
            data = jpeg.tobytes()
            encode_time = (time.perf_counter() - encode_start) * 1000

            # Record encoding data if collection enabled
            if self.data_collection:
                # We'll record later when sending to include send_time and impairment
                # For now we store encode time in a temporary attribute or pass along.
                self._last_encode_time = encode_time
                self._last_frame_data = data
            return data
            
        except Exception as e:
            self.logger.error(f"Encoding failed: {e}")
            return None
    
    def _send_frame(self, data: bytes) -> bool:
        """
        Send encoded frame to client.
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Apply impairment
            dropped = False
            delayed = False
            if self.network_impairment:
                if not self.network_impairment.apply_impairment():
                    dropped = True
                    # Record dropped frame
                    if self.data_collection:
                        self.data_collection.record_frame(
                            frame_id=self.frame_count,
                            loss_rate=self.network_impairment.loss_rate,
                            delay_ms=self.network_impairment.delay_ms,
                            jitter_ms=self.network_impairment.jitter_ms,
                            quality=self.quality,
                            scale=self.scale,
                            fps=self.fps,
                            frame_size=0,
                            encode_time=self._last_encode_time if hasattr(self, '_last_encode_time') else 0,
                            send_time=0,
                            was_dropped=dropped,
                            was_delayed=delayed,
                            cumulative_frames=self.frame_count,
                            cumulative_bytes=self.bytes_sent,
                            cumulative_dropped=self.network_impairment.dropped_frames,
                            cumulative_delayed=self.network_impairment.delayed_frames
                        )
                    return True  # Continue loop

            # Send frame
            start_time = time.perf_counter()
            message_size = struct.pack("!I", len(data))
            self.client_socket.sendall(message_size + data)
            send_time = (time.perf_counter() - start_time) * 1000

            self.frame_count += 1
            self.bytes_sent += len(data)

            # Record successful frame
            if self.data_collection:
                self.data_collection.record_frame(
                    frame_id=self.frame_count,
                    loss_rate=self.network_impairment.loss_rate if self.network_impairment else 0,
                    delay_ms=self.network_impairment.delay_ms if self.network_impairment else 0,
                    jitter_ms=self.network_impairment.jitter_ms if self.network_impairment else 0,
                    quality=self.quality,
                    scale=self.scale,
                    fps=self.fps,
                    frame_size=len(data),
                    encode_time=self._last_encode_time if hasattr(self, '_last_encode_time') else 0,
                    send_time=send_time,
                    was_dropped=dropped,
                    was_delayed=delayed,
                    cumulative_frames=self.frame_count,
                    cumulative_bytes=self.bytes_sent,
                    cumulative_dropped=self.network_impairment.dropped_frames,
                    cumulative_delayed=self.network_impairment.delayed_frames
                )

            return True
            
        except socket.error as e:
            self.logger.error(f"Send failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected send error: {e}")
            return False
    
    def update_quality(self, quality: int):
        """
        Update JPEG compression quality.
        
        Args:
            quality: New quality value (1-100)
        """
        if 1 <= quality <= 100:
            self.quality = quality
            self.logger.info(f"Quality updated to {quality}")
        else:
            self.logger.warning(f"Invalid quality: {quality} (must be 1-100)")
    
    def update_scale(self, scale: float):
        """
        Update resolution scale.
        
        Args:
            scale: New scale value (0.1-1.0)
        """
        if 0.1 <= scale <= 1.0:
            self.scale = scale
            self.logger.info(f"Scale updated to {scale}")
        else:
            self.logger.warning(f"Invalid scale: {scale} (must be 0.1-1.0)")
    
    def update_fps(self, fps: int):
        """
        Update target frame rate.
        
        Args:
            fps: New FPS value (1-60)
        """
        if 1 <= fps <= 60:
            self.fps = fps
            self.logger.info(f"FPS updated to {fps}")
        else:
            self.logger.warning(f"Invalid FPS: {fps} (must be 1-60)")
    
    def stream(self, max_frames: int = None, show_preview: bool = False):
        """
        Main streaming loop.
        
        Args:
            max_frames: Maximum frames to send (None = infinite)
            show_preview: Display server-side preview
        """
        if not self.client_socket:
            self.logger.error("No client connected. Call wait_for_client() first.")
            return
        
        self.is_running = True
        self.start_time = time.time()
        self.frame_count = 0
        
        self.logger.info("Starting stream...")
        
        try:
            while self.is_running:
                # Check for max frames limit
                if not self.repeat and  max_frames and self.frame_count >= max_frames:
                    self.logger.info(f"Reached max frames: {max_frames}")
                    break
                
                # Capture frame
                success, frame = self._get_frame()
                if not success:
                    continue
                
                # Encode frame
                encoded_data = self._encode_frame(frame)
                if encoded_data is None:
                    continue
                
                # Send frame
                if not self._send_frame(encoded_data):
                    break
                
                # Update statistics
                self.frame_count += 1
                
                # Optional preview
                if show_preview:
                    cv2.imshow('Server Video Preview', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                # === ML ADAPTATION ===
                if self.frame_count % self.adaptation_interval == 0:
                    new_quality, new_scale, new_fps = self._predict_params()
                    self.logger.info(f"ML adapted: quality={new_quality}, scale={new_scale}, fps={new_fps}")
                    if new_quality != self.quality:
                        self.update_quality(new_quality)
                    if new_scale != self.scale:
                        self.update_scale(new_scale)
                    if new_fps != self.fps:
                        self.update_fps(new_fps)
                # Frame rate control
                time.sleep(1.0 / self.fps)
                
        except KeyboardInterrupt:
            self.logger.info("Stream interrupted by user")
        except Exception as e:
            self.logger.error(f"Stream error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop streaming and clean up resources."""
        self.is_running = False
        
        # Close client connection
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            self.logger.info("Client connection closed")
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
            self.logger.info("Server socket closed")
        
        # Release camera
        if self.video_capture:
            try:
                self.video_capture.release()
            except:
                pass
            self.video_capture = None
            self.logger.info("Camera released")
        
        # Close windows
        cv2.destroyAllWindows()
        
        self.logger.info("Server stopped")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def get_stats(self):
        return self.network_impairment.get_stats()

    def _predict_params(self) -> Tuple[int, float, int]:
        """
        Predict optimal quality based on current network conditions.
        Returns: quality value (1-100)
        """
        if not self.use_ml or self.model is None:
            return self.quality, self.scale, self.fps  # fallback to current quality
        
        # Get current network stats from the impairment object
        if self.network_impairment:
            loss = self.network_impairment.loss_rate
            delay = self.network_impairment.delay_ms
            jitter = self.network_impairment.jitter_ms
        else:
            # If no impairment, assume perfect network
            loss = 0.0
            delay = 0.0
            jitter = 0.0
        
        features = [[loss, delay, jitter]]
        
        try:
            pred = self.model.predict(features)[0]  # [quality, scale, fps]
            quality = max(10, min(100, int(round(pred[0]))))
            # Round scale to nearest valid value
            valid_scales = [0.25, 0.5, 0.75, 1.0]
            scale = min(valid_scales, key=lambda x: abs(x - pred[1]))
            # Round fps to nearest valid value
            valid_fps = [10, 15, 20, 30]
            fps = min(valid_fps, key=lambda x: abs(x - pred[2]))
            
            return quality, scale, fps
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return self.quality, self.scale, self.fps  # fallback

def main():
    # Create and start server
    with VideoCaptureServer(
        camera_index=0,
        host=SERVER_IP,
        port=SERVER_PORT,
        quality=80,
        scale=0.5,
        fps=30,
        repeat= False,
        enable_logging= False,
        enable_impairment= False,
        enable_collection= False,
        enable_logging=True
    ) as server:
        
        print("Waiting for client to connect...")
        if server.wait_for_client(timeout=30):
            print("Client connected! Starting stream...")
            server.stream(show_preview=False)
        else:
            print("No client connected. Exiting.")

if __name__ == "__main__":
    main()