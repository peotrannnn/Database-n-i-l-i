# Lái

Web MVP quản lý cụm từ nói lái.

## Chạy local

Vào đúng thư mục có `app.py`:

```bash
cd lai_app
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Mở trình duyệt tại:

```txt
http://127.0.0.1:5000
```

## Tài khoản admin

Không còn tài khoản admin mặc định. Admin được tạo từ biến môi trường để không lộ trên GitHub.

Cần cấu hình đủ 3 biến:

```txt
ADMIN_EMAIL=email_admin_cua_ban@gmail.com
ADMIN_USERNAME=username_admin_cua_ban
ADMIN_PASSWORD=mat_khau_admin_manh
```

Trên Render, vào `Environment` của service và thêm 3 biến trên, sau đó redeploy.

Ở local PowerShell, có thể đặt tạm trước khi chạy:

```powershell
$env:ADMIN_EMAIL="email_admin_cua_ban@gmail.com"
$env:ADMIN_USERNAME="username_admin_cua_ban"
$env:ADMIN_PASSWORD="mat_khau_admin_manh"
python app.py
```

## Ghi chú

- Database SQLite nằm ở `lai.db` và sẽ tự tạo khi chạy lần đầu.
- User thường chỉ gửi đề xuất, admin duyệt/bỏ trong trang quản lý.
- Xuất CSV/Excel chỉ hiện trong trang quản lý admin.
- Nếu đã từng có admin cũ `admin@lai.local`, app sẽ tự chặn tài khoản đó khi admin mới từ biến môi trường được cấu hình.

## v26

- Đã bỏ toàn bộ chức năng quên mật khẩu qua email/Gmail.
- Đăng nhập/đăng ký không còn link Quên mật khẩu.
- Đổi mật khẩu trong trang Tài khoản chỉ cần mật khẩu hiện tại, mật khẩu mới và nhập lại mật khẩu mới.
- Không cần cấu hình MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM hay Gmail App Password nữa.
