# printer/manager.py
import os
import sys
import platform
import logging
import traceback
from typing import List, Tuple, Optional
from config.settings import Settings

logger = logging.getLogger(__name__)

class PrinterManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.system = platform.system()
        self.receipt_printer_available = False
        self.label_printer_available = False
        self._init_printers()

    def _init_printers(self):
        """初始化打印机状态"""
        try:
            printers = self.get_all_printers()
            self.receipt_printer_available = bool(self.settings.get("ticket_printer") in printers)
            self.label_printer_available = bool(self.settings.get("label_printer") in printers)
            logger.info(f"Printers initialized - Receipt: {self.receipt_printer_available}, Label: {self.label_printer_available}")
        except Exception as e:
            logger.error(f"Failed to initialize printers: {e}")
            traceback.print_exc()

    def get_all_printers(self) -> List[str]:
        """获取系统所有打印机列表"""
        try:
            if self.system == "Windows":
                return self._get_windows_printers()
            elif self.system == "Darwin":  # macOS
                return self._get_mac_printers()
            else:  # Linux
                return self._get_linux_printers()
        except Exception as e:
            logger.error(f"Failed to get printers: {e}")
            traceback.print_exc()
            return []

    def _get_windows_printers(self) -> List[str]:
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

    def _get_mac_printers(self) -> List[str]:
        """macOS系统获取打印机列表"""
        try:
            import subprocess
            output = subprocess.check_output(["lpstat", "-a"]).decode("utf-8")
            printers = [line.split()[0] for line in output.splitlines() if line]
            logger.debug(f"Found macOS printers: {printers}")
            return printers
        except Exception as e:
            logger.error(f"Failed to get macOS printers: {e}")
            return []

    def _get_linux_printers(self) -> List[str]:
        """Linux系统获取打印机列表"""
        try:
            import subprocess
            output = subprocess.check_output(["lpstat", "-a"]).decode("utf-8")
            printers = [line.split()[0] for line in output.splitlines() if line]
            logger.debug(f"Found Linux printers: {printers}")
            return printers
        except Exception as e:
            logger.error(f"Failed to get Linux printers: {e}")
            return []

    def discover_printers(self) -> Tuple[bool, bool]:
        """发现可用打印机并更新状态"""
        try:
            printers = self.get_all_printers()
            ticket_printer = self.settings.get("ticket_printer", "")
            label_printer = self.settings.get("label_printer", "")

            self.receipt_printer_available = ticket_printer in printers
            self.label_printer_available = label_printer in printers

            logger.info(f"Discovered printers - Receipt: {self.receipt_printer_available}, Label: {self.label_printer_available}")
            return self.receipt_printer_available, self.label_printer_available
        except Exception as e:
            logger.error(f"Failed to discover printers: {e}")
            traceback.print_exc()
            return False, False

    def is_receipt_printer_available(self) -> bool:
        """检查小票打印机是否可用"""
        return self.receipt_printer_available

    def is_label_printer_available(self) -> bool:
        """检查标签打印机是否可用"""
        return self.label_printer_available

    def manual_cut_receipt(self) -> Tuple[bool, str]:
        """手动切纸"""
        try:
            if not self.receipt_printer_available:
                logger.warning("Receipt printer not available, cannot cut paper")
                return False, "Receipt printer not available"

            printer_name = self.settings.get("ticket_printer", "")
            if not printer_name:
                logger.warning("No receipt printer selected")
                return False, "No receipt printer selected"

            logger.info(f"Manual paper cut for printer: {printer_name}")

            if self.system == "Windows":
                return self._windows_cut_paper(printer_name)
            else:
                return self._unix_cut_paper(printer_name)

        except Exception as e:
            logger.error(f"Failed to cut paper: {e}")
            traceback.print_exc()
            return False, f"Error: {str(e)}"

    def _windows_cut_paper(self, printer_name: str) -> Tuple[bool, str]:
        """Windows系统切纸"""
        try:
            import win32print
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

    def _unix_cut_paper(self, printer_name: str) -> Tuple[bool, str]:
        """Unix系统(macOS/Linux)切纸"""
        try:
            import tempfile
            import subprocess

            CUT_PAPER_COMMAND = b'\x1D\x56\x41\x00'  # GS V A 0 - 全切

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_name = temp_file.name
                temp_file.write(CUT_PAPER_COMMAND)

            try:
                subprocess.run(["lp", "-d", printer_name, temp_file_name], check=True)
                logger.info("Paper cut command sent successfully")
                return True, "Paper cut successful"
            finally:
                try:
                    os.remove(temp_file_name)
                except:
                    pass
        except Exception as e:
            logger.error(f"Error sending cut command: {e}")
            return False, f"Error sending cut command: {str(e)}"

    def print_test_page(self, printer_type: str = "receipt") -> Tuple[bool, str]:
        """打印测试页"""
        try:
            if printer_type == "receipt" and not self.receipt_printer_available:
                return False, "Receipt printer not available"
            elif printer_type == "label" and not self.label_printer_available:
                return False, "Label printer not available"

            printer_name = self.settings.get(f"{printer_type}_printer", "")
            if not printer_name:
                return False, f"No {printer_type} printer selected"

            # 这里添加实际的打印测试页逻辑
            # 示例代码，需要根据实际打印机协议实现
            logger.info(f"Printing test page on {printer_name}")
            return True, "Test page sent to printer"

        except Exception as e:
            logger.error(f"Failed to print test page: {e}")
            return False, f"Error: {str(e)}"
