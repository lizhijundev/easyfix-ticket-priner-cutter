import traceback
from typing import List, Tuple, Optional
from utils.logger import setup_logger
from config.settings import Settings


logger = setup_logger(__name__)

RECEIPT_PRINTER_NAME = "ReceiptPrinter"
LABEL_PRINTER_NAME = "LabelPrinter"


class WindowsPrinter:
    def __init__(self, settings: Settings):
        self.receipt_printer_available = False
        self.label_printer_available = False
        self.settings = settings
        self._init_printers()

    def _init_printers(self):
        """初始化打印机状态"""
        self.discover_printers()

    def discover_printers(self) -> Tuple[bool, bool]:
        """发现可用打印机并更新状态"""
        try:
            self.receipt_printer_available = self.check_printer_availability("receipt")
            self.label_printer_available = self.check_printer_availability("label")
            logger.info(f"Printers initialized - Receipt: {self.receipt_printer_available}, Label: {self.label_printer_available}")
            return self.receipt_printer_available, self.label_printer_available
        except Exception as e:
            logger.error(f"Failed to initialize printers: {e}")
            traceback.print_exc()
            return False, False

    def check_printer_availability(self, printer_type: str) -> bool:
        """检查特定类型打印机的USB连接状态"""
        try:
            printer_name = self.settings.get(f"{printer_type}_printer", "")
            if not printer_name:
                return False

            # 根据打印机类型获取对应的打印机列表
            if printer_type == "receipt":
                printers = self.get_receipt_printers()
            else:
                printers = self.get_label_printers()
            # 首先检查打印机是否在列表中
            if printer_name not in printers:
                return False

            return self._check_usb_printer(printer_name)
        except Exception as e:
            logger.error(f"Failed to check {printer_type} printer availability: {e}")
            return False

    def get_all_printers(self) -> List[str]:
        """Windows系统获取打印机列表"""
        try:
            import win32print
            printers = []
            for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL):
                printers.append(printer[2])
            logger.debug(f"Found Windows printers: {printers}")
            return printers
        except ImportError:
            logger.warning("win32print module not available, using dummy printers")
            return ["Dummy Receipt Printer", "Dummy Label Printer"]

    def get_receipt_printers(self) -> List[str]:
        """获取小票打印机列表"""
        all_printers = self.get_all_printers()
        receipt_printers = [p for p in all_printers if RECEIPT_PRINTER_NAME in p]
        logger.debug(f"Found receipt printers: {receipt_printers}")
        return receipt_printers

    def get_label_printers(self) -> List[str]:
        """获取标签打印机列表"""
        all_printers = self.get_all_printers()
        label_printers = [p for p in all_printers if LABEL_PRINTER_NAME in p]
        logger.debug(f"Found label printers: {label_printers}")
        return label_printers

    def _check_usb_printer(self, printer_name: str) -> bool:
        """Windows系统检查USB打印机状态"""
        try:
            import win32print
            printer_info = {}
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                printer_info = win32print.GetPrinter(hPrinter, 2)
            finally:
                win32print.ClosePrinter(hPrinter)

            # 检查打印机状态
            status = printer_info.get("Status", 0)
            if status == 0:  # 没有错误状态表示打印机可用
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking Windows USB printer: {e}")
            return False

    def is_receipt_printer_available(self) -> bool:
        """检查小票打印机是否可用"""
        return self.receipt_printer_available

    def is_label_printer_available(self) -> bool:
        """检查标签打印机是否可用"""
        return self.label_printer_available


    def manual_cut_receipt(self) -> Tuple[bool, str]:
        """手动切纸"""
        try:
            import win32print
            if not self.receipt_printer_available:
                logger.warning("Receipt printer not available, cannot cut paper")
                return False, "Receipt printer not available"

            printer_name = self.settings.get("receipt_printer", "")
            if not printer_name:
                logger.warning("No receipt printer selected")
                return False, "No receipt printer selected"

            logger.info(f"Manual paper cut for printer: {printer_name}")

            CUT_PAPER_COMMAND = b'\x1D\x56\x41\x00'  # GS V A 0 - 全切

            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Paper Cut", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, CUT_PAPER_COMMAND)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)

            logger.info("Paper cut command sent successfully")
            return True, "Paper cut successful"
        except ImportError:
            logger.warning("Cannot import win32print module for paper cutting")
            return False, "Missing required modules for paper cutting"
        except Exception as e:
            logger.error(f"Error sending cut command: {e}")
            return False, f"Error sending cut command: {str(e)}"


    def print_label_text(self, label_data: str) -> Tuple[bool, str]:
        """打印标签"""
        try:
            import win32print
            import tempfile

            if not self.label_printer_available:
                logger.warning("Label printer not available")
                return False, "Label printer not available"

            printer_name = self.settings.get("label_printer", "")
            if not printer_name:
                logger.warning("No label printer selected")
                return False, "No label printer selected"

            logger.info(f"Printing label on {printer_name}")

            # 创建临时文件保存标签数据
            with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
                temp_file_name = temp_file.name
                temp_file.write(label_data)

            try:
                # 获取打印机句柄
                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    # 发送原始打印数据
                    hJob = win32print.StartDocPrinter(hPrinter, 1, ("EasyFix Label", temp_file_name, "RAW"))
                    try:
                        with open(temp_file_name, "rb") as file:
                            data = file.read()
                            win32print.StartPagePrinter(hPrinter)
                            win32print.WritePrinter(hPrinter, data)
                            win32print.EndPagePrinter(hPrinter)
                    finally:
                        win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)
                logger.info(f"Label sent to Windows printer: {printer_name}")
                return True, "Label sent to printer"
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_name)
                except:
                    pass

        except ImportError:
            logger.error("win32print module not available")
            return False, "Missing required modules for printing on Windows"

        except Exception as e:
            logger.error(f"Failed to print label: {e}")
            traceback.print_exc()
            return False, f"Error: {str(e)}"
