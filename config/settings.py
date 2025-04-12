# config/settings.py
import os
import json
import platform
import traceback
from utils.logger import setup_logger

logger = setup_logger()

class Settings:
    def __init__(self):
        try:
            self.system = platform.system()
            self.config_file = self._get_config_path()
            self.settings = self._load_settings()
            logger.info(f"Settings loaded, config file: {self.config_file}")
        except Exception as e:
            logger.critical(f"Failed to initialize settings: {e}")
            traceback.print_exc()
            raise

    def _get_config_path(self):
        """获取配置文件路径"""
        try:
            if self.system == "Darwin":  # macOS
                config_dir = os.path.expanduser("~/Library/Application Support/PrintService")
            elif self.system == "Windows":
                config_dir = os.path.join(os.environ["APPDATA"], "PrintService")
            else:
                config_dir = os.path.expanduser("~/.printservice")

            # 确保目录存在
            os.makedirs(config_dir, exist_ok=True)

            return os.path.join(config_dir, "settings.json")
        except Exception as e:
            logger.critical(f"Error getting config path: {e}")
            traceback.print_exc()
            # 使用备用路径
            return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")

    def _load_settings(self):
        """加载设置"""
        try:
            if not os.path.exists(self.config_file):
                # 默认设置
                default_settings = {
                    "label_printer": "",
                    "label_size": "40x30mm",
                    "receipt_printer": "",
                    "receipt_width": "80mm",
                    "socket_port": 8420,
                    "http_port": 8520
                }

                # 保存默认设置
                with open(self.config_file, 'w') as f:
                    json.dump(default_settings, f, indent=2)

                return default_settings

            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            traceback.print_exc()
            # 返回默认设置
            return {
                "label_printer": "",
                "label_size": "40x30mm",
                "receipt_printer": "",
                "receipt_width": "80mm",
                "socket_port": 8420,
                "http_port": 8520
            }

    def get(self, key, default=None):
        """获取设置值"""
        try:
            return self.settings.get(key, default)
        except Exception as e:
            logger.error(f"Error getting setting '{key}': {e}")
            return default

    def set(self, key, value):
        """设置值"""
        try:
            self.settings[key] = value
            logger.debug(f"Setting '{key}' updated to: {value}")
        except Exception as e:
            logger.error(f"Failed to update setting '{key}': {e}")
            traceback.print_exc()

    def save(self):
        """保存设置到文件"""
        try:
            # 创建临时文件
            temp_file = f"{self.config_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.settings, f, indent=2)

            # 确保写入完成后再替换原文件
            os.replace(temp_file, self.config_file)
            logger.info(f"Settings saved to: {self.config_file}")
            return True
        except Exception as e:
            logger.critical(f"Failed to save settings: {e}")
            traceback.print_exc()
            return False

