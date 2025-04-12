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

### 测试打包后的应用

进入 dist 文件夹，运行生成的 .app 文件，检查是否正常。

如果 macOS 系统提示“无法验证开发者”，你可以按照以下步骤运行未签名的应用：

打开 系统偏好设置 -> 安全性与隐私 -> 通用。
点击“仍然打开”按钮，允许运行该应用。

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
