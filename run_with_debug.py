# run_with_debug.py
import sys
import traceback
import time

try:
    from main import PrintService

    print("正在启动打印服务...")
    service = PrintService()
    service.start()

    # 保持程序运行
    while True:
        time.sleep(1)
except Exception as e:
    print(f"严重错误: {e}")
    traceback.print_exc()
    print("\n按任意键退出...")
    input()
    sys.exit(1)
