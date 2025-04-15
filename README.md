# 打印机后台服务
支持打印机的后台服务，支持打印机的基本操作。

## 安装环境
```angular2html
pip install -r requirements.txt
```

## 打包

```
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --icon=assets/app_icon.icns main.py
```

参数说明：

--onefile：将所有依赖打包到一个独立的文件。

--windowed：隐藏应用运行时的终端窗口。

--icon：指定应用的图标文件。

打包完成后，生成的 .app 文件位于 dist 文件夹中。

### 使用 setup.py 打包

项目提供了一个 setup.py 脚本，简化打包过程：

```
# 打包为单个文件
python setup.py --onefile

# 为 Mac Intel 芯片打包
python setup.py --onefile --target-arch=x86_64

# 为 M1/M2 芯片打包
python setup.py --onefile --target-arch=arm64

# 打包为通用二进制（支持Intel和M系列芯片）
python setup.py --onefile --target-arch=universal2

# 强制忽略架构兼容性警告
python setup.py --onefile --target-arch=x86_64 --force
```

### 架构兼容性问题

在 macOS 系统上打包时，需要注意 Python 环境的架构与目标应用架构的兼容性：

1. 如果使用 Apple Silicon (M1/M2) Mac，Python 环境默认为 arm64 架构:
   - 可以直接打包 arm64 应用: `--target-arch=arm64`
   - 无法直接打包 x86_64 (Intel) 应用

2. 如果使用 Intel Mac，Python 环境默认为 x86_64 架构:
   - 可以直接打包 x86_64 应用: `--target-arch=x86_64`
   - 无法直接打包 arm64 应用

3. 如需打包 universal2 应用 (同时支持 Intel 和 Apple Silicon)，需要:
   - 安装两种架构的 Python 环境
   - 使用 `--target-arch=universal2` 参数

如果遇到架构错误，请使用与当前 Python 环境架构匹配的目标架构参数。

### 测试打包后的应用

进入 dist 文件夹，运行生成的 .app 文件，检查是否正常。

如果 macOS 系统提示"无法验证开发者"，你可以按照以下步骤运行未签名的应用：

打开 系统偏好设置 -> 安全性与隐私 -> 通用。
点击"仍然打开"按钮，允许运行该应用。

## 生成图标
```
cd resources
mkdir app.iconset
sips -z 16 16     printer_icon.png --out app.iconset/icon_16x16.png
sips -z 32 32     printer_icon.png --out app.iconset/icon_16x16@2x.png
sips -z 32 32     printer_icon.png --out app.iconset/icon_32x32.png
sips -z 64 64     printer_icon.png --out app.iconset/icon_32x32@2x.png
sips -z 128 128   printer_icon.png --out app.iconset/icon_128x128.png
sips -z 256 256   printer_icon.png --out app.iconset/icon_128x128@2x.png
sips -z 256 256   printer_icon.png --out app.iconset/icon_256x256.png
sips -z 512 512   printer_icon.png --out app.iconset/icon_256x256@2x.png
sips -z 512 512   printer_icon.png --out app.iconset/icon_512x512.png
cp printer_icon.png app.iconset/icon_512x512@2x.png
iconutil -c icns app.iconset
mv app.icns ../assets/app_icon.icns
rm -r app.iconset
```

