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
        try:
            super().__init__()
            self.setWindowTitle("Settings")

            self.settings = settings
            self.printer_manager = printer_manager
            self.socket_server = socket_server
            self.http_server = http_server

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

            # 小票打印机设置选项卡
            ticket_tab = QtWidgets.QWidget()
            ticket_layout = QtWidgets.QVBoxLayout()

            # 小票打印机选择
            printer_form = QtWidgets.QFormLayout()

            self.ticket_printer_combo = QtWidgets.QComboBox()
            printers = self.printer_manager.get_all_printers()
            self.ticket_printer_combo.addItems(printers)
            current_ticket_printer = self.settings.get("ticket_printer", "")
            if current_ticket_printer in printers:
                self.ticket_printer_combo.setCurrentText(current_ticket_printer)

            # 打印机状态
            self.receipt_printer_status = QtWidgets.QLabel()
            self.update_receipt_printer_status()

            # 小票宽度选择
            width_layout = QtWidgets.QHBoxLayout()
            self.ticket_width_combo = QtWidgets.QComboBox()
            self.ticket_width_combo.addItems(["80mm", "58mm", "Custom"])
            self.ticket_width_combo.setCurrentText(self.settings.get("ticket_width", "80mm"))

            self.ticket_width_custom = QtWidgets.QLineEdit()
            self.ticket_width_custom.setPlaceholderText("Width in mm")
            self.ticket_width_custom.setText(self.settings.get("ticket_width_custom", ""))
            self.ticket_width_custom.setEnabled(self.ticket_width_combo.currentText() == "Custom")

            self.ticket_width_combo.currentTextChanged.connect(self.on_ticket_width_changed)

            width_layout.addWidget(QtWidgets.QLabel("Receipt Width:"))
            width_layout.addWidget(self.ticket_width_combo)
            width_layout.addWidget(self.ticket_width_custom)

            # 手动切纸按钮
            self.cut_paper_btn = QtWidgets.QPushButton("Manual Paper Cut")
            self.cut_paper_btn.clicked.connect(self.on_cut_paper)
            self.cut_paper_btn.setEnabled(self.printer_manager.is_receipt_printer_available())

            printer_form.addRow("Receipt Printer:", self.ticket_printer_combo)
            printer_form.addRow("Status:", self.receipt_printer_status)

            ticket_layout.addLayout(printer_form)
            ticket_layout.addLayout(width_layout)
            ticket_layout.addWidget(self.cut_paper_btn)
            ticket_layout.addStretch(1)
            ticket_tab.setLayout(ticket_layout)

            # 标签打印机设置选项卡
            label_tab = QtWidgets.QWidget()
            label_layout = QtWidgets.QVBoxLayout()

            # 标签打印机选择
            label_printer_form = QtWidgets.QFormLayout()

            self.label_printer_combo = QtWidgets.QComboBox()
            self.label_printer_combo.addItems(printers)
            current_label_printer = self.settings.get("label_printer", "")
            if current_label_printer in printers:
                self.label_printer_combo.setCurrentText(current_label_printer)

            # 打印机状态
            self.label_printer_status = QtWidgets.QLabel()
            self.update_label_printer_status()

            label_printer_form.addRow("Label Printer:", self.label_printer_combo)
            label_printer_form.addRow("Status:", self.label_printer_status)

            # 标签尺寸选择
            size_group = QtWidgets.QGroupBox("Label Size")
            size_layout = QtWidgets.QVBoxLayout()

            # 标签尺寸选择组合框和自定义输入
            size_combo_layout = QtWidgets.QHBoxLayout()
            self.label_size_combo = QtWidgets.QComboBox()
            self.label_size_combo.addItems(["50mm x 40mm", "Custom"])

            # 获取当前尺寸设置
            current_size = self.settings.get("label_size", "50mm x 40mm")
            if "Custom" in current_size:
                self.label_size_combo.setCurrentText("Custom")
            else:
                # 尝试匹配预设尺寸，如果没有匹配则设置为自定义
                if current_size in ["50mm x 40mm"]:
                    self.label_size_combo.setCurrentText(current_size)
                else:
                    self.label_size_combo.setCurrentText("Custom")

            size_combo_layout.addWidget(QtWidgets.QLabel("Preset:"))
            size_combo_layout.addWidget(self.label_size_combo)

            # 自定义尺寸输入
            custom_size_layout = QtWidgets.QHBoxLayout()
            self.label_width_edit = QtWidgets.QLineEdit()
            self.label_height_edit = QtWidgets.QLineEdit()
            self.label_width_edit.setPlaceholderText("Width (mm)")
            self.label_height_edit.setPlaceholderText("Height (mm)")

            # 如果是自定义尺寸，从设置中获取宽高
            if self.label_size_combo.currentText() == "Custom":
                width_height = self.settings.get("label_custom_size", "40x30").split("x")
                if len(width_height) == 2:
                    self.label_width_edit.setText(width_height[0])
                    self.label_height_edit.setText(width_height[1])

            # 根据是否选择自定义尺寸启用或禁用输入框
            self.update_label_size_inputs()
            self.label_size_combo.currentTextChanged.connect(self.update_label_size_inputs)

            custom_size_layout.addWidget(QtWidgets.QLabel("Width:"))
            custom_size_layout.addWidget(self.label_width_edit)
            custom_size_layout.addWidget(QtWidgets.QLabel("mm"))
            custom_size_layout.addWidget(QtWidgets.QLabel("Height:"))
            custom_size_layout.addWidget(self.label_height_edit)
            custom_size_layout.addWidget(QtWidgets.QLabel("mm"))

            size_layout.addLayout(size_combo_layout)
            size_layout.addLayout(custom_size_layout)
            size_group.setLayout(size_layout)

            label_layout.addLayout(label_printer_form)
            label_layout.addWidget(size_group)
            label_layout.addStretch(1)
            label_tab.setLayout(label_layout)

            # 服务设置选项卡
            service_tab = QtWidgets.QWidget()
            service_layout = QtWidgets.QVBoxLayout()

            # 端口设置
            port_group = QtWidgets.QGroupBox("Port Settings")
            port_layout = QtWidgets.QFormLayout()

            self.socket_port_spin = QtWidgets.QSpinBox()
            self.socket_port_spin.setMinimum(1024)
            self.socket_port_spin.setMaximum(65535)
            self.socket_port_spin.setValue(self.settings.get("socket_port", 8420))

            self.http_port_spin = QtWidgets.QSpinBox()
            self.http_port_spin.setMinimum(1024)
            self.http_port_spin.setMaximum(65535)
            self.http_port_spin.setValue(self.settings.get("http_port", 8520))

            port_layout.addRow("Socket Port:", self.socket_port_spin)
            port_layout.addRow("HTTP Port:", self.http_port_spin)
            port_group.setLayout(port_layout)

            # 服务状态
            status_group = QtWidgets.QGroupBox("Service Status")
            status_layout = QtWidgets.QVBoxLayout()

            # 显示当前服务状态
            socket_status = QtWidgets.QHBoxLayout()
            socket_status.addWidget(QtWidgets.QLabel("Socket Service:"))
            self.socket_status_label = QtWidgets.QLabel("Running" if self.socket_server else "Stopped")
            self.socket_status_label.setStyleSheet("color: green; font-weight: bold;" if self.socket_server else "color: red; font-weight: bold;")
            socket_status.addWidget(self.socket_status_label)
            socket_status.addStretch(1)

            http_status = QtWidgets.QHBoxLayout()
            http_status.addWidget(QtWidgets.QLabel("HTTP Service:"))
            self.http_status_label = QtWidgets.QLabel("Running" if self.http_server else "Stopped")
            self.http_status_label.setStyleSheet("color: green; font-weight: bold;" if self.http_server else "color: red; font-weight: bold;")
            http_status.addWidget(self.http_status_label)
            http_status.addStretch(1)

            # 添加服务链接
            socket_link = QtWidgets.QHBoxLayout()
            socket_link.addWidget(QtWidgets.QLabel("Socket:"))
            socket_url = f"localhost:{self.socket_port_spin.value()}"
            socket_link_label = QtWidgets.QLabel(f"<a href='#'>{socket_url}</a>")
            socket_link_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
            socket_link_label.setOpenExternalLinks(False)
            socket_link_label.linkActivated.connect(lambda: self._copy_to_clipboard(socket_url))
            socket_link.addWidget(socket_link_label)
            socket_link.addStretch(1)

            http_link = QtWidgets.QHBoxLayout()
            http_link.addWidget(QtWidgets.QLabel("HTTP:"))
            http_url = f"http://localhost:{self.http_port_spin.value()}"
            http_link_label = QtWidgets.QLabel(f"<a href='{http_url}'>{http_url}</a>")
            http_link_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
            http_link_label.setOpenExternalLinks(True)
            http_link.addWidget(http_link_label)
            http_link.addStretch(1)

            # 服务控制按钮
            control_buttons = QtWidgets.QHBoxLayout()

            self.restart_btn = QtWidgets.QPushButton("Restart Services")
            self.restart_btn.clicked.connect(self._restart_services)

            self.stop_btn = QtWidgets.QPushButton("Stop Services")
            self.stop_btn.clicked.connect(self._stop_services)

            self.start_btn = QtWidgets.QPushButton("Start Services")
            self.start_btn.clicked.connect(self._start_services)
            self.start_btn.setEnabled(not (self.socket_server and self.http_server))

            control_buttons.addWidget(self.restart_btn)
            control_buttons.addWidget(self.stop_btn)
            control_buttons.addWidget(self.start_btn)

            status_layout.addLayout(socket_status)
            status_layout.addLayout(http_status)
            status_layout.addLayout(socket_link)
            status_layout.addLayout(http_link)
            status_layout.addLayout(control_buttons)
            status_group.setLayout(status_layout)

            service_layout.addWidget(port_group)
            service_layout.addWidget(status_group)
            service_layout.addStretch(1)
            service_tab.setLayout(service_layout)

            # 添加选项卡（交换顺序）
            tabs.addTab(ticket_tab, "Receipt Printer")
            tabs.addTab(label_tab, "Label Printer")
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

    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(text)
            QtWidgets.QMessageBox.information(self, "Copied", f"Copied to clipboard: {text}")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            traceback.print_exc()

    def _restart_services(self):
        """重启服务"""
        try:
            # 发出信号通知需要重启服务
            logger.info("User requested service restart")
            self.settingsChanged.emit()

            # 更新状态标签
            self.socket_status_label.setText("Running")
            self.socket_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.http_status_label.setText("Running")
            self.http_status_label.setStyleSheet("color: green; font-weight: bold;")

            # 更新按钮状态
            self.start_btn.setEnabled(False)

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
            self.socket_status_label.setText("Stopped")
            self.socket_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.http_status_label.setText("Stopped")
            self.http_status_label.setStyleSheet("color: red; font-weight: bold;")

            # 更新按钮状态
            self.start_btn.setEnabled(True)

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
            self.socket_status_label.setText("Running")
            self.socket_status_label.setStyleSheet("color: green; font-weight: bold;")
            self.http_status_label.setText("Running")
            self.http_status_label.setStyleSheet("color: green; font-weight: bold;")

            # 更新按钮状态
            self.start_btn.setEnabled(False)

            QtWidgets.QMessageBox.information(self, "Services Started", "Services have been started successfully.")
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to start services: {str(e)}")

    def update_label_printer_status(self):
        """更新标签打印机状态显示"""
        if self.printer_manager.is_label_printer_available():
            self.label_printer_status.setText("Available")
            self.label_printer_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.label_printer_status.setText("Not Available")
            self.label_printer_status.setStyleSheet("color: red; font-weight: bold;")

    def update_receipt_printer_status(self):
        """更新小票打印机状态显示"""
        if self.printer_manager.is_receipt_printer_available():
            self.receipt_printer_status.setText("Available")
            self.receipt_printer_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.receipt_printer_status.setText("Not Available")
            self.receipt_printer_status.setStyleSheet("color: red; font-weight: bold;")

    def update_label_size_inputs(self):
        """根据选择的标签尺寸类型更新输入框状态"""
        is_custom = self.label_size_combo.currentText() == "Custom"
        self.label_width_edit.setEnabled(is_custom)
        self.label_height_edit.setEnabled(is_custom)

    def on_ticket_width_changed(self, text):
        """当小票宽度选择改变时更新自定义宽度输入框状态"""
        self.ticket_width_custom.setEnabled(text == "Custom")

    def on_cut_paper(self):
        """手动切纸按钮点击事件"""
        try:
            success, message = self.printer_manager.manual_cut_receipt()
            if success:
                QtWidgets.QMessageBox.information(self, "Success", message)
            else:
                QtWidgets.QMessageBox.warning(self, "Warning", message)
        except Exception as e:
            logger.error(f"Error during manual paper cut: {e}")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to cut paper: {str(e)}")

    def save_settings(self, restart_services=True):
        try:
            logger.info("Saving settings...")
            # 保存打印机设置
            self.settings.set("label_printer", self.label_printer_combo.currentText())
            self.settings.set("ticket_printer", self.ticket_printer_combo.currentText())

            # 保存小票宽度设置
            ticket_width = self.ticket_width_combo.currentText()
            self.settings.set("ticket_width", ticket_width)
            if ticket_width == "Custom":
                self.settings.set("ticket_width_custom", self.ticket_width_custom.text())

            # 保存标签尺寸设置
            label_size = self.label_size_combo.currentText()
            self.settings.set("label_size", label_size)
            if label_size == "Custom":
                custom_width = self.label_width_edit.text()
                custom_height = self.label_height_edit.text()
                self.settings.set("label_custom_size", f"{custom_width}x{custom_height}")

            # 保存端口设置
            old_socket_port = self.settings.get("socket_port", 8420)
            old_http_port = self.settings.get("http_port", 8520)

            self.settings.set("socket_port", self.socket_port_spin.value())
            self.settings.set("http_port", self.http_port_spin.value())

            self.settings.save()
            logger.info("Settings saved")

            # 检查是否需要重启服务
            if restart_services and (old_socket_port != self.socket_port_spin.value() or
                                     old_http_port != self.http_port_spin.value()):
                # 发出信号，通知需要重启服务
                logger.info("Port settings changed, emitting settingsChanged signal")
                self.settingsChanged.emit()

            # 如果不需要重启服务，直接接受对话框
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