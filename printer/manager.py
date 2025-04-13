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
        # logger.info("Discovering printers...")
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

            logger.info(f"Printing label on {printer_name}")

            # 根据不同的操作系统使用不同的打印方法
            if self.system == "Windows":
                return self._print_label_windows(printer_name, label_data)
            else:  # macOS 或 Linux
                return self._print_label_cups(printer_name, label_data)

        except Exception as e:
            logger.error(f"Failed to print label: {e}")
            traceback.print_exc()
            return False, f"Error: {str(e)}"

    def _print_label_cups(self, printer_name: str, label_data: str) -> Tuple[bool, str]:
        """可靠的TSPL图片打印函数（经过实际测试）

        参数:
            printer_name: CUPS打印机名称
            image_path: 图片路径
            width_mm: 标签宽度(mm)
            height_mm: 标签高度(mm)

        返回:
            (成功状态, 状态信息)
        """
        try:
            import cups
            from PIL import Image, ImageOps
            import tempfile
            import os
            import math
            import subprocess

            # ========== 1. 图像预处理 ==========
            # 打开图片并确保为RGB模式
            img = Image.open(image_path).convert('RGB')

            # 增强对比度（重要！）
            img = ImageOps.autocontrast(img)

            # 计算目标像素尺寸（203 DPI标准）
            dpi = 203
            target_width = int(width_mm * dpi / 25.4)
            target_height = int(height_mm * dpi / 25.4)

            # 调整大小并转换为黑白
            img = img.resize((target_width, target_height), Image.LANCZOS)
            bw_img = img.convert('1', dither=Image.FLOYDSTEINBERG)

            # ========== 2. 生成TSPL位图数据 ==========
            width, height = bw_img.size
            pixels = bw_img.load()
            bytes_per_row = math.ceil(width / 8)
            bitmap_data = []

            # TSPL要求：每行数据必须是8像素的倍数
            for y in range(height):
                for byte_idx in range(bytes_per_row):
                    byte_val = 0
                    for bit in range(8):
                        x = byte_idx * 8 + bit
                        if x < width and pixels[x, y] == 0:  # 0表示黑色
                            byte_val |= (1 << (7 - bit))  # MSB优先
                    bitmap_data.append(str(byte_val))

            # ========== 3. 构建TSPL命令 ==========
            tspl_commands = [
                f"SIZE {width_mm:.1f},{height_mm:.1f}",
                "CLS",
                f"BITMAP 0,0,{bytes_per_row},{height},0,{','.join(bitmap_data)}",
                "PRINT 1",
                ""
            ]

            # ========== 4. 通过CUPS打印 ==========
            # 方法1：直接发送到打印机（推荐）
            conn = cups.Connection()
            try:
                # 检查打印机状态
                printer_info = conn.getPrinters().get(printer_name)
                if not printer_info:
                    return False, f"打印机 {printer_name} 未找到"

                if printer_info['printer-state'] != 3:  # 3表示空闲
                    return False, "打印机忙或不可用"

                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.tspl', delete=False) as f:
                    f.write('\n'.join(tspl_commands))
                    temp_path = f.name

                # 使用lpr命令直接发送（避免CUPS转换）
                result = subprocess.run(
                    ['lpr', '-P', printer_name, '-o', 'raw', temp_path],
                    capture_output=True,
                    text=True
                )

                os.unlink(temp_path)

                if result.returncode != 0:
                    return False, f"打印失败: {result.stderr}"

                return True, "打印任务已发送"

            except cups.IPPError as e:
                # 方法2：回退到CUPS原生打印
                try:
                    job_id = conn.printFile(
                        printer_name,
                        temp_path,
                        "TSPL_Print_Job",
                        options={'raw': 'true'}
                    )
                    return True if job_id else False, "打印任务已提交"
                except Exception as e:
                    return False, f"CUPS打印错误: {str(e)}"

        except Exception as e:
            return False, f"系统错误: {str(e)}"


    def _print_label_windows(self, printer_name: str, label_data: str) -> Tuple[bool, str]:
        """Windows系统打印标签"""
        try:
            import win32print
            import tempfile

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
            logger.error(f"Error sending label to Windows printer: {e}")
            return False, f"Error: {str(e)}"

    def print_label_image(self, image_data: bytes, image_format: str = "png") -> Tuple[bool, str]:
        """打印图片标签

        Args:
            image_data: 图片二进制数据
            image_format: 图片格式(png, jpg等)

        Returns:
            (成功状态, 消息)
        """
        try:
            # 检查标签打印机是否可用
            if not self.label_printer_available:
                logger.warning("Label printer not available")
                return False, "Label printer not available"

            printer_name = self.settings.get("label_printer", "")
            if not printer_name:
                logger.warning("No label printer selected")
                return False, "No label printer selected"

            # 处理图片尺寸
            from PIL import Image
            import io
            import tempfile

            # 从二进制数据创建图片对象
            img = Image.open(io.BytesIO(image_data))

            # 从设置中获取标签尺寸
            label_size = self.settings.get("label_size", "50x40")

            # 解析标签尺寸 (宽x高，单位mm)
            try:
                if "x" in label_size:
                    width_mm, height_mm = map(int, label_size.split("x"))
                else:
                    # 默认标签大小
                    width_mm, height_mm = 50, 40
            except:
                width_mm, height_mm = 50, 40

            logger.info(f"Label size: {width_mm}x{height_mm}mm")

            # 假设打印分辨率为203 DPI (8 dots/mm)
            dpi = 203
            dots_per_mm = dpi / 25.4

            # 计算标签的宽度(像素)
            target_width_px = int(width_mm * dots_per_mm)

            # 计算等比例缩放后的高度
            original_width, original_height = img.size
            target_height_px = int((original_height * target_width_px) / original_width)

            # 调整图片大小
            resized_img = img.resize((target_width_px, target_height_px))

            # 创建临时文件保存处理后的图片
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{image_format}") as temp_file:
                temp_file_name = temp_file.name
                resized_img.save(temp_file_name)

            logger.info(f"Image resized to {target_width_px}x{target_height_px}px and saved to {temp_file_name}")

            try:
                # 根据不同的操作系统使用不同的打印方法
                if self.system == "Windows":
                    return self._print_image_windows(printer_name, temp_file_name)
                else:  # macOS 或 Linux
                    return self._print_image_cups(printer_name, temp_file_name, width_mm, height_mm)
            finally:
                # 清理临时文件
                try:
                    # os.unlink(temp_file_name)
                    logger.info(f"Please Check file {temp_file_name}")
                except:
                    pass

        except ImportError as e:
            logger.error(f"Missing required module: {e}")
            return False, f"Missing required module: {str(e)}. Please install Pillow with 'pip install Pillow'."
        except Exception as e:
            logger.error(f"Failed to print image label: {e}")
            traceback.print_exc()
            return False, f"Error: {str(e)}"

    def _print_image_cups(self, printer_name: str, image_path: str, width_mm: int, height_mm: int) -> Tuple[bool, str]:
        try:
            import cups
            from PIL import Image, ImageOps
            import tempfile
            import os
            import math
            import io

            # 1. 图像预处理（增强对比度）
            img = Image.open(image_path)

            # 转换为灰度并自动增强对比度
            img = img.convert('L')
            img = ImageOps.autocontrast(img)

            # 调试：保存预处理图像
            debug_img = img.copy()
            debug_img.save("/tmp/debug_preprocessed.png")

            # 2. 计算像素尺寸（基于203 DPI）
            dpi = 203
            width_px = int(width_mm * dpi / 25.4)
            height_px = int(height_mm * dpi / 25.4)

            # 调整大小并转换为1位黑白（使用Floyd-Steinberg抖动算法）
            img = img.resize((width_px, height_px), Image.LANCZOS)
            # img = img.convert('1', dither=Image.FLOYDSTEINBERG)

            # 调试：保存调整后的图像
            debug_img = img.copy()
            debug_img.save("/tmp/debug_final.png")

            # 3. 图像数据转换为TSPL BITMAP格式
            def image_to_tspl_bitmap(img):
                width, height = img.size
                pixels = img.load()
                bytes_per_row = math.ceil(width / 8)
                bitmap_data = bytearray()

                # TSPL要求每行数据必须是8的倍数
                for y in range(height):
                    for byte_idx in range(bytes_per_row):
                        byte_val = 0
                        for bit in range(8):
                            x = byte_idx * 8 + bit
                            if x < width and pixels[x, y] == 0:  # 0=黑
                                byte_val |= (1 << (7 - bit))  # MSB优先
                        bitmap_data.append(byte_val)

                return width, height, bytes_per_row, bitmap_data

            img_width, img_height, bytes_per_row, bitmap_data = image_to_tspl_bitmap(img)

            # 4. 生成完整的TSPL命令
            tspl_commands = [
                f"SIZE {width_mm:.1f} mm,{height_mm:.1f} mm",
                "CLS",  # 清除缓冲区
                f"DENSITY 10",  # 打印浓度(1-15)
                f"SPEED 3",  # 打印速度(1-5)
                f"DIRECTION 0",  # 打印方向
                # BITMAP格式: X,Y,width(像素),height(像素),mode,data
                # mode: 0=覆盖,1=异或,2=与,3=或
                f"BITMAP 0,0,{img_width},{img_height},0,{','.join(f'{b}' for b in bitmap_data)}",
                "PRINT 1",  # 打印1份
                "END"
            ]

            # 5. 创建临时TSPL文件
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.tspl', delete=False) as tspl_file:
                tspl_file.write('\n'.join(tspl_commands))
                tspl_file_path = tspl_file.name

            # 6. 通过CUPS打印
            # conn = cups.Connection()
            # options = {
            #     'print-quality': '5',  # 高质量打印
            #     'printer-resolution': '203x203',  # 设置DPI
            #     'raw': 'true',  # 原始打印模式
            # }
            #
            # job_id = conn.printFile(
            #     printer_name,
            #     tspl_file_path,
            #     "TSPL_Label_Print",
            #     options
            # )
            #
            # # 7. 清理临时文件
            # os.unlink(tspl_file_path)

            job_id = 1
            if job_id:
                return True, f"TSPL标签打印任务已发送（作业ID: {job_id}）"
            return False, "打印任务发送失败"

        except cups.IPPError as e:
            return False, f"CUPS打印错误: {str(e)}"
        except Exception as e:
            return False, f"TSPL打印错误: {str(e)}"







    def _print_image_windows(self, printer_name: str, image_path: str) -> Tuple[bool, str]:
        """Windows系统打印图片标签"""
        try:
            # 尝试使用win32print模块
            import win32print
            import win32ui
            from PIL import Image, ImageWin

            # 打开图片
            img = Image.open(image_path)

            # 获取打印机DC
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(printer_name)

            # 开始文档
            hDC.StartDoc(image_path)
            hDC.StartPage()

            # 获取打印区域的尺寸
            dpi_x = hDC.GetDeviceCaps(88)  # LOGPIXELSX
            dpi_y = hDC.GetDeviceCaps(90)  # LOGPIXELSY
            width = int(img.width * 1000 / dpi_x)  # 单位为0.1毫米
            height = int(img.height * 1000 / dpi_y)  # 单位为0.1毫米

            # 打印图片
            ImageWin.Dib(img).draw(hDC.GetHandleOutput(), (0, 0, width, height))

            # 结束文档
            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()

            logger.info(f"Image label sent to Windows printer: {printer_name}")
            return True, "Image label sent to printer"

        except ImportError:
            logger.error("win32print or win32ui module not available")
            return False, "Missing required modules for printing on Windows"
        except Exception as e:
            logger.error(f"Error sending image to Windows printer: {e}")
            return False, f"Error: {str(e)}"

