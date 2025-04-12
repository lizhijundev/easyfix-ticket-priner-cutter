from PyQt6 import QtWidgets, QtCore
from utils.logger import setup_logger

logger = setup_logger()

class ReceiptTab(QtWidgets.QWidget):
    def __init__(self, settings, printer_manager):
        super().__init__()
        self.settings = settings
        self.printer_manager = printer_manager
        self.init_ui()

    def init_ui(self):
        """初始化小票打印机设置选项卡UI"""
        receipt_layout = QtWidgets.QVBoxLayout()

        # 小票打印机选择
        printer_form = QtWidgets.QFormLayout()
        
        # 获取小票打印机列表
        printers = self.printer_manager.get_receipt_printers()
        
        self.receipt_printer_combo = self.create_printer_combo(
            printers, "receipt_printer")

        # 打印机状态
        self.receipt_printer_status = QtWidgets.QLabel()
        self.update_receipt_printer_status()

        # 添加到表单
        printer_form.addRow("Receipt Printer:", self.receipt_printer_combo)
        printer_form.addRow("Status:", self.receipt_printer_status)
        
        # 小票宽度选择
        width_layout = QtWidgets.QHBoxLayout()
        self.receipt_width_combo = QtWidgets.QComboBox()
        self.receipt_width_combo.addItems(["80mm", "58mm", "Custom"])
        self.receipt_width_combo.setCurrentText(self.settings.get("receipt_width", "80mm"))

        self.receipt_width_custom = QtWidgets.QLineEdit()
        self.receipt_width_custom.setPlaceholderText("Width in mm")
        self.receipt_width_custom.setText(self.settings.get("receipt_width_custom", ""))
        self.receipt_width_custom.setEnabled(self.receipt_width_combo.currentText() == "Custom")

        self.receipt_width_combo.currentTextChanged.connect(self.on_receipt_width_changed)

        width_layout.addWidget(QtWidgets.QLabel("Receipt Width:"))
        width_layout.addWidget(self.receipt_width_combo)
        width_layout.addWidget(self.receipt_width_custom)

        # 手动切纸按钮
        self.cut_paper_btn = QtWidgets.QPushButton("Manual Paper Cut")
        self.cut_paper_btn.clicked.connect(self.on_cut_paper)
        self.cut_paper_btn.setEnabled(self.printer_manager.is_receipt_printer_available())

        receipt_layout.addLayout(printer_form)
        receipt_layout.addLayout(width_layout)
        receipt_layout.addWidget(self.cut_paper_btn)
        receipt_layout.addStretch(1)
        self.setLayout(receipt_layout)
    
    def create_printer_combo(self, printers, setting_key):
        """创建打印机选择下拉框"""
        combo = QtWidgets.QComboBox()
        combo.addItems(printers)
        current_printer = self.settings.get(setting_key, "")
        if current_printer in printers:
            combo.setCurrentText(current_printer)
        return combo
    
    def on_receipt_width_changed(self, text):
        """当小票宽度选择改变时更新自定义宽度输入框状态"""
        self.receipt_width_custom.setEnabled(text == "Custom")

    def update_receipt_printer_status(self):
        """更新小票打印机状态显示"""
        self.printer_manager.discover_printers()  # 重新检查打印机状态
        is_available = self.printer_manager.is_receipt_printer_available()
        status_text = "Available" if is_available else "Not Available"
        status_style = "color: green; font-weight: bold;" if is_available else "color: red; font-weight: bold;"
        self.receipt_printer_status.setText(status_text)
        self.receipt_printer_status.setStyleSheet(status_style)

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
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to cut paper: {str(e)}")

    def save_settings(self):
        """保存当前标签页的设置"""
        # 保存小票打印机设置
        self.settings.set("receipt_printer", self.receipt_printer_combo.currentText())
        
        # 保存小票宽度设置
        receipt_width = self.receipt_width_combo.currentText()
        self.settings.set("receipt_width", receipt_width)
        if receipt_width == "Custom":
            self.settings.set("receipt_width_custom", self.receipt_width_custom.text())

