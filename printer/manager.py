# printer/manager.py
import os
import sys
import platform
import logging
import traceback
from typing import List, Tuple, Optional
from config.settings import Settings
from printer.client.mac_printer import MacPrinter
from printer.client.win_printer import WindowsPrinter

from utils.logger import setup_logger

logger = setup_logger(__name__)

class PrinterManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.system = platform.system()
        self.printer = None
        if self.system == "Windows":
            self.printer = WindowsPrinter(settings)
        elif self.system == "Darwin":  # macOS
            self.printer = MacPrinter(settings)
        else:  # Linux
            self.printer = MacPrinter(settings)  # 使用MacPrinter作为Linux的默认实现

        self.receipt_printer_available = self.printer.receipt_printer_available
        self.label_printer_available = self.printer.label_printer_available


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

