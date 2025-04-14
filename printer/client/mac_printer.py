import cups
import tempfile
import os
import traceback
from typing import List, Tuple, Optional
from utils.logger import setup_logger
from config.settings import Settings


logger = setup_logger(__name__)

RECEIPT_PRINTER_NAME = "ReceiptPrinter"
LABEL_PRINTER_NAME = "LabelPrinter"

class MacPrinter:
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
        # logger.info("Discovering printers...")
        try:
            self.receipt_printer_available = self.check_printer_availability("receipt")
            self.label_printer_available = self.check_printer_availability("label")
            # logger.info(f"Discovered printers - Receipt: {self.receipt_printer_available}, Label: {self.label_printer_available}")
            return self.receipt_printer_available, self.label_printer_available
        except Exception as e:
            # logger.error(f"Failed to discover printers: {e}")
            traceback.print_exc()
            return False, False

    def get_all_printers(self) -> List[str]:
        try:
            conn = cups.Connection()
            printers = conn.getPrinters()
            printer_list = list(printers.keys())
            logger.debug(f"Found macOS printers using pycups: {printer_list}")
            return printer_list
        except ImportError:
            logger.warning("cups module not available, falling back to subprocess method")
            return self._get_printers_fallback()
        except Exception as e:
            logger.error(f"Failed to get macOS printers using pycups: {e}")
            return self._get_printers_fallback()


    def _get_printers_fallback(self) -> List[str]:
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


    def _check_usb_printer(self, printer_name: str) -> bool:
        """macOS系统检查USB打印机状态"""
        try:
            # 首先尝试使用cups库
            try:
                conn = cups.Connection()
                printers = conn.getPrinters()

                # 检查打印机是否在连接的打印机列表中
                if (printer_name not in printers):
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
                    # logger.warning(f"Printer '{printer_name}' is offline")
                    return False

                # 如果状态为3(idle)或4(processing)且没有严重错误，则认为打印机可用
                if printer_state in [3, 4] and not any(reason.endswith("-error") for reason in printer_state_reasons):
                    return True
                return False

            except Exception as cups_error:
                logger.warning(f"Failed to check printer with cups: {cups_error}, falling back to subprocess")
                return self._check_usb_printer_fallback(printer_name)

        except ImportError:
            logger.warning("cups module not available, falling back to subprocess")
            return self._check_usb_printer_fallback(printer_name)


    def _check_usb_printer_fallback(self, printer_name: str) -> bool:
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

            conn = cups.Connection()

            # ESC/POS 切纸命令
            cut_command = b'\x1D\x56\x00'

            # 检查打印机状态
            printer_info = conn.getPrinters().get(printer_name)
            if not printer_info:
                return False, f"打印机 {printer_name} 未找到"

            if printer_info['printer-state'] != 3:  # 3表示空闲
                return False, "打印机忙或不可用"

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(cut_command)
                temp_file_path = temp_file.name

            # 使用 CUPS 打印临时文件
            conn.printFile(printer_name, temp_file_path,
                           "Cut Command", {"raw": "true"})

            os.remove(temp_file_path)
            logger.info("Paper cut command sent successfully")
            return True, "Paper cut successful"
        except Exception as e:
            logger.error(f"Error during manual paper cut: {e}")
            return False, f"Failed to cut paper: {str(e)}"


    def print_label(self, label_data: str) -> Tuple[bool, str]:
        """打印标签"""
        try:
            if not self.label_printer_available:
                logger.warning("Label printer not available")
                return False, "Label printer not available"

            printer_name = self.settings.get("label_printer", "")
            if not printer_name:
                logger.warning("No label printer selected")
                return False, "No label printer selected"

            conn = cups.Connection()
            # 检查打印机状态
            printer_info = conn.getPrinters().get(printer_name)
            if not printer_info:
                logger.error(f"Can't find printer [{printer_name}]")
                return False, f"Can't find printer [{printer_name}]"

            # 打印详细的打印机状态信息，帮助调试
            logger.info(f"Printer {printer_name} status: {printer_info['printer-state']}, "
                       f"state-message: {printer_info.get('printer-state-message', '')}, "
                       f"reasons: {printer_info.get('printer-state-reasons', [])}")

            if printer_info['printer-state'] != 3:  # 3表示空闲
                logger.warning(f"Printer state is {printer_info['printer-state']}, not ready (3=idle)")
                return False, "Printer is busy or unavailable"

            # ESC/POS 切纸命令
            tspl_command = [
                "SIZE 50 mm,40 mm",
                "GAP 2 mm,0",
                "DIRECTION 1",
                "CLS",
                f"TEXT 10,20,\"2\",0,1,1,\"{label_data}\"",
                "PRINT 1",
                "END"
            ]

            options = {
                "raw": "true",
                "media": "Custom.50x40mm",
            }

            # 创建临时文件保存标签数据
            temp_file_path = "/tmp/tspl_job.txt"
            try:
                with open(temp_file_path, "w") as f:
                    f.write("\r\n".join(tspl_command))

                logger.info(f"TSPL commands written to temp file: {temp_file_path}")
                logger.debug(f"TSPL content: {tspl_command}")

                # 使用 CUPS 打印临时文件
                job_id = conn.printFile(
                    printer_name,
                    temp_file_path,
                    "Label Print",
                    options
                )

                logger.info(f"Printing job sent with ID: {job_id}")

                if job_id:
                    logger.info(f"TSPL print job sent to {printer_name}, job ID: {job_id}")
                    return True, f"TSPL label sent to printer (Job ID: {job_id})"
                else:
                    logger.error("Failed to send TSPL print job, no job ID returned")
                    return False, "Failed to send TSPL print job"

            finally:
                pass
            #     # 确保临时文件被删除
            #     if temp_file_path and os.path.exists(temp_file_path):
            #         try:
            #             os.unlink(temp_file_path)
            #             logger.debug(f"Temporary file {temp_file_path} removed")
            #         except Exception as e:
            #             logger.warning(f"Failed to delete temporary file: {e}")

        except cups.IPPError as ipp_err:
            error_code, error_message = ipp_err.args
            logger.error(f"IPP Error {error_code}: {error_message}")
            return False, f"Printer error: {error_message}"
        except Exception as e:
            logger.error(f"Failed to print label: {e}")
            traceback.print_exc()
            return False, f"Error: {str(e)}"

