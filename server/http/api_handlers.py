# server/http/api_handlers.py
import traceback
import io
import os
from flask import request, jsonify
from utils.logger import setup_logger
from config.settings import Settings
from PIL import Image, ImageDraw, ImageFont

logger = setup_logger()

class APIHandlers:
    """
    API request handlers for printer operations
    """
    def __init__(self, printer):
        self.printer = printer

    def handle_print_label_text(self):
        """Handle label printing request"""
        try:
            # Check if label printer is available
            if not self.printer.is_label_printer_available():
                return jsonify({
                    'code': 300,
                    'message': "Label printer not available"
                })

            # Parse request data
            data = request.get_json()
            
            # Check required fields
            if not data or 'content' not in data:
                return jsonify({
                    'code': 400,
                    'message': "Missing content field"
                }), 400

            # Print label
            rs, message = self.printer.print_label_text(data['content'])

            # Return result
            return jsonify({
                'code': 0 if rs else 400,
                'message': "Label printed successfully" if rs else message
            })
        except Exception as e:
            logger.error(f"Error handling label print request: {e}")
            traceback.print_exc()
            return jsonify({
                'code': 500,
                'message': f"Error processing label print request: {str(e)}"
            }), 500

    def handle_print_receipt(self):
        """Handle receipt printing request"""
        # todo: 待实现
        try:
            # Check if receipt printer is available
            if not self.printer.is_receipt_printer_available():
                return jsonify({
                    'code': 300,
                    'message': "Receipt printer not available"
                })

            # Parse request data
            data = request.get_json()
            
            # Check required fields
            if not data or 'content' not in data:
                return jsonify({
                    'code': 400,
                    'message': "Missing content field"
                }), 400

            # Print receipt
            success = self.printer.print_receipt(data['content'])

            # Return result
            return jsonify({
                'code': 0 if success else 400,
                'message': "Receipt printed successfully" if success else "Failed to print receipt"
            })
        except Exception as e:
            logger.error(f"Error handling receipt print request: {e}")
            traceback.print_exc()
            return jsonify({
                'code': 500,
                'message': f"Error processing receipt print request: {str(e)}"
            }), 500

    def handle_print_label_img(self):
        """Handle image label printing request"""
        try:
            # Check if label printer is available
            if not self.printer.is_label_printer_available():
                return jsonify({
                    'code': 300,
                    'message': "Label printer not available"
                })

            # Check if image file exists in request
            if 'image' not in request.files:
                return jsonify({
                    'code': 400,
                    'message': "Missing image file"
                }), 400

            # Get image file
            image_file = request.files['image']
            if not image_file.filename:
                return jsonify({
                    'code': 400,
                    'message': "Invalid image file"
                }), 400

            # Get file format
            file_ext = os.path.splitext(image_file.filename)[1].lower().lstrip('.')
            if not file_ext or file_ext not in ['png', 'jpg', 'jpeg', 'bmp', 'gif']:
                file_ext = 'png'  # Default format

            # Read image data
            image_data = image_file.read()
            
            logger.info(f"Received image file: {image_file.filename}, size: {len(image_data)} bytes")

            # Print image label
            success, message = self.printer.print_label_image(image_data, file_ext)

            # Return result
            return jsonify({
                'code': 0 if success else 400,
                'message': "Image label printed successfully" if success else message
            })
        except Exception as e:
            logger.error(f"Error processing image label print request: {e}")
            traceback.print_exc()
            return jsonify({
                'code': 500,
                'message': f"Error processing image label print request: {str(e)}"
            }), 500

    def handle_printer_status(self):
        """Handle printer status query"""
        try:
            # Get printer type from query parameters
            printer_type = request.args.get('printer_type', 'label')
            
            # Validate printer_type
            if printer_type not in ['label', 'receipt']:
                return jsonify({
                    'code': 400,
                    'message': "Invalid printer_type. Must be 'label' or 'receipt'"
                }), 400
            
            # Check printer status
            if printer_type == 'label':
                is_available = self.printer.is_label_printer_available()
                # Force refresh printer status
                self.printer.check_printer_availability('label')
                status_msg = "Label printer is connected" if is_available else "Label printer is disconnected"
            else:  # receipt
                is_available = self.printer.is_receipt_printer_available()
                # Force refresh printer status
                self.printer.check_printer_availability('receipt')
                status_msg = "Receipt printer is connected" if is_available else "Receipt printer is disconnected"
            
            # Return printer status
            return jsonify({
                'code': 0,
                'message': status_msg,
                'data': {
                    'printer_type': printer_type,
                    'is_connected': is_available
                }
            })
        except Exception as e:
            logger.error(f"Error handling printer status query: {e}")
            traceback.print_exc()
            return jsonify({
                'code': 500,
                'message': f"Error processing printer status query: {str(e)}"
            }), 500

    def handle_print_engineer_order(self):
        """Handle engineer order label printing request"""
        try:
            # Check if label printer is available
            # if not self.printer.is_label_printer_available():
            #     return jsonify({
            #         'code': 300,
            #         'message': "Label printer not available"
            #     })

            # Parse request data
            data = request.get_json()
            
            # Check required fields
            if not data:
                return jsonify({
                    'code': 400,
                    'message': "Missing request data"
                }), 400

            required_fields = ['logo', 'qr_url', 'time', 'user', 'device', 'fault_data', 'notice', 'extra']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f"Missing required field: {field}"
                    }), 400

            # Format engineer order label content
            label_image_path = self._format_engineer_order_label(data)
            
            # Print label
            rs, message = self.printer.print_label_image(label_image_path)

            rs = True
            # Return result
            return jsonify({
                'code': 0 if rs else 400,
                'message': message if rs else message
            })
        except Exception as e:
            logger.error(f"Error handling engineer order label print request: {e}")
            traceback.print_exc()
            return jsonify({
                'code': 500,
                'message': f"Error processing engineer order label print request: {str(e)}"
            }), 500
    
    def _format_engineer_order_label(self, data):
        """Format engineering order data into label content"""
        try:
            settings = Settings()
            # 从设置中获取标签尺寸
            label_size = settings.get("label_size", "50x40")

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
            # 2. 计算像素尺寸（基于203 DPI）
            dpi = 203
            width_px = int(width_mm * dpi / 25.4)
            height_px = int(height_mm * dpi / 25.4)
            logger.info(f"Label size: {width_px}x{height_px}px")

            # 加载字体
            try:
                font_16 = ImageFont.truetype(os.getcwd() + '/fonts/NotoSansSC-SemiBold.ttf', 16)
            except IOError:
                font_16 = ImageFont.load_default()


            # 绘制一张空白的标签， 50mm x 40mm
            label_canvas = Image.new('RGB', (width_px, height_px), color='white')
            draw = ImageDraw.Draw(label_canvas)


            # # 添加logo
            # if 'logo' in data and data['logo']:
            #     logo = Image.open(io.BytesIO(data['logo']))
            #     logo = logo.resize((100, 100), Image.ANTIALIAS)
            #     label_canvas.paste(logo, (10, 10))
            # # 添加二维码
            # if 'qr_url' in data and data['qr_url']:
            #     qr_code = qrcode.make(data['qr_url'])
            #     qr_code = qr_code.resize((100, 100), Image.ANTIALIAS)
            #     label_canvas.paste(qr_code, (400, 10))
            # 添加其他信息
            # 添加标题
            draw.text((10, 5), "Easyfix.vn", fill="black", font=font_16)
            # 添加额外信息
            if 'extra' in data and isinstance(data['extra'], list):
                for i, extra in enumerate(data['extra']):
                    draw.text((10, 120 + i * 20), extra, fill="black", font=font_16)
            # 添加分隔线
            draw.line((0, 50, 500, 50), fill="black", width=2)
            # 添加标签内容
            # 添加时间、用户、设备等信息
            draw.text((10, 110), f"时间: {data.get('time', '')}", fill="black", font=font_16)
            draw.text((10, 140), f"用户: {data.get('user', '')}", fill="black", font=font_16)
            draw.text((10, 170), f"设备: {data.get('device', '')}", fill="black", font=font_16)
            # 添加故障信息
            if 'fault_data' in data and isinstance(data['fault_data'], list):
                draw.text((10, 200), "故障信息:", fill="black", font=font_16)
                for i, fault in enumerate(data['fault_data']):
                    fault_name = fault.get('fault_name', f'故障 {i+1}')
                    draw.text((20, 220 + i * 20), f"{i+1}. {fault_name}", fill="black", font=font_16)
                    # 添加故障处理计划
                    if 'fault_plan' in fault and isinstance(fault['fault_plan'], list):
                        for j, plan in enumerate(fault['fault_plan']):
                            draw.text((40, 240 + (i + j) * 20), f"   - {plan}", fill="black", font=font_16)
            # 添加注意事项
            if 'notice' in data and isinstance(data['notice'], list):
                draw.text((10, 300), "注意事项:", fill="black", font=font_16)
                for i, notice in enumerate(data['notice']):
                    draw.text((20, 320 + i * 20), f"* {notice}", fill="black", font=font_16)
            # 保存标签内容为图片，并输出路径
            label_image_path = os.path.join(os.getcwd(), 'engineer_order_label.png')
            label_canvas.save(label_image_path)
            # 返回标签图片路径
            return label_image_path



            # # 构建标签内容
            # label_lines = []
            #
            # # 添加时间和用户信息
            # label_lines.append(f"时间: {data.get('time', '')}")
            # label_lines.append(f"用户: {data.get('user', '')}")
            # label_lines.append(f"设备: {data.get('device', '')}")
            # label_lines.append("-" * 40)  # 分隔线
            #
            # # 添加故障数据
            # if 'fault_data' in data and isinstance(data['fault_data'], list):
            #     label_lines.append("故障信息:")
            #     for i, fault in enumerate(data['fault_data']):
            #         fault_name = fault.get('fault_name', f'故障 {i+1}')
            #         label_lines.append(f"{i+1}. {fault_name}")
            #
            #         # 添加故障处理计划
            #         if 'fault_plan' in fault and isinstance(fault['fault_plan'], list):
            #             for j, plan in enumerate(fault['fault_plan']):
            #                 label_lines.append(f"   - {plan}")
            #
            # label_lines.append("-" * 40)  # 分隔线
            #
            # # 添加注意事项
            # if 'notice' in data and isinstance(data['notice'], list):
            #     label_lines.append("注意事项:")
            #     for i, notice in enumerate(data['notice']):
            #         label_lines.append(f"* {notice}")
            #
            # # 合并所有行并返回
            # return "\n".join(label_lines)
        except Exception as e:
            logger.error(f"Error formatting engineer order label: {e}")
            return f"Error: Could not format engineer order - {str(e)}"

