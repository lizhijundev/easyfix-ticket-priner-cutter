# utils/logger.py
import os
import logging
import platform
from logging.handlers import RotatingFileHandler

def setup_logger(name='print_service'):
    """设置并返回日志记录器"""
    logger = logging.getLogger(name)

    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(logging.DEBUG)

    # 确定日志文件路径
    if platform.system() == "Darwin":  # macOS
        log_dir = os.path.expanduser("~/Library/Logs/PrintService")
    elif platform.system() == "Windows":
        log_dir = os.path.join(os.environ["APPDATA"], "PrintService", "logs")
    else:  # Linux
        log_dir = os.path.expanduser("~/.printservice/logs")

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "print_service.log")

    # 创建文件处理器，限制每个日志文件的大小为5MB，保留5个备份文件
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging system initialized")
    logger.info(f"Log file path: {log_file}")

    return logger
