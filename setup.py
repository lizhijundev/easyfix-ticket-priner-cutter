# setup.py
import sys
from cx_Freeze import setup, Executable

# 依赖
build_exe_options = {
    "packages": [
        "PyQt6", "flask", "json", "threading", "asyncio",
        "reportlab", "logging", "os", "sys", "platform", "signal"
    ],
    "excludes": [],
    "include_files": [
        ("resources/", "resources/")
    ]
}

# 根据系统添加特定依赖
if sys.platform == "darwin":
    build_exe_options["packages"].append("cups")
elif sys.platform == "win32":
    build_exe_options["packages"].extend(["win32print", "win32api"])

# 可执行文件
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Windows GUI应用

executables = [
    Executable(
        "main.py",
        base=base,
        target_name="PrintService",
        icon="resources/printer_icon.png"
    )
]

setup(
    name="PrintService",
    version="1.0",
    description="Printing Service for Labels and Tickets",
    options={"build_exe": build_exe_options},
    executables=executables
)
