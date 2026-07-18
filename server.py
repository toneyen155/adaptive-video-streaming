#!/usr/bin/env python3

import cv2
import socket
import struct
import time
import logging
from typing import Optional, Tuple

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
        repeat: bool = True,
        enable_logging: bool = True
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
        """
        # Configuration
        self.host = host
        self.port = port
        self.quality = quality  # ML will change this
        self.scale = scale      # ML will change this
        self.fps = fps          # ML might change this
        self.max_connections = max_connections
        self.repeat = repeat
        # State
        self.is_running = False
        self.connection_count = 0
        self.frame_count = 0
        self.start_time = None
        self.is_video_file = False
        # Setup logging
        self.logger = self._setup_logging(enable_logging)
        
        # Initialize components
        try:
            self.video_capture = self._init_video(camera_index)
            self.server_socket = self._init_server()
            self.client_socket = None
            self.client_address = None
            
            self.logger.info(f"Server initialized on {host}:{port}")
            self.logger.info(f"Initial quality: {quality}, scale: {scale}, fps: {fps}")
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise
    
    def _setup_logging(self, enable: bool) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('VideoCaptureServer')
        if enable:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        else:
            logger.setLevel(logging.WARNING)
        return logger
    
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
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            ret, jpeg = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                self.logger.warning("Failed to encode frame")
                return None
            
            return jpeg.tobytes()
            
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
            # Send frame size (4 bytes) then frame data
            # Force fixed Unsigned Int
            message_size = struct.pack("!I", len(data))
            self.client_socket.sendall(message_size + data)
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
    
    def get_stats(self) -> dict:
        """
        Get server statistics.
        
        Returns:
            Dictionary with current statistics
        """
        if self.start_time is None:
            runtime = 0
        else:
            runtime = time.time() - self.start_time
        
        return {
            'frames_sent': self.frame_count,
            'runtime': runtime,
            'fps_actual': self.frame_count / runtime if runtime > 0 else 0,
            'fps_target': self.fps,
            'quality': self.quality,
            'scale': self.scale,
            'connections': self.connection_count,
            'is_running': self.is_running,
            'client_connected': self.client_socket is not None
        }
    
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


# Usage Example:
def main():
    # Create and start server
    with VideoCaptureServer(
        camera_index=0,
        quality=80,
        scale=0.5,
        fps=30,
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