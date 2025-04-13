# server/http_server.py
import threading
import traceback
import uuid
import os
import io
import re
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
                    <title>Easyfix Print Service Status</title>
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
                    <h1>Easyfix Print Service Status</h1>
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
            logger.info(f"接收到POST请求: {self.path}")

            # 判断请求类型
            content_type = self.headers.get('Content-Type', '')

            # 处理不同类型的请求
            if content_type.startswith('application/json'):
                # 处理JSON格式的请求
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                logger.debug(f"JSON POST数据: {post_data}")

                try:
                    data = json.loads(post_data)
                except json.JSONDecodeError:
                    self.send_error(400, "无效的JSON格式")
                    return

                # 处理打印请求
                if self.path == '/api/print/label':
                    self._handle_print_label(data)
                elif self.path == '/api/print/receipt':
                    self._handle_print_receipt(data)
                else:
                    self.send_error(404, "API端点不存在")

            elif content_type.startswith('multipart/form-data'):
                # 处理表单数据，包含文件上传
                if self.path == '/api/print/label_img':
                    self._handle_print_label_img()
                else:
                    self.send_error(404, "API端点不存在")
            else:
                self.send_error(415, "不支持的媒体类型")

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
                    'code': 300,
                    'message': "Label printer not available"
                })
                return

            # 检查必要的字段
            if 'content' not in data:
                self.send_error(400, "Missing content field")
                return

            # 打印标签
            rs, message = self.printer_manager.print_label(data['content'])

            # 返回结果
            self._send_json_response({
                'code': 0 if rs else 400,
                'message': "Label printed successfully" if rs else message
            })
        except Exception as e:
            logger.error(f"Error handling label print request: {e}")
            traceback.print_exc()
            self.send_error(500, "Error processing label print request")

    def _handle_print_label_img(self):
        """处理图片标签打印请求"""
        try:
            # 首先检查标签打印机是否可用
            if not self.printer_manager.is_label_printer_available():
                self._send_json_response({
                    'code': 300,
                    'message': "Label printer not available"
                })
                return

            # 解析表单数据
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))

            # 获取boundary
            boundary = None
            for param in content_type.split(';'):
                param = param.strip()
                if param.startswith('boundary='):
                    boundary = param[9:]
                    if boundary.startswith('"') and boundary.endswith('"'):
                        boundary = boundary[1:-1]
                    break

            if not boundary:
                self._send_json_response({
                    'code': 400,
                    'message': "Missing boundary in content-type"
                })
                return

            # 读取完整的请求体
            post_data = self.rfile.read(content_length)

            # 解析multipart/form-data
            image_data = None
            filename = None

            # 按boundary分隔表单数据
            boundary_bytes = f'--{boundary}'.encode('utf-8')
            parts = post_data.split(boundary_bytes)

            # 遍历所有部分寻找图片数据
            for part in parts:
                if b'Content-Disposition: form-data; name="image"' in part:
                    # 找到文件名
                    filename_match = re.search(b'filename="(.+?)"', part)
                    if filename_match:
                        filename = filename_match.group(1).decode('utf-8')

                    # 分离头部和内容
                    header_end = part.find(b'\r\n\r\n')
                    if header_end > 0:
                        image_data = part[header_end + 4:]  # +4是跳过\r\n\r\n
                        # 移除尾部的\r\n
                        if image_data.endswith(b'\r\n'):
                            image_data = image_data[:-2]
                    break

            if not image_data or not filename:
                self._send_json_response({
                    'code': 400,
                    'message': "Missing image file"
                })
                return

            # 获取文件格式
            file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
            if not file_ext or file_ext not in ['png', 'jpg', 'jpeg', 'bmp', 'gif']:
                file_ext = 'png'  # 默认格式

            logger.info(f"接收到图片文件: {filename}, 大小: {len(image_data)} 字节")

            # 打印图片标签
            success, message = self.printer_manager.print_label_image(image_data, file_ext)

            # 返回结果
            self._send_json_response({
                'code': 0 if success else 400,
                'message': "Image label printed successfully" if success else message
            })

        except Exception as e:
            logger.error(f"处理图片标签打印请求出错: {e}")
            traceback.print_exc()
            self._send_json_response({
                'code': 500,
                'message': f"Error processing image label print request: {str(e)}"
            })

    def _handle_print_receipt(self, data):
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


            # 打印小票
            success = self.printer_manager.print_receipt(data['content'])

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
        # 创建一个闭包类来添加printer_manager
        handler_with_printer = type('HandlerWithPrinter',
                                    (RequestHandlerClass,),
                                    {'printer_manager': printer_manager})
        super().__init__(server_address, handler_with_printer)

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

