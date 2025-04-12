from PyQt6 import QtWidgets, QtCore
import traceback
from utils.logger import setup_logger
from ui.settings import TicketTab, LabelTab, ServiceTab

logger = setup_logger()

class SettingsDialog(QtWidgets.QDialog):
    # 添加信号
    settingsChanged = QtCore.pyqtSignal()

    def __init__(self, settings, printer_manager, socket_server=None, http_server=None):
        try:
            super().__init__()
            self.setWindowTitle("Settings")
            self.resize(600, 450)

            self.settings = settings
            self.printer_manager = printer_manager
            self.socket_server = socket_server
            self.http_server = http_server
            
            # 初始化选项卡
            self.ticket_tab = None
            self.label_tab = None
            self.service_tab = None

            self.init_ui()
            logger.info("Settings dialog initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize settings dialog: {e}")
            traceback.print_exc()
            raise

    def init_ui(self):
        """初始化UI主框架"""
        try:
            layout = QtWidgets.QVBoxLayout()

            # 创建选项卡
            tabs = QtWidgets.QTabWidget()
            
            # 创建各个选项卡
            self.ticket_tab = TicketTab(self.settings, self.printer_manager)
            self.label_tab = LabelTab(self.settings, self.printer_manager)
            self.service_tab = ServiceTab(self.settings, self.socket_server, self.http_server)
            
            # 连接服务控制信号
            self.service_tab.serviceControlRequested.connect(self.handle_service_control)
            
            tabs.addTab(self.ticket_tab, "Receipt Printer")
            tabs.addTab(self.label_tab, "Label Printer")
            tabs.addTab(self.service_tab, "Services")

            layout.addWidget(tabs)

            # 添加确认和取消按钮
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok |
                QtWidgets.QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(self.save_settings)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
            
            self.setLayout(layout)
        except Exception as e:
            logger.critical(f"Failed to initialize settings dialog UI: {e}")
            traceback.print_exc()
            raise

    def handle_service_control(self, action):
        """处理服务控制请求"""
        try:
            logger.info(f"Service control action requested: {action}")
            
            if action == "restart":
                self._restart_services()
            elif action == "stop":
                self._stop_services()
            elif action == "start":
                self._start_services()
        except Exception as e:
            logger.error(f"Failed to handle service control action {action}: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to {action} services: {str(e)}")

    def _restart_services(self):
        """重启服务"""
        try:
            # 发出信号通知需要重启服务
            logger.info("User requested service restart")
            self.settingsChanged.emit()

            # 更新状态标签
            self.service_tab.update_service_status(True)

            QtWidgets.QMessageBox.information(self, "Services Restarted", "Services have been restarted successfully.")
        except Exception as e:
            logger.error(f"Failed to restart services: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to restart services: {str(e)}")

    def _stop_services(self):
        """停止服务"""
        try:
            if self.socket_server:
                self.socket_server.stop()
            if self.http_server:
                self.http_server.stop()

            # 更新状态标签
            self.service_tab.update_service_status(False)

            QtWidgets.QMessageBox.information(self, "Services Stopped", "Services have been stopped successfully.")
        except Exception as e:
            logger.error(f"Failed to stop services: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to stop services: {str(e)}")

    def _start_services(self):
        """启动服务"""
        try:
            # 先保存当前设置
            self.save_settings(restart_services=False)

            # 发出信号通知需要重启服务
            logger.info("User requested service start")
            self.settingsChanged.emit()

            # 更新状态标签
            self.service_tab.update_service_status(True)

            QtWidgets.QMessageBox.information(self, "Services Started", "Services have been started successfully.")
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to start services: {str(e)}")

    def save_settings(self, restart_services=True):
        """保存所有设置"""
        try:
            logger.info("Saving settings...")
            
            # 保存小票打印机选项卡设置
            self.ticket_tab.save_settings()
            
            # 保存标签打印机选项卡设置
            self.label_tab.save_settings()
            
            # 保存服务选项卡设置并获取端口变更信息
            port_changes = self.service_tab.save_settings()
            
            # 保存设置到文件
            self.settings.save()
            logger.info("Settings saved")

            # 检查是否需要重启服务
            if restart_services and (port_changes["old_socket_port"] != port_changes["new_socket_port"] or
                                     port_changes["old_http_port"] != port_changes["new_http_port"]):
                # 发出信号，通知需要重启服务
                logger.info("Port settings changed, emitting settingsChanged signal")
                self.settingsChanged.emit()

            # 如果不需要重启服务，直接返回
            if not restart_services:
                return

            # 接受对话框
            logger.info("Closing settings dialog")
            self.accept()
        except Exception as e:
            logger.critical(f"Failed to save settings: {e}")
            traceback.print_exc()

            # 显示错误消息
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Error saving settings: {str(e)}"
            )
