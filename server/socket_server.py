# server/socket_server.py
import threading
import socket
import traceback
import time
import json
from utils.logger import setup_logger

logger = setup_logger()

class SocketServer:
    def __init__(self, port, printer_manager):
        try:
            self.port = port
            self.printer_manager = printer_manager
            self.running = False
            self.server_thread = None
            self.client_timeout = 60  # 客户端连接超时时间，单位秒
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
            client.settimeout(self.client_timeout)  # 使用更长的超时时间
            logger.info(f"客户端 {addr} 连接超时设置为 {self.client_timeout} 秒")

            # 使用缓冲区接收数据
            buffer = []
            while True:
                try:
                    chunk = client.recv(4096)
                    if not chunk:  # 连接已关闭
                        break
                    buffer.append(chunk)
                    
                    # 尝试解析已收到的数据，看是否是完整的请求
                    try:
                        data = b''.join(buffer).decode('utf-8')
                        # 检查是否是有效的JSON (简单验证)
                        json.loads(data)
                        # 如果能成功解析为JSON，说明数据已完整接收
                        break
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # 数据还不完整，继续接收
                        continue
                except socket.timeout:
                    logger.warning(f"客户端 {addr} 接收数据超时")
                    client.send("ERROR: Connection timeout".encode('utf-8'))
                    return

            data = b''.join(buffer).decode('utf-8')
            if not data:
                logger.warning(f"收到来自 {addr} 的空数据")
                client.send("ERROR: Empty data received".encode('utf-8'))
                return

            logger.info(f"收到来自 {addr} 的数据: {data}")

            # 默认响应
            response = "OK"

            # 解析数据，处理打印请求
            try:
                request_data = json.loads(data)
                
                # 根据event_type处理不同的请求
                event_type = request_data.get('event_type')
                
                if event_type == 'get_receipt_printer':
                    # 获取小票打印机状态
                    is_available = self.printer_manager.is_receipt_printer_available()
                    response = json.dumps({
                        'status': 'ok' if is_available else 'error',
                        'available': is_available,
                        'message': '小票打印机可用' if is_available else '小票打印机不可用'
                    })
                    
                elif event_type == 'get_ticket_printer':
                    # 获取标签打印机状态
                    is_available = self.printer_manager.is_label_printer_available()
                    response = json.dumps({
                        'status': 'ok' if is_available else 'error',
                        'available': is_available,
                        'message': '标签打印机可用' if is_available else '标签打印机不可用'
                    })
                    
                elif event_type == 'print_receipt':
                    # 打印小票
                    if not self.printer_manager.is_receipt_printer_available():
                        response = json.dumps({
                            'status': 'error',
                            'message': '小票打印机不可用'
                        })
                    else:
                        try:
                            # 获取原始打印数据
                            raw_data = request_data.get('raw')
                            if not raw_data:
                                raise ValueError("缺少打印数据")
                                
                            # 构建打印数据对象
                            print_data = {
                                'raw': raw_data,
                                'type': 'receipt'
                            }
                            
                            result = self.printer_manager.print_receipt(print_data)
                            if result:
                                response = json.dumps({
                                    'status': 'ok',
                                    'message': '小票打印成功'
                                })
                            else:
                                response = json.dumps({
                                    'status': 'error',
                                    'message': '小票打印失败'
                                })
                            logger.info(f"小票打印结果: {response}")
                        except Exception as e:
                            error_msg = f"小票打印过程出错: {str(e)}"
                            logger.error(error_msg)
                            response = json.dumps({
                                'status': 'error',
                                'message': error_msg
                            })
                
                elif event_type == 'print_label':
                    # 打印标签
                    if not self.printer_manager.is_label_printer_available():
                        response = json.dumps({
                            'status': 'error',
                            'message': '标签打印机不可用'
                        })
                    else:
                        try:
                            # 获取原始打印数据
                            raw_data = request_data.get('raw')
                            if not raw_data:
                                raise ValueError("缺少打印数据")
                                
                            # 构建打印数据对象
                            print_data = {
                                'raw': raw_data,
                                'type': 'label'
                            }
                            
                            result = self.printer_manager.print_label(print_data)
                            if result:
                                response = json.dumps({
                                    'status': 'ok',
                                    'message': '标签打印成功'
                                })
                            else:
                                response = json.dumps({
                                    'status': 'error',
                                    'message': '标签打印失败'
                                })
                            logger.info(f"标签打印结果: {response}")
                        except Exception as e:
                            error_msg = f"标签打印过程出错: {str(e)}"
                            logger.error(error_msg)
                            response = json.dumps({
                                'status': 'error',
                                'message': error_msg
                            })
                
                elif event_type == 'heartbeat':
                    # 心跳检测
                    response = json.dumps({
                        'status': 'ok',
                        'message': 'HEARTBEAT_OK'
                    })
                    
                else:
                    # 未知事件类型
                    error_msg = f"未知的事件类型: {event_type}"
                    logger.warning(error_msg)
                    response = json.dumps({
                        'status': 'error',
                        'message': error_msg
                    })
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSON解析错误: {str(e)}"
                logger.error(f"来自 {addr} 的数据格式无效: {error_msg}")
                response = json.dumps({
                    'status': 'error',
                    'message': f"JSON格式无效: {error_msg}"
                })
            except Exception as e:
                error_msg = f"处理请求时出错: {str(e)}"
                logger.error(error_msg)
                response = json.dumps({
                    'status': 'error',
                    'message': error_msg
                })

            try:
                client.send(response.encode('utf-8'))
                logger.info(f"已发送响应到 {addr}: {response}")
            except socket.timeout:
                logger.error(f"向客户端 {addr} 发送响应超时")
            except Exception as e:
                logger.error(f"发送响应到 {addr} 时出错: {str(e)}")
        except socket.timeout:
            logger.error(f"客户端 {addr} 连接超时")
            try:
                error_response = json.dumps({
                    'status': 'error',
                    'message': '连接超时'
                })
                client.send(error_response.encode('utf-8'))
            except:
                pass
        except Exception as e:
            logger.error(f"处理客户端 {addr} 时出错: {e}")
            traceback.print_exc()
            try:
                error_response = json.dumps({
                    'status': 'error',
                    'message': f"服务器错误: {str(e)[:100]}"
                })
                client.send(error_response.encode('utf-8'))
            except:
                pass
        finally:
            client.close()
            logger.info(f"关闭与 {addr} 的连接")

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
