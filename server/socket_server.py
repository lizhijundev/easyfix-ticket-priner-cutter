# server/socket_server.py
import threading
import socket
import traceback
import time
from utils.logger import setup_logger

logger = setup_logger()

class SocketServer:
    def __init__(self, port, printer_manager):
        try:
            self.port = port
            self.printer_manager = printer_manager
            self.running = False
            self.server_thread = None
            logger.info(f"Socket服务器初始化，端口: {port}")
        except Exception as e:
            logger.critical(f"初始化Socket服务器失败: {e}")
            traceback.print_exc()
            raise

    def start(self):
        """启动Socket服务器"""
        try:
            if self.running:
                logger.warning("Socket服务器已在运行")
                return

            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            logger.info(f"Socket服务器已启动于端口 {self.port}")
        except Exception as e:
            logger.critical(f"启动Socket服务器失败: {e}")
            traceback.print_exc()
            self.running = False
            raise

    def _server_loop(self):
        """服务器主循环"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                server.bind(('0.0.0.0', self.port))
                server.listen(5)
                server.settimeout(1)  # 设置超时，使stop方法能够中断循环

                logger.info(f"Socket服务器开始监听端口 {self.port}")

                while self.running:
                    try:
                        client, addr = server.accept()
                        logger.info(f"接受来自 {addr} 的连接")

                        # 处理客户端连接
                        client_thread = threading.Thread(
                            target=self._handle_client,
                            args=(client, addr)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                    except socket.timeout:
                        # 超时只是为了检查running标志，不是错误
                        continue
                    except Exception as e:
                        if self.running:  # 只有在服务器应该运行时才记录错误
                            logger.error(f"接受连接时出错: {e}")
                            traceback.print_exc()
            finally:
                server.close()
                logger.info("Socket服务器已关闭")
        except Exception as e:
            logger.critical(f"Socket服务器循环出错: {e}")
            traceback.print_exc()
            self.running = False

    def _handle_client(self, client, addr):
        """处理客户端连接"""
        try:
            client.settimeout(30)  # 设置30秒超时

            # 接收数据
            data = client.recv(4096).decode('utf-8')
            if not data:
                logger.warning(f"Received empty data from {addr}")
                return

            logger.info(f"Received from {addr}: {data}")

            # 检查打印机状态
            response = "OK"

            # 解析数据，确定是标签还是小票打印请求
            try:
                request_data = json.loads(data)
                if 'type' in request_data:
                    if request_data['type'] == 'label':
                        if not self.printer_manager.is_label_printer_available():
                            response = "ERROR: Label printer not available"
                    elif request_data['type'] == 'receipt':
                        if not self.printer_manager.is_receipt_printer_available():
                            response = "ERROR: Receipt printer not available"
            except json.JSONDecodeError:
                # 不是JSON格式，使用默认响应
                pass

            client.send(response.encode('utf-8'))

            logger.info(f"Sent response to {addr}: {response}")
        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
            traceback.print_exc()
        finally:
            client.close()

    def stop(self):
        """停止Socket服务器"""
        try:
            if not self.running:
                logger.warning("Socket服务器未在运行")
                return

            logger.info("正在停止Socket服务器...")
            self.running = False

            # 等待服务器线程结束
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(2)  # 等待最多2秒

            logger.info("Socket服务器已停止")
        except Exception as e:
            logger.error(f"停止Socket服务器时出错: {e}")
            traceback.print_exc()
