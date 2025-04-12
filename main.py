# main.py
import sys
import signal
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer  # 添加 QTimer 用于定时任务
from ui.tray import SystemTray
from printer.manager import PrinterManager
from server.socket_server import SocketServer
from server.http_server import HttpServer
from config.settings import Settings
from utils.logger import setup_logger

# 设置日志记录
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
            self.printer_manager = PrinterManager(self.settings)  # 传递settings给PrinterManager
            self.socket_server = None
            self.http_server = None
            self.tray = None
            self.printer_discovery_timer = None  # 定时器用于定期发现打印机
            logger.info("PrintService initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize PrintService: {e}")
            traceback.print_exc()
            raise

    def start(self):
        try:
            # 初始化打印机管理
            logger.info("Starting PrintService")
            test = self.printer_manager.discover_printers()
            logger.info(test)


            # 启动服务器
            self._start_servers()

            # 启动系统托盘
            self.tray = SystemTray(self)

            self._start_printer_discovery_timer()  # 启动定时器

            logger.info("Print service started")
        except Exception as e:
            logger.critical(f"Failed to start service: {e}")
            traceback.print_exc()
            raise

    def _start_printer_discovery_timer(self):
        """启动定时器以定期发现打印机"""
        self.printer_discovery_timer = QTimer()
        self.printer_discovery_timer.timeout.connect(self.printer_manager.discover_printers)
        self.printer_discovery_timer.start(5000)  # 每5秒调用一次 discover_printers
        logger.info("Printer discovery timer started")

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
            # 停止定时器
            if self.printer_discovery_timer:
                self.printer_discovery_timer.stop()
                logger.info("Printer discovery timer stopped")

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
            # 如果设置窗口已经打开，则激活它而不是创建新的
            if hasattr(self, 'settings_dialog') and self.settings_dialog.isVisible():
                self.settings_dialog.activateWindow()
                return

            # 显示设置窗口
            from ui.settings_dialog import SettingsDialog
            self.settings_dialog = SettingsDialog(
                self.settings,
                self.printer_manager,
                socket_server=self.socket_server,
                http_server=self.http_server
            )
            # 连接信号
            self.settings_dialog.settingsChanged.connect(self.restart_servers)
            result = self.settings_dialog.exec()
            logger.info(f"Settings dialog returned result: {result}")
        except Exception as e:
            logger.critical(f"Failed to show settings dialog: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # 确保关闭窗口不会退出应用

        # 设置应用程序图标
        from PyQt6.QtGui import QIcon
        import os

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app_icon.icns")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            # logger.info(f"Application icon set from {icon_path}")
        else:
            logger.warning(f"Icon file not found at {icon_path}")

        # 在 macOS 上隐藏 Dock 图标
        if sys.platform == "darwin":
            try:
                import objc
                objc.loadBundle('Foundation', globals(), bundle_path=objc.pathForFramework('/System/Library/Frameworks/Foundation.framework'))
                NSApp = objc.lookUpClass('NSApplication').sharedApplication()
                NSApp.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory = 1
                # logger.info("Set application to accessory mode (no Dock icon)")
            except Exception as e:
                logger.warning(f"Failed to hide Dock icon: {e}")

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
