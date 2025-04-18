# server/templates.py

class Templates:
    """
    HTML templates for the HTTP server
    """
    @staticmethod
    def get_status_html():
        """Return HTML for status page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Easyfix Print Service Status</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
                .running { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
                .api { background-color: #f8f9fa; border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
                code { background-color: #eee; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>Easyfix Print Service Status</h1>
            <div class="status running">
                <strong>Status:</strong> Running
            </div>
            
            <h2>API Endpoints:</h2>
            <div class="api">
                <h3>Get Printer Status</h3>
                <p><strong>URL:</strong> <code>/api/print/status?printer_type=label|receipt</code></p>
                <p><strong>Method:</strong> GET</p>
                <p><strong>Parameters:</strong></p>
                <pre><code>printer_type: label or receipt (default: label)</code></pre>
            </div>
            
            <div class="api">
                <h3>Print Label</h3>
                <p><strong>URL:</strong> <code>/api/print/label</code></p>
                <p><strong>Method:</strong> POST</p>
                <p><strong>Body:</strong></p>
                <pre><code>{
    "printer": "Optional printer name",
    "content": "Label content to print"
}</code></pre>
            </div>
            
            <div class="api">
                <h3>Print Receipt</h3>
                <p><strong>URL:</strong> <code>/api/print/receipt</code></p>
                <p><strong>Method:</strong> POST</p>
                <p><strong>Body:</strong></p>
                <pre><code>{
    "printer": "Optional printer name",
    "content": "Receipt content to print"
}</code></pre>
            </div>
            
            <div class="api">
                <h3>Print Label Image</h3>
                <p><strong>URL:</strong> <code>/api/print/label_img</code></p>
                <p><strong>Method:</strong> POST</p>
                <p><strong>Content-Type:</strong> <code>multipart/form-data</code></p>
                <p><strong>Body:</strong></p>
                <pre><code>
    Form field name: image
    File content: The image file to print
</code></pre>
            </div>
            
            <div class="api">
                <h3>Print Engineer Order Label</h3>
                <p><strong>URL:</strong> <code>/api/print/label/engineer_order</code></p>
                <p><strong>Method:</strong> POST</p>
                <p><strong>Body:</strong></p>
                <pre><code>{
    "time": "23/04 06:13",
    "user": "lzj|18320181200",
    "device": "iPhone 13 Pro max|64G",
    "fault_data": [
        {
            "fault_name": "Nâng cấp bộ nhớ",
            "fault_plan": [
                "Nâng cấp bộ nhớ chính hãng lên 256GB",
                "Nâng cấp bộ nhớ chính hãng lên 256GB"
            ]
        }
    ],
    "notice": [
        '[ ] Cần sao lưu dữ liệu',
        '[ ] Đã sao lưu',
        '[ ] Đã đăng xuất tài khoản iCloud？',
        '[ ] Mật khẩu mở khóa:',
    ],
    "extra": [
        "Note:"
    ],
    "qr_url": "https://easyfix.vn/"
}</code></pre>
            </div>
        </body>
        </html>
        """
