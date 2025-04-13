from PyQt6 import QtWidgets, QtCore
import webbrowser
from utils.logger import setup_logger

logger = setup_logger()

class ServiceTab(QtWidgets.QWidget):
    # Define signals
    serviceControlRequested = QtCore.pyqtSignal(str)
    
    def __init__(self, settings, socket_server=None, http_server=None):
        super().__init__()
        self.settings = settings
        self.socket_server = socket_server
        self.http_server = http_server
        self.init_ui()

    def init_ui(self):
        """Initialize service settings tab UI"""
        service_layout = QtWidgets.QVBoxLayout()

        # Port settings
        port_group = self.create_port_settings_group()
        
        # Service status display and control
        status_group = self.create_service_status_group()

        service_layout.addWidget(port_group)
        service_layout.addWidget(status_group)
        service_layout.addStretch(1)
        self.setLayout(service_layout)

    def create_port_settings_group(self):
        """Create port settings group"""
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
        
        return port_group
        
    def create_service_status_group(self):
        """Create service status group"""
        status_group = QtWidgets.QGroupBox("Service Status")
        status_layout = QtWidgets.QVBoxLayout()

        # Socket service status
        socket_status = QtWidgets.QHBoxLayout()
        socket_status.addWidget(QtWidgets.QLabel("Socket Service:"))
        self.socket_status_label = self.create_status_label(self.socket_server is not None)
        socket_status.addWidget(self.socket_status_label)
        socket_status.addStretch(1)

        # HTTP service status
        http_status = QtWidgets.QHBoxLayout()
        http_status.addWidget(QtWidgets.QLabel("HTTP (Flask) Service:"))
        self.http_status_label = self.create_status_label(self.http_server is not None)
        http_status.addWidget(self.http_status_label)
        http_status.addStretch(1)

        # Socket service link
        socket_link = QtWidgets.QHBoxLayout()
        socket_link.addWidget(QtWidgets.QLabel("Socket:"))
        socket_url = f"localhost:{self.socket_port_spin.value()}"
        socket_link_label = QtWidgets.QLabel(f"<a href='#'>{socket_url}</a>")
        socket_link_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        socket_link_label.setOpenExternalLinks(False)
        socket_link_label.linkActivated.connect(lambda: self._copy_to_clipboard(socket_url))
        socket_link.addWidget(socket_link_label)
        socket_link.addStretch(1)

        # HTTP service link
        http_link = QtWidgets.QHBoxLayout()
        http_link.addWidget(QtWidgets.QLabel("HTTP:"))
        http_url = f"http://localhost:{self.http_port_spin.value()}"
        http_link_label = QtWidgets.QLabel(f"<a href='{http_url}'>{http_url}</a>")
        http_link_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        http_link_label.setOpenExternalLinks(True)
        http_link.addWidget(http_link_label)
        http_link.addStretch(1)

        # Service control buttons
        control_buttons = self.create_service_control_buttons()

        status_layout.addLayout(socket_status)
        status_layout.addLayout(http_status)
        status_layout.addLayout(socket_link)
        status_layout.addLayout(http_link)
        status_layout.addLayout(control_buttons)
        status_group.setLayout(status_layout)
        
        return status_group
    
    def create_service_control_buttons(self):
        """Create service control buttons"""
        control_buttons = QtWidgets.QHBoxLayout()

        self.restart_btn = QtWidgets.QPushButton("Restart Services")
        self.restart_btn.clicked.connect(lambda: self.serviceControlRequested.emit("restart"))

        self.stop_btn = QtWidgets.QPushButton("Stop Services")
        self.stop_btn.clicked.connect(lambda: self.serviceControlRequested.emit("stop"))

        self.start_btn = QtWidgets.QPushButton("Start Services")
        self.start_btn.clicked.connect(lambda: self.serviceControlRequested.emit("start"))
        self.start_btn.setEnabled(not (self.socket_server and self.http_server))

        control_buttons.addWidget(self.restart_btn)
        control_buttons.addWidget(self.stop_btn)
        control_buttons.addWidget(self.start_btn)
        
        return control_buttons
    
    def create_status_label(self, is_running):
        """Create status label"""
        label = QtWidgets.QLabel("Running" if is_running else "Stopped")
        label.setStyleSheet("color: green; font-weight: bold;" if is_running else "color: red; font-weight: bold;")
        return label

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(text)
            QtWidgets.QMessageBox.information(self, "Copied", f"Copied to clipboard: {text}")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
    
    def update_service_status(self, is_running):
        """Update service status display"""
        status_text = "Running" if is_running else "Stopped"
        status_style = "color: green; font-weight: bold;" if is_running else "color: red; font-weight: bold;"
        
        self.socket_status_label.setText(status_text)
        self.socket_status_label.setStyleSheet(status_style)
        self.http_status_label.setText(status_text)
        self.http_status_label.setStyleSheet(status_style)
        
        self.start_btn.setEnabled(not is_running)
    
    def save_settings(self):
        """Save current tab settings"""
        # Save port settings
        self.settings.set("socket_port", self.socket_port_spin.value())
        self.settings.set("http_port", self.http_port_spin.value())
        
        return {
            "old_socket_port": self.settings.get("socket_port", 8420),
            "old_http_port": self.settings.get("http_port", 8520),
            "new_socket_port": self.socket_port_spin.value(),
            "new_http_port": self.http_port_spin.value()
        }
