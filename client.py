#!/usr/bin/env python3

from flask import Flask, Response, render_template
import cv2
import socket
import struct
import numpy as np
from logger import Logger
from typing import List, Optional
import threading
import time
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_IP= os.getenv("CLIENT_IP") 
SERVER_IP= os.getenv("SERVER_IP") 
CLIENT_PORT= os.getenv("CLIENT_PORT") 
SERVER_PORT= os.getenv("SERVER_PORT") 

class VideoCaptureClient:
    def __init__(
        self,
        host: str = '127.0.0.1', 
        port: int = 9999,
        web_port: int = 5555,
        enable_logging: bool = True
    ):
        """
        Initialize the video streaming client.
        
        Args:
            host: Server IP address
            port: Server port
            enable_logging: Enable debug logging
        """
        self.host = host
        self.port = int(port)
        self.client_socket = None
        self.is_running = True
        self.frame_count = 0
        self.frames: List[bytes] = []  # Store encoded JPEG bytes
        self.frame_lock = threading.Lock()  # Mutex for thread-safe access
        self.latest_frame = None
        self.frame_available = threading.Event()
        self.web_port = int(web_port)
        self.connected = False
        # Setup logging
        self.logger = Logger.get_logger(__name__, enable_logging=enable_logging)
        # 
        self.app = Flask(__name__)
        self._setup_routes()
        
        # Start receiver thread
        self.receiver_thread = threading.Thread(target=self.stream, daemon=True)
        self.receiver_thread.start()
        
    def _setup_routes(self):
        # Streamming web UI
        @self.app.route("/")
        def entrypoint():
            self.logger.debug("Requested /")
            return render_template("index.html", host=self.host, port=self.port, frame_count=self.frame_count)
        
        @self.app.route("/video_feed")
        def video_feed():
            return Response(self.gen(),
                mimetype="multipart/x-mixed-replace; boundary=frame")
        
    def gen(self):
        self.logger.debug("Starting stream")
        while self.is_running:
            # ============ GET FRAME FROM QUEUE WITH MUTEX ============
            frame_data = None
            
            # Wait for a frame to be available (with timeout)
            if self.frame_available.wait(timeout=1.0):
                with self.frame_lock:
                    if len(self.frames) > 0:
                        frame_data = self.frames.pop(0)
                    
                    # Clear event if queue is empty
                    if len(self.frames) == 0:
                        self.frame_available.clear()
            # ==========================================================
            
            if frame_data is None:
                time.sleep(0.01)
                continue
            
            # Yield MJPEG frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n'
                   + frame_data + b'\r\n')

    def _connect(self) -> bool:
        """Establish a connection to the server with a single attempt."""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10.0)   # Connection timeout
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(None)   # No timeout for receiving
            self.logger.info(f"Connected to server {self.host}:{self.port}")
            self.connected = True
            return True
        except Exception as e:
            self.logger.warning(f"Connection attempt failed: {e}")
            self.connected = False
            return False

    def _reconnect(self) -> bool:
        """Try to reconnect with exponential backoff until success or stopped."""
        self.logger.info("Attempting to reconnect...")
        delay = 1
        while self.is_running:
            if self._connect():
                return True
            self.logger.warning(f"Reconnect failed, retrying in {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 30)   # Cap at 30s
        return False
    
    def read_frame(self) -> Optional[cv2.Mat]:
        """
        Read one frame from the server.
        
        Returns:
            cv2 image frame or None if error
        """
        try:
            # 1. Read frame size (4 bytes)
            size_bytes = self.client_socket.recv(4)
            if len(size_bytes) < 4:
                self.logger.warning("Connection closed or no data")
                self.connected = False
                return None
            
            frame_size = struct.unpack("!I", size_bytes)[0]
            
            # 2. Read frame data (frame_size bytes)
            frame_data = b''
            while len(frame_data) < frame_size:
                chunk = self.client_socket.recv(frame_size - len(frame_data))
                if not chunk:
                    self.logger.warning("Connection closed during frame receive")
                    self.connected = False
                    return None
                frame_data += chunk
            
            # 3. Decode the frame
            np_array = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            if frame is None:
                self.logger.warning("Failed to decode frame")
                return None
            
            return frame
            
        except socket.timeout:
            self.logger.warning("Socket timeout while receiving frame")
            return None
        except socket.error as e:
            self.logger.error(f"Socket error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None
    
    
    def send_feedback(self, message: str):
        """
        Send feedback to server (optional feature).
        
        Args:
            message: Feedback message to send
        """
        if self.client_socket:
            try:
                self.client_socket.send(message.encode())
            except:
                pass
            
    def stream(self):
        """Main receive loop – handles connection and reconnection."""
        self.logger.info("Receiver thread started")

        # Initial connection (with retries)
        while self.is_running and not self._connect():
            time.sleep(1)

        if not self.is_running:
            return

        self.logger.info("Starting video stream")

        while self.is_running:
            # Ensure we have a connection
            if not self.client_socket or not self.connected:
                self.logger.warning("Connection lost, trying to reconnect")
                if not self._reconnect():
                    time.sleep(1)
                    continue

            frame = self.read_frame()
            if frame is None:
                # Connection likely lost – mark as disconnected and retry
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                    self.client_socket = None
                    self.connected = False
                continue

            # Encode frame and add to queue
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                self.logger.error("Encode failed")
                continue

            jpeg_bytes = jpeg.tobytes()
            with self.frame_lock:
                if len(self.frames) < 10:
                    self.frames.append(jpeg_bytes)
                else:
                    self.frames.pop(0)
                    self.frames.append(jpeg_bytes)
                self.frame_available.set()

            self.frame_count += 1
            if self.frame_count % 30 == 0:
                self.logger.info(f"Received {self.frame_count} frames")

        self.logger.info("Receiver thread stopped")

    def close(self):
        """Clean up resources."""
        self.is_running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        cv2.destroyAllWindows()
        self.logger.info("Client closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Cleanup on destruction."""
        self.close()
        
    def start_web(self):
        self.logger.info(f"Starting web server at http://localhost:{self.web_port}")
        self.logger.info(f"Stream page: http://localhost:{self.web_port}/stream")
        
        try:
            self.app.run(
                host='0.0.0.0',
                port=self.web_port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            self.close()

# Main function outside the class
def main():
    """Main entry point."""
    try:
        # Create client and connect to server
        with VideoCaptureClient(
            host=SERVER_IP,  #
            port=SERVER_PORT,
            web_port=CLIENT_PORT,
            enable_logging=True
        ) as client:
            client.start_web()
    except ConnectionRefusedError:
        print("Connection refused. Is the server running?")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()