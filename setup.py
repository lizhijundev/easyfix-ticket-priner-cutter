# setup.py - 使用 PyInstaller 进行打包
import sys
import os
import subprocess
import argparse
import platform

# 创建参数解析器
parser = argparse.ArgumentParser(description='打包应用程序')
parser.add_argument('--onefile', action='store_true', help='打包为单个文件')
parser.add_argument('--target-arch', choices=['universal2', 'x86_64', 'arm64'], 
                    help='指定目标架构（仅macOS）: universal2, x86_64 (Intel), arm64 (Apple Silicon)')
parser.add_argument('--force', action='store_true', help='强制打包，忽略架构兼容性警告')
args, unknown = parser.parse_known_args()

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
if args.onefile or "--onefile" in unknown:
    command.append("--onefile")
    if "--onefile" in unknown:
        unknown.remove("--onefile")

# 架构兼容性检查（仅适用于 macOS）
if sys.platform == "darwin" and args.target_arch:
    # 检测当前 Python 环境的架构
    current_arch = platform.machine()
    print(f"当前 Python 环境架构: {current_arch}")
    
    # 检查架构兼容性
    is_compatible = True
    if current_arch == "arm64" and args.target_arch == "x86_64":
        is_compatible = False
        print("\n警告: 您正在使用 Apple Silicon (arm64) Python 环境尝试构建 Intel (x86_64) 应用。")
        print("这可能导致架构兼容性错误。解决方案:")
        print("1. 使用 '--target-arch=arm64' 为 Apple Silicon 构建")
        print("2. 使用 '--target-arch=universal2' 构建通用二进制(需要安装 Intel 和 ARM 的 Python 环境)")
        print("3. 在 Intel 架构的 Python 环境中运行此脚本以构建 x86_64 应用\n")
    elif current_arch == "x86_64" and args.target_arch == "arm64":
        is_compatible = False
        print("\n警告: 您正在使用 Intel (x86_64) Python 环境尝试构建 Apple Silicon (arm64) 应用。")
        print("这可能导致架构兼容性错误。解决方案:")
        print("1. 使用 '--target-arch=x86_64' 为 Intel 架构构建")
        print("2. 使用 '--target-arch=universal2' 构建通用二进制(需要安装 Intel 和 ARM 的 Python 环境)")
        print("3. 在 Apple Silicon 架构的 Python 环境中运行此脚本以构建 arm64 应用\n")
    
    # 如果架构不兼容且用户没有强制执行，则中止
    if not is_compatible and not args.force:
        print("打包操作已中止。如果您确信要继续，请添加 --force 参数。")
        print("例如: python setup.py --onefile --target-arch=x86_64 --force\n")
        sys.exit(1)
    
    # 添加目标架构参数
    command.append(f"--target-architecture={args.target_arch}")
    print(f"为目标架构 {args.target_arch} 打包")

# 添加其他未知参数
command.extend(unknown)

# 添加主程序文件
command.append("main.py")

# 执行打包命令
print("开始打包应用程序...")
print(" ".join(command))
try:
    subprocess.check_call(command)
    print("\n打包完成！打包后的应用位于 dist 目录")
except subprocess.CalledProcessError as e:
    print(f"\n打包失败，错误码: {e.returncode}")
    print("请参考 PyInstaller 文档了解更多关于多架构支持的信息:")
    print("https://pyinstaller.org/en/stable/feature-notes.html#macos-multi-arch-support")
