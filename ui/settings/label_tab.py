from PyQt6 import QtWidgets, QtCore
from utils.logger import setup_logger

logger = setup_logger()

class LabelTab(QtWidgets.QWidget):
    def __init__(self, settings, printer):
        super().__init__()
        self.settings = settings
        self.printer = printer
        self.init_ui()

    def init_ui(self):
        """初始化标签打印机设置选项卡UI"""
        label_layout = QtWidgets.QVBoxLayout()

        # 标签打印机选择
        label_printer_form = QtWidgets.QFormLayout()
        
        # 获取标签打印机列表
        printers = self.printer.get_label_printers()
        
        self.label_printer_combo = self.create_printer_combo(
            printers, "label_printer")

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
        self.setLayout(label_layout)

    def create_printer_combo(self, printers, setting_key):
        """创建打印机选择下拉框"""
        combo = QtWidgets.QComboBox()
        combo.addItems(printers)
        current_printer = self.settings.get(setting_key, "")
        if current_printer in printers:
            combo.setCurrentText(current_printer)
        return combo
    
    def update_label_printer_status(self):
        """更新标签打印机状态显示"""
        self.printer.discover_printers()  # 重新检查打印机状态
        is_available = self.printer.is_label_printer_available()
        status_text = "Available" if is_available else "Not Available"
        status_style = "color: green; font-weight: bold;" if is_available else "color: red; font-weight: bold;"
        self.label_printer_status.setText(status_text)
        self.label_printer_status.setStyleSheet(status_style)

    def update_label_size_inputs(self):
        """根据选择的标签尺寸类型更新输入框状态"""
        is_custom = self.label_size_combo.currentText() == "Custom"
        self.label_width_edit.setEnabled(is_custom)
        self.label_height_edit.setEnabled(is_custom)
    
    def save_settings(self):
        """保存当前标签页的设置"""
        # 保存标签打印机设置
        self.settings.set("label_printer", self.label_printer_combo.currentText())
        
        # 保存标签尺寸设置
        label_size = self.label_size_combo.currentText()
        self.settings.set("label_size", label_size)
        if label_size == "Custom":
            custom_width = self.label_width_edit.text()
            custom_height = self.label_height_edit.text()
            self.settings.set("label_custom_size", f"{custom_width}x{custom_height}")

