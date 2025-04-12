# setup.py - 使用 PyInstaller 进行打包
import sys
import os
import subprocess

# 项目根目录
base_dir = os.path.abspath(os.path.dirname(__file__))
assets_dir = os.path.join(base_dir, "assets")

# 检查 PyInstaller 是否已安装
try:
    import PyInstaller
except ImportError:
    print("正在安装 PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

# 确定图标路径
icon_path = None
if sys.platform == "darwin":
    icon_path = os.path.join(assets_dir, "app_icon.icns")
elif sys.platform == "win32":
    icon_path = os.path.join(assets_dir, "app_icon.ico")
else:  # Linux
    icon_path = os.path.join(assets_dir, "app_icon.png")

# 检查图标是否存在
if not os.path.exists(icon_path):
    print(f"警告: 图标文件 {icon_path} 不存在")
    icon_option = ""
else:
    icon_option = f"--icon={icon_path}"

# 构建 PyInstaller 命令
command = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--windowed",
    icon_option,
    "--name=PrintService",
    "--add-data", f"{assets_dir}{os.pathsep}assets",
]

# 是否需要打包为单文件
if "--onefile" in sys.argv:
    command.append("--onefile")
    sys.argv.remove("--onefile")

# 添加主程序文件
command.append("main.py")

# 执行打包命令
print("开始打包应用程序...")
print(" ".join(command))
subprocess.check_call(command)

print("\n打包完成！打包后的应用位于 dist 目录")