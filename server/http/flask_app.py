# server/http/flask_app.py
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from server.http.api_handlers import APIHandlers
from server.http.templates import Templates
from utils.logger import setup_logger

logger = setup_logger()

def create_flask_app(printer):
    """
    Creates and configures a Flask application
    """
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    api_handlers = APIHandlers(printer)
    
    # Status pages
    @app.route('/', methods=['GET'])
    @app.route('/status', methods=['GET'])
    def status_page():
        return render_template_string(Templates.get_status_html())
    
    # API routes
    @app.route('/api/print/status', methods=['GET'])
    def printer_status():
        return api_handlers.handle_printer_status()
    
    @app.route('/api/print/label/text', methods=['POST'])
    def print_label():
        return api_handlers.handle_print_label_text()

    @app.route('/api/print/label/engineer_order', methods=['POST'])
    def print_engineer_order():
        return api_handlers.handle_print_engineer_order()
    
    @app.route('/api/print/receipt', methods=['POST'])
    def print_receipt():
        return api_handlers.handle_print_receipt()
    
    @app.route('/api/print/label_img', methods=['POST'])
    def print_label_img():
        return api_handlers.handle_print_label_img()

    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'code': 404, 'message': 'API endpoint not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'code': 500, 'message': 'Internal server error'}), 500
        
    return app
