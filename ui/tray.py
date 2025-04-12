# ui/tray.py
import sys
import os
import platform
import traceback
from PyQt6 import QtWidgets, QtGui
from utils.logger import setup_logger
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction


logger = setup_logger()

class SystemTray(QSystemTrayIcon):
    @staticmethod
    def create_application():
        try:
            app = QtWidgets.QApplication(sys.argv)
            app.setQuitOnLastWindowClosed(False)  # 确保关闭窗口不会退出应用
            return app
        except Exception as e:
            logger.critical(f"Failed to create application instance: {e}")
            traceback.print_exc()
            raise

    def __init__(self, service):
        try:
            super().__init__()
            self.service = service
            self.app = QtWidgets.QApplication.instance()

            # 创建系统托盘图标
            self.tray_icon = QtWidgets.QSystemTrayIcon()

            # 尝试加载图标文件，如果失败则使用系统默认图标
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app_icon.icns")
            # logger.info(f"Attempting to load icon: {icon_path}")

            if os.path.exists(icon_path):
                icon = QtGui.QIcon(icon_path)
            else:
                # 使用系统默认图标
                icon = QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon)

            self.tray_icon.setIcon(icon)
            self.tray_icon.setToolTip("Easyfix Printer Service")

            # 创建托盘菜单
            tray_menu = QtWidgets.QMenu()

            settings_action = tray_menu.addAction("Service Settings")
            settings_action.triggered.connect(self._show_settings)

            # 添加手动切纸选项
            cut_paper_action = tray_menu.addAction("Receipt Printer Paper Cut")
            cut_paper_action.triggered.connect(self._manual_paper_cut)

            # 添加分隔符
            tray_menu.addSeparator()

            exit_action = tray_menu.addAction("Exit")
            exit_action.triggered.connect(self.exit_app)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()

            # logger.info("System tray icon initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize system tray: {e}")
            traceback.print_exc()
            raise

    def _manual_paper_cut(self):
        """手动切纸功能"""
        try:
            logger.info("Manual paper cut requested from tray menu")
            success, message = self.service.printer_manager.manual_cut_receipt()
            if success:
                self.show_notification("Paper Cut", message)
            else:
                QtWidgets.QMessageBox.warning(None, "Warning", message)
        except Exception as e:
            logger.error(f"Error during manual paper cut: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                None,
                "Error",
                f"Failed to cut paper: {str(e)}"
            )

    def _show_settings(self):
        """显示设置对话框的包装方法，添加异常处理"""
        try:
            logger.info("Showing settings dialog")
            self.service.show_settings()
        except Exception as e:
            logger.critical(f"Failed to show settings dialog: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                None,
                "Error",
                f"Error showing settings dialog: {str(e)}"
            )

    def show_notification(self, title, message):
        """显示系统通知"""
        try:
            logger.info(f"Showing notification: {title} - {message}")
            self.tray_icon.showMessage(title, message, QtWidgets.QSystemTrayIcon.MessageIcon.Information, 3000)
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            traceback.print_exc()

    def exit_app(self):
        """退出应用程序"""
        try:
            logger.info("User requested to exit application")
            reply = QtWidgets.QMessageBox.question(
                None,
                'Confirm Exit',
                'Are you sure you want to exit Print Service?',
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )

            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                logger.info("User confirmed exit, stopping service")
                self.service.stop()
                self.app.quit()
                logger.info("Application exited")
        except Exception as e:
            logger.critical(f"Failed to exit application: {e}")
            traceback.print_exc()
            # 强制退出
            sys.exit(1)
