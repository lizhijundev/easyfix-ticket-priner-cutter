# ui/settings_dialog.py
from PyQt6 import QtWidgets, QtCore, QtGui
import traceback
import webbrowser
from utils.logger import setup_logger

logger = setup_logger()

class ServiceStatusWidget(QtWidgets.QWidget):
    """服务状态和控制小部件"""
    def __init__(self, service_name, port, service_obj=None):
        super().__init__()
        self.service_name = service_name
        self.port = port
        self.service_obj = service_obj
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 服务状态标签
        self.status_label = QtWidgets.QLabel()
        self.update_status()

        # URL链接
        url = f"http://localhost:{self.port}"
        if self.service_name == "Socket":
            url_text = f"localhost:{self.port}"
        else:
            url_text = url

        self.url_label = QtWidgets.QLabel(f'<a href="{url}">{url_text}</a>')
        self.url_label.setOpenExternalLinks(True)

        # 控制按钮
        self.start_btn = QtWidgets.QPushButton("Start")
        self.start_btn.setFixedWidth(60)
        self.start_btn.clicked.connect(self.start_service)

        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.setFixedWidth(60)
        self.stop_btn.clicked.connect(self.stop_service)

        self.restart_btn = QtWidgets.QPushButton("Restart")
        self.restart_btn.setFixedWidth(60)
        self.restart_btn.clicked.connect(self.restart_service)

        # 添加到布局
        layout.addWidget(self.status_label)
        layout.addWidget(self.url_label)
        layout.addStretch(1)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.restart_btn)

        self.setLayout(layout)

        # 更新按钮状态
        self.update_button_states()

    def update_status(self):
        """更新服务状态显示"""
        is_running = False
        if self.service_obj:
            is_running = self.service_obj.running

        if is_running:
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def update_button_states(self):
        """根据服务状态更新按钮状态"""
        is_running = False
        if self.service_obj:
            is_running = self.service_obj.running

        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        self.restart_btn.setEnabled(is_running)

    def start_service(self):
        """启动服务"""
        try:
            if self.service_obj and not self.service_obj.running:
                self.service_obj.start()
                self.update_status()
                self.update_button_states()
        except Exception as e:
            logger.error(f"Failed to start {self.service_name} service: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to start {self.service_name} service: {str(e)}"
            )

    def stop_service(self):
        """停止服务"""
        try:
            if self.service_obj and self.service_obj.running:
                self.service_obj.stop()
                self.update_status()
                self.update_button_states()
        except Exception as e:
            logger.error(f"Failed to stop {self.service_name} service: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to stop {self.service_name} service: {str(e)}"
            )

    def restart_service(self):
        """重启服务"""
        try:
            if self.service_obj and self.service_obj.running:
                self.service_obj.stop()
                self.service_obj.start()
                self.update_status()
                self.update_button_states()
        except Exception as e:
            logger.error(f"Failed to restart {self.service_name} service: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to restart {self.service_name} service: {str(e)}"
            )


class SettingsDialog(QtWidgets.QDialog):
    # 添加信号
    settingsChanged = QtCore.pyqtSignal()

    def __init__(self, settings, printer_manager, socket_server=None, http_server=None):
        super().__init__()
        try:
            self.settings = settings
            self.printer_manager = printer_manager
            self.socket_server = socket_server
            self.http_server = http_server
            self.old_settings = {
                "socket_port": settings.get("socket_port", 8420),
                "http_port": settings.get("http_port", 8520)
            }

            self.setWindowTitle("Print Service Settings")
            self.init_ui()
            logger.info("Settings dialog initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize settings dialog: {e}")
            traceback.print_exc()
            raise

    def init_ui(self):
        try:
            self.resize(600, 450)

            layout = QtWidgets.QVBoxLayout()

            # 创建选项卡
            tabs = QtWidgets.QTabWidget()

            # 标签打印机设置选项卡
            label_tab = QtWidgets.QWidget()
            label_layout = QtWidgets.QFormLayout()

            # 获取系统打印机列表
            printers = self.printer_manager.get_all_printers()

            # 标签打印机选择
            self.label_printer_combo = QtWidgets.QComboBox()
            self.label_printer_combo.addItems(printers)
            current_label_printer = self.settings.get("label_printer", "")
            if current_label_printer in printers:
                self.label_printer_combo.setCurrentText(current_label_printer)

            # 标签尺寸选择
            self.label_size_combo = QtWidgets.QComboBox()
            self.label_size_combo.addItems(["30x20mm", "40x30mm", "50x30mm", "60x40mm", "Custom"])
            self.label_size_combo.setCurrentText(self.settings.get("label_size", "40x30mm"))

            label_layout.addRow("Label Printer:", self.label_printer_combo)
            label_layout.addRow("Label Size:", self.label_size_combo)
            label_tab.setLayout(label_layout)

            # 小票打印机设置选项卡
            ticket_tab = QtWidgets.QWidget()
            ticket_layout = QtWidgets.QFormLayout()

            # 小票打印机选择
            self.ticket_printer_combo = QtWidgets.QComboBox()
            self.ticket_printer_combo.addItems(printers)
            current_ticket_printer = self.settings.get("ticket_printer", "")
            if current_ticket_printer in printers:
                self.ticket_printer_combo.setCurrentText(current_ticket_printer)

            # 小票宽度选择
            self.ticket_width_combo = QtWidgets.QComboBox()
            self.ticket_width_combo.addItems(["58mm", "80mm", "Custom"])
            self.ticket_width_combo.setCurrentText(self.settings.get("ticket_width", "80mm"))

            ticket_layout.addRow("Receipt Printer:", self.ticket_printer_combo)
            ticket_layout.addRow("Receipt Width:", self.ticket_width_combo)
            ticket_tab.setLayout(ticket_layout)

            # 服务设置选项卡
            service_tab = QtWidgets.QWidget()
            service_layout = QtWidgets.QVBoxLayout()

            # 端口设置组
            port_group = QtWidgets.QGroupBox("Service Ports")
            port_layout = QtWidgets.QFormLayout()

            # Socket端口
            self.socket_port_spin = QtWidgets.QSpinBox()
            self.socket_port_spin.setRange(1024, 65535)
            self.socket_port_spin.setValue(self.settings.get("socket_port", 8420))

            # HTTP端口
            self.http_port_spin = QtWidgets.QSpinBox()
            self.http_port_spin.setRange(1024, 65535)
            self.http_port_spin.setValue(self.settings.get("http_port", 8520))

            port_layout.addRow("Socket Service Port:", self.socket_port_spin)
            port_layout.addRow("HTTP Service Port:", self.http_port_spin)
            port_group.setLayout(port_layout)

            # 服务状态组
            status_group = QtWidgets.QGroupBox("Service Status")
            status_layout = QtWidgets.QVBoxLayout()

            # Socket服务状态
            socket_port = self.settings.get("socket_port", 8420)
            self.socket_status_widget = ServiceStatusWidget("Socket", socket_port, self.socket_server)

            # HTTP服务状态
            http_port = self.settings.get("http_port", 8520)
            self.http_status_widget = ServiceStatusWidget("HTTP", http_port, self.http_server)

            status_layout.addWidget(QtWidgets.QLabel("Socket Service:"))
            status_layout.addWidget(self.socket_status_widget)
            status_layout.addWidget(QtWidgets.QLabel("HTTP Service:"))
            status_layout.addWidget(self.http_status_widget)
            status_group.setLayout(status_layout)

            service_layout.addWidget(port_group)
            service_layout.addWidget(status_group)
            service_layout.addStretch(1)
            service_tab.setLayout(service_layout)

            # 添加选项卡
            tabs.addTab(label_tab, "Label Printer")
            tabs.addTab(ticket_tab, "Receipt Printer")
            tabs.addTab(service_tab, "Services")

            layout.addWidget(tabs)

            # 按钮
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

    def save_settings(self):
        try:
            logger.info("Saving settings...")
            # 保存设置
            self.settings.set("label_printer", self.label_printer_combo.currentText())
            self.settings.set("label_size", self.label_size_combo.currentText())
            self.settings.set("ticket_printer", self.ticket_printer_combo.currentText())
            self.settings.set("ticket_width", self.ticket_width_combo.currentText())
            self.settings.set("socket_port", self.socket_port_spin.value())
            self.settings.set("http_port", self.http_port_spin.value())

            self.settings.save()
            logger.info("Settings saved")

            # 检查是否需要重启服务
            if (self.old_settings["socket_port"] != self.socket_port_spin.value() or
                    self.old_settings["http_port"] != self.http_port_spin.value()):
                # 发出信号，通知需要重启服务
                logger.info("Port settings changed, emitting settingsChanged signal")
                self.settingsChanged.emit()

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
