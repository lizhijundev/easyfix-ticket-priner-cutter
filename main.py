# main.py
import sys
import signal
import traceback
from PyQt6.QtWidgets import QApplication
from ui.tray import SystemTray
from printer.manager import PrinterManager
from server.socket_server import SocketServer
from server.http_server import HttpServer
from config.settings import Settings
from utils.logger import setup_logger

logger = setup_logger()

# 设置全局异常处理
def global_exception_handler(exctype, value, tb):
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Uncaught exception: {error_msg}")
    # 原始的异常处理
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler

class PrintService:
    def __init__(self):
        try:
            self.settings = Settings()
            self.printer_manager = PrinterManager()
            self.socket_server = None
            self.http_server = None
            self.tray = None
            logger.info("PrintService initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize PrintService: {e}")
            traceback.print_exc()
            raise

    def start(self):
        try:
            # 初始化打印机管理
            self.printer_manager.discover_printers()

            # 启动服务器
            self._start_servers()

            # 启动系统托盘
            self.tray = SystemTray(self)

            logger.info("Print service started")
        except Exception as e:
            logger.critical(f"Failed to start service: {e}")
            traceback.print_exc()
            raise

    def _start_servers(self):
        try:
            # 启动服务器
            socket_port = self.settings.get("socket_port", 8420)
            http_port = self.settings.get("http_port", 8520)

            # 如果服务已经在运行，先停止
            if self.socket_server:
                self.socket_server.stop()
            if self.http_server:
                self.http_server.stop()

            self.socket_server = SocketServer(socket_port, self.printer_manager)
            self.http_server = HttpServer(http_port, self.printer_manager)

            self.socket_server.start()
            self.http_server.start()

            logger.info(f"Servers started - Socket port: {socket_port}, HTTP port: {http_port}")
        except Exception as e:
            logger.critical(f"Failed to start servers: {e}")
            traceback.print_exc()
            raise

    def restart_servers(self):
        """重启服务器以应用新设置"""
        try:
            logger.info("Restarting services to apply new settings")
            self._start_servers()

            # 显示通知
            if self.tray:
                self.tray.show_notification("Services Restarted", "New settings applied")
        except Exception as e:
            logger.critical(f"Failed to restart servers: {e}")
            traceback.print_exc()

    def stop(self):
        try:
            if self.socket_server:
                self.socket_server.stop()

            if self.http_server:
                self.http_server.stop()

            logger.info("Print service stopped")

            # 显示通知
            if self.tray:
                self.tray.show_notification("Print Service Stopped", "Thank you for using Print Service")
        except Exception as e:
            logger.critical(f"Failed to stop service: {e}")
            traceback.print_exc()

    def show_settings(self):
        try:
            # 显示设置窗口
            from ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(
                self.settings,
                self.printer_manager,
                socket_server=self.socket_server,
                http_server=self.http_server
            )
            # 连接信号
            dialog.settingsChanged.connect(self.restart_servers)
            result = dialog.exec()
            logger.info(f"Settings dialog returned result: {result}")
        except Exception as e:
            logger.critical(f"Failed to show settings dialog: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # 确保关闭窗口不会退出应用

        service = PrintService()
        service.start()

        # 处理信号以便优雅关闭
        def signal_handler(sig, frame):
            logger.info(f"Received signal: {sig}")
            service.stop()
            app.quit()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Entering application main loop")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Main program exception: {e}")
        traceback.print_exc()
        sys.exit(1)
