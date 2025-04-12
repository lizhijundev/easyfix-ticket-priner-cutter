# printer/manager.py
import os
import sys
import platform
import logging
import traceback
from typing import List, Tuple, Optional
from config.settings import Settings

from utils.logger import setup_logger

logger = setup_logger(__name__)

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
            self.receipt_printer_available = self.check_printer_availability("receipt")
            self.label_printer_available = self.check_printer_availability("label")
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
    
    def get_receipt_printers(self) -> List[str]:
        """获取小票打印机列表"""
        all_printers = self.get_all_printers()
        receipt_printers = [p for p in all_printers if "ReceiptPrinter" in p]
        logger.debug(f"Found receipt printers: {receipt_printers}")
        return receipt_printers
    
    def get_label_printers(self) -> List[str]:
        """获取标签打印机列表"""
        all_printers = self.get_all_printers()
        label_printers = [p for p in all_printers if "LabelPrinter" in p]
        logger.debug(f"XX Found label printers: {label_printers}")
        return label_printers

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
            import cups
            conn = cups.Connection()
            printers = conn.getPrinters()
            printer_list = list(printers.keys())
            logger.debug(f"Found macOS printers using pycups: {printer_list}")
            return printer_list
        except ImportError:
            logger.warning("cups module not available, falling back to subprocess method")
            return self._get_mac_printers_fallback()
        except Exception as e:
            logger.error(f"Failed to get macOS printers using pycups: {e}")
            return self._get_mac_printers_fallback()

    def _get_mac_printers_fallback(self) -> List[str]:
        """使用subprocess的备用方法获取打印机列表"""
        try:
            import subprocess
            output = subprocess.check_output(["lpstat", "-a"]).decode("utf-8")
            printers = [line.split()[0] for line in output.splitlines() if line]
            logger.debug(f"Found macOS printers (fallback): {printers}")
            return printers
        except Exception as e:
            logger.error(f"Failed to get macOS printers with fallback method: {e}")
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

            logger.info(f"1.Found {printer_type} printers: {printers}, printer_name: {printer_name}")

                
            # 首先检查打印机是否在列表中
            if printer_name not in printers:
                return False
                
            # 检查USB连接状态
            if self.system == "Windows":
                return self._check_windows_usb_printer(printer_name)
            elif self.system == "Darwin":  # macOS
                return self._check_mac_usb_printer(printer_name)
            else:  # Linux
                return self._check_linux_usb_printer(printer_name)
        except Exception as e:
            logger.error(f"Failed to check {printer_type} printer availability: {e}")
            return False

    def _check_windows_usb_printer(self, printer_name: str) -> bool:
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

    def _check_mac_usb_printer(self, printer_name: str) -> bool:
        """macOS系统检查USB打印机状态"""
        try:
            # 首先尝试使用cups库
            import cups
            try:
                conn = cups.Connection()
                printers = conn.getPrinters()
                
                # 检查打印机是否在连接的打印机列表中
                if printer_name not in printers:
                    logger.warning(f"Printer '{printer_name}' not found in the system")
                    return False
                    
                # 获取打印机状态
                printer_attrs = printers[printer_name]
                # cups状态码：3表示空闲(idle)，4表示正在处理(processing)，5表示停止(stopped)
                printer_state = printer_attrs.get("printer-state", 0)
                # 检查是否有错误状态
                printer_state_reasons = printer_attrs.get("printer-state-reasons", [])
                
                logger.debug(f"Printer '{printer_name}' state: {printer_state}, reasons: {printer_state_reasons}")
                
                # 如果打印机状态包含offline-report，表示打印机离线
                if "offline-report" in " ".join(printer_state_reasons):
                    logger.warning(f"Printer '{printer_name}' is offline")
                    return False

                # 如果状态为3(idle)或4(processing)且没有严重错误，则认为打印机可用
                if printer_state in [3, 4] and not any(reason.endswith("-error") for reason in printer_state_reasons):
                    return True
                return False

            except Exception as cups_error:
                logger.warning(f"Failed to check printer with cups: {cups_error}, falling back to subprocess")
                return self._check_mac_usb_printer_fallback(printer_name)

        except ImportError:
            logger.warning("cups module not available, falling back to subprocess")
            return self._check_mac_usb_printer_fallback(printer_name)

    def _check_mac_usb_printer_fallback(self, printer_name: str) -> bool:
        """使用subprocess备用方法检查macOS打印机状态"""
        try:
            import subprocess
            # 获取打印机状态
            result = subprocess.run(
                ["lpstat", "-p", printer_name],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return False

            # 如果输出中包含"idle"或"ready"表示打印机可用
            output = result.stdout.lower()
            return "idle" in output or "ready" in output
        except Exception as e:
            logger.error(f"Error checking macOS USB printer: {e}")
            return False

    def _check_linux_usb_printer(self, printer_name: str) -> bool:
        """Linux系统检查USB打印机状态"""
        try:
            import subprocess
            # 获取打印机状态
            result = subprocess.run(
                ["lpstat", "-p", printer_name],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                return False

            # 如果输出中包含"idle"表示打印机可用
            return "idle" in result.stdout.lower()
        except Exception as e:
            logger.error(f"Error checking Linux USB printer: {e}")
            return False

    def discover_printers(self) -> Tuple[bool, bool]:
        """发现可用打印机并更新状态"""
        logger.info("Discovering printers...")
        try:
            self.receipt_printer_available = self.check_printer_availability("receipt")
            self.label_printer_available = self.check_printer_availability("label")

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

            printer_name = self.settings.get("receipt_printer", "")
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


