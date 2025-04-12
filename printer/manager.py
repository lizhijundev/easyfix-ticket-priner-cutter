# printer/manager.py
import platform
import traceback
from utils.logger import setup_logger

logger = setup_logger()

class PrinterManager:
    def __init__(self):
        try:
            self.system = platform.system()
            self.printers = []
            logger.info("Printer manager initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize printer manager: {e}")
            traceback.print_exc()
            raise

    def discover_printers(self):
        """发现系统中的打印机"""
        try:
            logger.info("Starting to discover system printers")
            if self.system == "Windows":
                self._discover_windows_printers()
            elif self.system == "Darwin":  # macOS
                self._discover_mac_printers()
            else:  # Linux
                self._discover_linux_printers()

            logger.info(f"Found {len(self.printers)} printers")
            return self.printers
        except Exception as e:
            logger.error(f"Failed to discover printers: {e}")
            traceback.print_exc()
            return []

    def _discover_windows_printers(self):
        """查找Windows系统中的打印机"""
        try:
            import win32print
            self.printers = [printer[2] for printer in win32print.EnumPrinters(2)]
            logger.info(f"Windows printers: {', '.join(self.printers)}")
        except ImportError:
            logger.warning("Cannot import win32print module, please install pywin32")
            self.printers = ["Demo Printer 1", "Demo Printer 2"]
        except Exception as e:
            logger.error(f"Failed to discover Windows printers: {e}")
            traceback.print_exc()
            self.printers = ["Demo Printer 1", "Demo Printer 2"]

    def _discover_mac_printers(self):
        """查找macOS系统中的打印机"""
        try:
            import subprocess
            result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            self.printers = []
            for line in lines:
                if line.startswith("printer "):
                    self.printers.append(line.split()[1])

            if not self.printers:
                logger.warning("No Mac printers found, using demo printers")
                self.printers = ["Demo Printer 1", "Demo Printer 2"]

            logger.info(f"Mac printers: {', '.join(self.printers)}")
        except Exception as e:
            logger.error(f"Failed to discover Mac printers: {e}")
            traceback.print_exc()
            self.printers = ["Demo Printer 1", "Demo Printer 2"]

    def _discover_linux_printers(self):
        """查找Linux系统中的打印机"""
        try:
            import subprocess
            result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            self.printers = []
            for line in lines:
                if line.startswith("printer "):
                    self.printers.append(line.split()[1])

            if not self.printers:
                logger.warning("No Linux printers found, using demo printers")
                self.printers = ["Demo Printer 1", "Demo Printer 2"]

            logger.info(f"Linux printers: {', '.join(self.printers)}")
        except Exception as e:
            logger.error(f"Failed to discover Linux printers: {e}")
            traceback.print_exc()
            self.printers = ["Demo Printer 1", "Demo Printer 2"]

    def get_all_printers(self):
        """获取所有打印机列表"""
        if not self.printers:
            self.discover_printers()
        return self.printers

    def print_label(self, printer_name, content):
        """打印标签"""
        try:
            logger.info(f"Printing label to {printer_name}: {content}")
            # 实际打印逻辑将在此实现
            return True
        except Exception as e:
            logger.error(f"Failed to print label: {e}")
            traceback.print_exc()
            return False

    def print_ticket(self, printer_name, content):
        """打印小票"""
        try:
            logger.info(f"Printing receipt to {printer_name}: {content}")
            # 实际打印逻辑将在此实现
            return True
        except Exception as e:
            logger.error(f"Failed to print receipt: {e}")
            traceback.print_exc()
            return False
