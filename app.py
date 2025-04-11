import cups
import os
import tkinter as tk
from tkinter import messagebox
import serial


def list_printers():
    """
    使用 pycups 获取本地可用打印机列表。
    过滤掉非 USB 打印机，返回打印机名称和设备 URI。
    """
    conn = cups.Connection()
    printers = conn.getPrinters()

    usb_printers = []  # 存放 USB 打印机
    for printer_name, printer_info in printers.items():
        device_uri = printer_info["device-uri"]
        # 过滤仅保留 USB 打印机（设备 URI 包含 "usb://" 的打印机）
        if "usb://" in device_uri:
            usb_printers.append((printer_name, device_uri))
    return usb_printers  # 返回 [(打印机名称, 设备 URI)]


def send_cut_command_to_usb(device_uri):
    """
    发送 ESC/POS 切纸指令到指定的 USB 打印机。
    使用设备 URI 解析端口路径。
    """
    try:
        # 提取设备路径（例如：/dev/ttyUSB0）
        if "usb://" in device_uri:
            # 获取设备端口（macOS 的 USB 打印机通常无法直接从 device-uri 获取具体端口）
            printer_port = "/dev/ttyUSB0"  # 默认端口，需要替换为实际的端口
        else:
            raise ValueError(f"无法识别的设备 URI: {device_uri}")

        # 打开 USB 端口并发送切纸命令
        with serial.Serial(printer_port, baudrate=9600, timeout=1) as printer:
            cut_command = b'\x1D\x56\x00'  # ESC/POS 完整切纸
            printer.write(cut_command)
            messagebox.showinfo("成功", f"切纸指令已发送到打印机端口: {printer_port}")
    except Exception as e:
        messagebox.showerror("错误", f"发送切纸指令失败：{e}")


def on_cut_paper():
    """
    切纸按钮的回调函数。
    获取选中的打印机并发送切纸指令。
    """
    selected_index = printer_listbox.curselection()
    if not selected_index:
        messagebox.showwarning("警告", "请先选择一个打印机！")
        return

    # 获取用户选中的打印机信息
    printer_name, device_uri = usb_printers[selected_index[0]]
    send_cut_command_to_usb(device_uri)


# 创建主窗口
root = tk.Tk()
root.title("Easyfix Ticket Print Cutter")

# 获取 USB 打印机列表
usb_printers = list_printers()

# 如果没有检测到 USB 打印机，提示用户并退出程序
if not usb_printers:
    messagebox.showerror("Error", "Can't find any USB Device, Pleasy retry.")
    root.destroy()  # 关闭程序
else:
    # 打印机列表标题
    tk.Label(root, text="Select Printer:").pack(pady=5)

    # 创建打印机列表框
    printer_listbox = tk.Listbox(root, height=10, selectmode=tk.SINGLE)
    for printer_name, device_uri in usb_printers:
        printer_listbox.insert(tk.END, f"{printer_name} ({device_uri})")
    printer_listbox.pack(padx=10, pady=10)

    # 切纸按钮
    cut_button = tk.Button(root, text="Cut Paper", command=on_cut_paper)
    cut_button.pack(pady=10)

# 启动 GUI 主循环
root.mainloop()
