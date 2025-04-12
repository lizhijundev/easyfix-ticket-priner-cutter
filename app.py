import cups
import os
import tkinter as tk
from tkinter import messagebox
import serial
import tempfile
import os


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
    使用 CUPS 打印服务发送切纸指令到 USB 打印机。
    """
    try:
        conn = cups.Connection()

        # ESC/POS 切纸命令
        cut_command = b'\x1D\x56\x00'

        # 使用 CUPS 打印服务查找对应的打印机名称
        printer_name = None
        for name, info in conn.getPrinters().items():
            if info["device-uri"] == device_uri:
                printer_name = name
                break

        if not printer_name:
            raise ValueError(
                f"Can't find device's name,Device URI: {device_uri}")

        # 创建临时文件保存切纸指令
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(cut_command)
            temp_file_path = temp_file.name

        # 使用 CUPS 打印临时文件
        conn.printFile(printer_name, temp_file_path,
                       "ESC/POS Cut Command", {"raw": "true"})

        messagebox.showinfo("Success", f"Cutter Command sent: {
                            printer_name} ({device_uri})")
        os.remove(temp_file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Sent Command Error {e}")


def on_cut_paper():
    """
    切纸按钮的回调函数。
    获取选中的打印机并发送切纸指令。
    """
    selected_index = printer_listbox.curselection()
    if not selected_index:
        messagebox.showwarning("WARN", "Please choose a printer")
        return

    # 获取用户选中的打印机信息
    printer_name, device_uri = usb_printers[selected_index[0]]
    send_cut_command_to_usb(device_uri)


# 创建主窗口
root = tk.Tk()
root.title("Easyfix Printer Service")

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
