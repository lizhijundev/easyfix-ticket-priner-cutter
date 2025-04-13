# server/http/api_handlers.py
import traceback
import io
import os
from flask import request, jsonify
from utils.logger import setup_logger

logger = setup_logger()

class APIHandlers:
    """
    API request handlers for printer operations
    """
    def __init__(self, printer):
        self.printer = printer

    def handle_print_label(self):
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
            rs, message = self.printer.print_label(data['content'])

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
            if not self.printer.is_label_printer_available():
                return jsonify({
                    'code': 300,
                    'message': "Label printer not available"
                })

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
            label_content = self._format_engineer_order_label(data)
            
            # Print label
            rs, message = self.printer.print_label(label_content)

            # Return result
            return jsonify({
                'code': 0 if rs else 400,
                'message': "Engineer order label printed successfully" if rs else message
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
            # 构建标签内容
            label_lines = []
            
            # 添加时间和用户信息
            label_lines.append(f"时间: {data.get('time', '')}")
            label_lines.append(f"用户: {data.get('user', '')}")
            label_lines.append(f"设备: {data.get('device', '')}")
            label_lines.append("-" * 40)  # 分隔线
            
            # 添加故障数据
            if 'fault_data' in data and isinstance(data['fault_data'], list):
                label_lines.append("故障信息:")
                for i, fault in enumerate(data['fault_data']):
                    fault_name = fault.get('fault_name', f'故障 {i+1}')
                    label_lines.append(f"{i+1}. {fault_name}")
                    
                    # 添加故障处理计划
                    if 'fault_plan' in fault and isinstance(fault['fault_plan'], list):
                        for j, plan in enumerate(fault['fault_plan']):
                            label_lines.append(f"   - {plan}")
            
            label_lines.append("-" * 40)  # 分隔线
            
            # 添加注意事项
            if 'notice' in data and isinstance(data['notice'], list):
                label_lines.append("注意事项:")
                for i, notice in enumerate(data['notice']):
                    label_lines.append(f"* {notice}")
            
            # 合并所有行并返回
            return "\n".join(label_lines)
        except Exception as e:
            logger.error(f"Error formatting engineer order label: {e}")
            return f"Error: Could not format engineer order - {str(e)}"

