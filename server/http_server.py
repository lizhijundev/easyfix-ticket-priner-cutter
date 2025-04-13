# server/http_server.py
import threading
import traceback
from werkzeug.serving import make_server

from server.http.flask_app import create_flask_app
from utils.logger import setup_logger

logger = setup_logger()

class HttpServer:
    def __init__(self, port, printer):
        try:
            self.port = port
            self.printer = printer
            self.running = False
            self.server = None
            self.server_thread = None
            self.flask_app = create_flask_app(printer)
            logger.info(f"Flask HTTP server initialized on port: {port}")
        except Exception as e:
            logger.critical(f"Failed to initialize HTTP server: {e}")
            traceback.print_exc()
            raise

    def start(self):
        """Start HTTP server"""
        try:
            if self.running:
                logger.warning("HTTP server is already running")
                return

            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            logger.info(f"Flask HTTP server started on port {self.port}")
        except Exception as e:
            logger.critical(f"Failed to start HTTP server: {e}")
            traceback.print_exc()
            self.running = False
            raise

    def _server_loop(self):
        """Server main loop"""
        try:
            # Create a multi-threaded WSGI server
            self.server = make_server('0.0.0.0', self.port, self.flask_app, threaded=True)
            
            # Set timeout to allow the stop method to interrupt the loop
            self.server.timeout = 1
            
            logger.info(f"Flask HTTP server listening on port {self.port}")
            
            # Run the server until self.running becomes False
            while self.running:
                self.server.handle_request()
                
            logger.info("Flask HTTP server main loop ended")
        except Exception as e:
            logger.critical(f"Flask HTTP server loop error: {e}")
            traceback.print_exc()
        finally:
            if hasattr(self, 'server') and self.server:
                self.server = None
                logger.info("Flask HTTP server closed")
            self.running = False

    def stop(self):
        """Stop HTTP server"""
        try:
            if not self.running:
                logger.warning("HTTP server is not running")
                return

            logger.info("Stopping HTTP server...")
            self.running = False

            # Wait for server thread to end
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(2)  # Wait up to 2 seconds

            logger.info("HTTP server stopped")
        except Exception as e:
            logger.error(f"Error stopping HTTP server: {e}")
            traceback.print_exc()

