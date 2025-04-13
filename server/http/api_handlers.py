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
    def __init__(self, printer_manager):
        self.printer_manager = printer_manager

    def handle_print_label(self):
        """Handle label printing request"""
        try:
            # Check if label printer is available
            if not self.printer_manager.is_label_printer_available():
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
            rs, message = self.printer_manager.print_label(data['content'])

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
            if not self.printer_manager.is_receipt_printer_available():
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
            success = self.printer_manager.print_receipt(data['content'])

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
            if not self.printer_manager.is_label_printer_available():
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
            success, message = self.printer_manager.print_label_image(image_data, file_ext)

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
                is_available = self.printer_manager.is_label_printer_available()
                # Force refresh printer status
                self.printer_manager.check_printer_availability('label')
                status_msg = "Label printer is connected" if is_available else "Label printer is disconnected"
            else:  # receipt
                is_available = self.printer_manager.is_receipt_printer_available()
                # Force refresh printer status
                self.printer_manager.check_printer_availability('receipt')
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
