# server/http_server.py
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from utils.logger import setup_logger

logger = setup_logger()

class PrintRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, printer_manager=None, **kwargs):
        self.printer_manager = printer_manager
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """重写日志方法，使用我们的日志器"""
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        """处理GET请求，返回服务状态页面"""
        try:
            if self.path == '/' or self.path == '/status':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                # 简单的状态页面
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Print Service Status</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                        .running {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
                        .api {{ background-color: #f8f9fa; border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
                        code {{ background-color: #eee; padding: 2px 5px; border-radius: 3px; }}
                    </style>
                </head>
                <body>
                    <h1>Print Service Status</h1>
                    <div class="status running">
                        <strong>Status:</strong> Running
                    </div>
                    
                    <h2>API Endpoints:</h2>
                    <div class="api">
                        <h3>Print Label</h3>
                        <p><strong>URL:</strong> <code>/api/print/label</code></p>
                        <p><strong>Method:</strong> POST</p>
                        <p><strong>Body:</strong></p>
                        <pre><code>{{
    "printer": "Optional printer name",
    "content": "Label content to print"
}}</code></pre>
                    </div>
                    
                    <div class="api">
                        <h3>Print Receipt</h3>
                        <p><strong>URL:</strong> <code>/api/print/ticket</code></p>
                        <p><strong>Method:</strong> POST</p>
                        <p><strong>Body:</strong></p>
                        <pre><code>{{
    "printer": "Optional printer name",
    "content": "Receipt content to print"
}}</code></pre>
                    </div>
                </body>
                </html>
                """

                self.wfile.write(html.encode('utf-8'))
                return

            self.send_error(404, "Page not found")
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            traceback.print_exc()
            self.send_error(500, "Internal Server Error")

    def do_POST(self):
        """处理POST请求"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')

            logger.info(f"接收到POST请求: {self.path}")
            logger.debug(f"POST数据: {post_data}")

            # 解析JSON数据
            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                self.send_error(400, "无效的JSON格式")
                return

            # 处理打印请求
            if self.path == '/api/print/label':
                self._handle_print_label(data)
            elif self.path == '/api/print/ticket':
                self._handle_print_ticket(data)
            else:
                self.send_error(404, "API端点不存在")
        except Exception as e:
            logger.error(f"处理POST请求出错: {e}")
            traceback.print_exc()
            self.send_error(500, "服务器内部错误")

    def _handle_print_label(self, data):
        """处理标签打印请求"""
        try:
            # 首先检查标签打印机是否可用
            if not self.printer_manager.is_label_printer_available():
                self._send_json_response({
                    'success': False,
                    'message': "Label printer not available"
                })
                return

            # 检查必要的字段
            if 'content' not in data:
                self.send_error(400, "Missing content field")
                return

            # 获取打印机名称
            printer_name = data.get('printer', None)
            if not printer_name:
                printer_name = self.printer_manager.settings.get("label_printer", "")

            # 打印标签
            success = self.printer_manager.print_label(printer_name, data['content'])

            # 返回结果
            self._send_json_response({
                'success': success,
                'message': "Label printed successfully" if success else "Failed to print label"
            })
        except Exception as e:
            logger.error(f"Error handling label print request: {e}")
            traceback.print_exc()
            self.send_error(500, "Error processing label print request")

    def _handle_print_ticket(self, data):
        """处理小票打印请求"""
        try:
            # 首先检查小票打印机是否可用
            if not self.printer_manager.is_receipt_printer_available():
                self._send_json_response({
                    'success': False,
                    'message': "Receipt printer not available"
                })
                return

            # 检查必要的字段
            if 'content' not in data:
                self.send_error(400, "Missing content field")
                return

            # 获取打印机名称
            printer_name = data.get('printer', None)
            if not printer_name:
                printer_name = self.printer_manager.settings.get("ticket_printer", "")

            # 打印小票
            success = self.printer_manager.print_ticket(printer_name, data['content'])

            # 返回结果
            self._send_json_response({
                'success': success,
                'message': "Receipt printed successfully" if success else "Failed to print receipt"
            })
        except Exception as e:
            logger.error(f"Error handling receipt print request: {e}")
            traceback.print_exc()
            self.send_error(500, "Error processing receipt print request")

    def _send_json_response(self, data):
        """发送JSON响应"""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            response = json.dumps(data).encode('utf-8')
            self.wfile.write(response)
        except Exception as e:
            logger.error(f"发送JSON响应时出错: {e}")
            traceback.print_exc()


class HTTPServerThread(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, printer_manager):
        self.printer_manager = printer_manager
        super().__init__(server_address, RequestHandlerClass)

    def finish_request(self, request, client_address):
        """重写以传递printer_manager到处理器"""
        self.RequestHandlerClass(
            request, client_address, self,
            printer_manager=self.printer_manager
        )


class HttpServer:
    def __init__(self, port, printer_manager):
        try:
            self.port = port
            self.printer_manager = printer_manager
            self.running = False
            self.server = None
            self.server_thread = None
            logger.info(f"HTTP服务器初始化，端口: {port}")
        except Exception as e:
            logger.critical(f"初始化HTTP服务器失败: {e}")
            traceback.print_exc()
            raise

    def start(self):
        """启动HTTP服务器"""
        try:
            if self.running:
                logger.warning("HTTP服务器已在运行")
                return

            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            logger.info(f"HTTP服务器已启动于端口 {self.port}")
        except Exception as e:
            logger.critical(f"启动HTTP服务器失败: {e}")
            traceback.print_exc()
            self.running = False
            raise

    def _server_loop(self):
        """服务器主循环"""
        try:
            # 创建HTTP服务器
            handler = PrintRequestHandler
            self.server = HTTPServerThread(('0.0.0.0', self.port), handler, self.printer_manager)
            self.server.timeout = 1  # 设置超时，使stop方法能够中断循环

            logger.info(f"HTTP服务器开始监听端口 {self.port}")

            # 运行服务器，直到self.running为False
            while self.running:
                self.server.handle_request()

            logger.info("HTTP服务器主循环结束")
        except Exception as e:
            logger.critical(f"HTTP服务器循环出错: {e}")
            traceback.print_exc()
        finally:
            if self.server:
                self.server.server_close()
                logger.info("HTTP服务器已关闭")
            self.running = False

    def stop(self):
        """停止HTTP服务器"""
        try:
            if not self.running:
                logger.warning("HTTP服务器未在运行")
                return

            logger.info("正在停止HTTP服务器...")
            self.running = False

            # 等待服务器线程结束
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(2)  # 等待最多2秒

            logger.info("HTTP服务器已停止")
        except Exception as e:
            logger.error(f"停止HTTP服务器时出错: {e}")
            traceback.print_exc()
