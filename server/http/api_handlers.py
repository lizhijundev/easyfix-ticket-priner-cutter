# server/http/api_handlers.py
import traceback
import io
import os
from flask import request, jsonify
from utils.logger import setup_logger
from config.settings import Settings
from PIL import Image, ImageDraw, ImageFont
from unidecode import unidecode
import re

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

            required_fields = ['qr_url', 'time', 'user', 'device', 'fault_data', 'notice', 'extra']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'code': 400,
                        'message': f"Missing required field: {field}"
                    }), 400

            # Format engineer order label content
            tspl_commands = self._format_engineer_order_label(data)
            
            # Print label
            rs, message = self.printer.print_label_TSPL(tspl_commands)

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

    def remove_punctuation(self, text):
        """
        对 TSPL 命令中的特殊字符进行转义
        """
        # 定义需要转义的特殊字符
        escape_mapping = {
            '\\': '\\\\',  # 转义反斜杠
            '"': '\\"',    # 转义双引号
            '\'': '\\\'',  # 转义单引号
            ',': '|',    # 转义逗号
        }

        # 遍历字符串，将特殊字符替换为转义后的字符
        escaped_text = "".join(escape_mapping.get(char, char) for char in text)
        return escaped_text

    def _calc_block_size(self, text, font_width, font_height, container_width):
        """Calculate the size of the text block"""
        # 转义文本中的特殊字符，比如逗号
        text = self.remove_punctuation(text)
        text = unidecode(text)

        word_count = len(text)
        # Calculate the number of lines needed to fit the text
        lines = (word_count * font_width) // container_width + 1
        # Calculate the height of the text block
        container_height = lines * font_height
        return text, container_width, container_height


    
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
            
            # 203dpi 转换为 mm
            dpi = 203
            mm_to_dpi = 25.4 / dpi
            # 计算标签尺寸
            label_width = int(width_mm / mm_to_dpi)
            label_height = int(height_mm / mm_to_dpi)
            
            # 定义常量
            font = "\"TSS24.BF2\""
            font_width = 14
            font_height = 24
            common_padding = 10
            line_bottom = 3
            qr_code_size = 80
            max_usable_height = label_height - common_padding * 2  # 可用高度，去除上下边距
            
            # 存储所有标签的TSPL命令
            all_labels_commands = []
            
            # 初始标签基本设置命令
            label_init_commands = [
                f"SIZE {width_mm} mm,{height_mm} mm",
                "GAP 2 mm,0 mm",
                "DIRECTION 1",
                "DENSITY 8",
                "SPEED 6",
                "CLS"
            ]
            
            current_label_commands = label_init_commands.copy()
            y_offset = common_padding  # 初始y偏移设为上边距
            
            # 打印二维码 (仅第一张标签)
            qr_code_x = int(label_width - qr_code_size - common_padding)
            qr_code_y = int(common_padding)
            qr_code_data = data.get('qr_url', '')
            current_label_commands.append(f"QRCODE {qr_code_x},{qr_code_y},H,2,A,0,\"{qr_code_data}\"")
            
            # 预处理要打印的内容项
            content_items = []
            
            # 添加时间信息
            label_time = data.get('time', '')
            text, block_width, block_height = self._calc_block_size(label_time, font_width, font_height, 
                                                               label_width - common_padding * 2 - qr_code_size)
            content_items.append({
                'text': text, 
                'width': block_width, 
                'height': block_height, 
                'indent': 0,
                'type': 'normal'
            })
            
            # 添加用户信息
            label_user = data.get('user', '')
            text, block_width, block_height = self._calc_block_size(label_user, font_width, font_height, 
                                                              label_width - common_padding * 2 - qr_code_size)
            content_items.append({
                'text': text, 
                'width': block_width, 
                'height': block_height, 
                'indent': 0,
                'type': 'normal'
            })
            
            # 添加设备信息
            label_device = data.get('device', '')
            text, block_width, block_height = self._calc_block_size(label_device, font_width, font_height, 
                                                              label_width - common_padding * 2 - qr_code_size)
            content_items.append({
                'text': text, 
                'width': block_width,
                'height': block_height, 
                'indent': 0,
                'type': 'normal'
            })
            
            # 添加分隔线
            content_items.append({
                'type': 'separator',
                'width': label_width - common_padding * 2 - qr_code_size - 10,
                'height': 2 + line_bottom
            })
            
            # 添加故障信息
            fault_data = data.get('fault_data', [])
            if fault_data and isinstance(fault_data, list):
                for i, fault in enumerate(fault_data):
                    fault_name = fault.get('fault_name', f'{i+1}')
                    text, block_width, block_height = self._calc_block_size(fault_name, font_width, font_height, 
                                                                      label_width - common_padding * 2)
                    content_items.append({
                        'text': text, 
                        'width': block_width, 
                        'height': block_height, 
                        'indent': 0,
                        'type': 'normal'
                    })
                    
                    # 添加故障处理计划
                    if 'fault_plan' in fault and isinstance(fault['fault_plan'], list):
                        for plan in fault['fault_plan']:
                            text, block_width, block_height = self._calc_block_size(f"- {plan}", font_width, font_height,
                                                                             label_width - common_padding * 2 - 10)
                            content_items.append({
                                'text': text, 
                                'width': block_width, 
                                'height': block_height, 
                                'indent': 10,  # 缩进10单位
                                'type': 'normal'
                            })
            
            # 添加分隔线
            content_items.append({
                'type': 'separator',
                'width': label_width - common_padding * 2,
                'height': 2 + line_bottom
            })
            
            # 添加注意事项
            notice = data.get('notice', [])
            if notice and isinstance(notice, list):
                for notice_item in notice:
                    text, block_width, block_height = self._calc_block_size(notice_item, font_width, font_height, 
                                                                     label_width - common_padding * 2)
                    content_items.append({
                        'text': text, 
                        'width': block_width, 
                        'height': block_height, 
                        'indent': 0,
                        'type': 'normal'
                    })

            
            # 添加额外信息
            extra = data.get('extra', [])
            if extra and isinstance(extra, list):
                for extra_item in extra:
                    text, block_width, block_height = self._calc_block_size(extra_item, font_width, font_height, 
                                                                     label_width - common_padding * 2)
                    content_items.append({
                        'text': text, 
                        'width': block_width, 
                        'height': block_height, 
                        'indent': 0,
                        'type': 'normal'
                    })
            
            # 遍历所有内容项，根据高度自动分页
            for item in content_items:
                item_height = item['height']
                
                # 检查当前项是否会超出当前标签的可用高度
                if y_offset + item_height > max_usable_height:
                    # 完成当前标签
                    current_label_commands.append("PRINT 1")
                    current_label_commands.append("END")
                    all_labels_commands.extend(current_label_commands)
                    
                    # 创建新标签
                    current_label_commands = label_init_commands.copy()
                    y_offset = common_padding  # 重置y偏移量
                
                # 添加当前项到标签
                if item['type'] == 'separator':
                    item_width = item['width']
                    current_label_commands.append(f"BAR {common_padding},{y_offset},{item_width},{item_height - line_bottom}")
                else:
                    indent = item.get('indent', 0)
                    x_position = common_padding + indent
                    current_label_commands.append(f"BLOCK {x_position},{y_offset},{item['width']},{item['height']},{font},0,1,1,\"{item['text']}\"")
                
                # 更新y偏移量
                y_offset += item_height
            
            # 完成最后一张标签
            current_label_commands.append("PRINT 1")
            current_label_commands.append("END")
            all_labels_commands.extend(current_label_commands)
            
            return all_labels_commands

        except Exception as e:
            logger.error(f"Error formatting engineer order label: {e}")
            traceback.print_exc()
            return f"Error: Could not format engineer order - {str(e)}"

