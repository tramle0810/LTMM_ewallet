# E-Wallet – Ví điện tử mô phỏng

Ứng dụng ví điện tử dạng mobile (PySide6) với **SHA-256** và **chữ ký số RSA-2048**.
Mọi dữ liệu (người dùng, số dư, giao dịch) được đọc/ghi trực tiếp từ `wallet.db`;
ứng dụng **không có dữ liệu mẫu hay tài khoản dựng sẵn**.

## Chức năng

| Chức năng | Mô tả |
|---|---|
| Đăng ký | Tạo tài khoản, sinh số tài khoản và cặp khóa RSA-2048 |
| Đăng nhập | Bằng số tài khoản + mật khẩu |
| Nạp tiền | Ghi vào DB, băm SHA-256 và ký RSA như một giao dịch |
| Chuyển tiền | Tra cứu người nhận, xác nhận, ký RSA, cập nhật 2 số dư nguyên tử |
| Lịch sử | Lọc Tất cả / Tiền vào / Tiền ra, xem chi tiết từng giao dịch |
| Xác minh | Băm lại dữ liệu trong DB + kiểm tra chữ ký bằng public key người gửi |
| Demo giả mạo | Sửa số tiền trực tiếp trong DB để chứng minh chữ ký phát hiện được |

## Cài đặt & chạy

```bash
pip install -r requirements.txt
python main.py
```

Font: bỏ `Roboto-Regular.ttf` và `Roboto-Medium.ttf` vào thư mục `fonts/`
(xem `fonts/README.txt`). Thiếu font app vẫn chạy bằng font dự phòng.

Tiện ích khác:

```bash
python -m core.database                         # in nội dung wallet.db ra console
python -m unittest discover -s tests -t . -v    # chạy bộ test (không cần PySide6)
```

Đổi file database bằng biến môi trường: `EWALLET_DB=/duong/dan/khac.db python main.py`

## Cấu trúc dự án

```
ewallet/
├── main.py                  # điểm khởi chạy
├── wallet.db                # cơ sở dữ liệu SQLite
├── requirements.txt
├── fonts/                   # Isometra + Roboto
├── core/                    # nghiệp vụ, không phụ thuộc giao diện
│   ├── crypto_utils.py      # SHA-256, RSA, băm mật khẩu
│   ├── database.py          # kết nối, giao dịch nguyên tử, migrate schema
│   └── wallet_service.py    # đăng ký/đăng nhập/nạp/chuyển/xác minh
├── ui/                      # giao diện PySide6
│   ├── theme.py             # bảng màu navy, font, QSS
│   ├── icons.py             # icon SVG vẽ bằng code
│   ├── formatting.py        # định dạng tiền, thời gian
│   ├── widgets.py           # nền gradient, ô nhập, nút, dòng giao dịch
│   ├── dialogs.py           # chi tiết / biên lai giao dịch
│   ├── main_window.py       # điều hướng giữa các màn hình
│   └── screens/             # login, register, dashboard, deposit, transfer, history
└── tests/                   # unit test tầng nghiệp vụ
```

Nguyên tắc: **giao diện chỉ gọi `WalletService`**, không viết SQL hay mã hóa trong `ui/`.

## Cơ sở dữ liệu

- `users(id, account_number, username, password, private_key, public_key, balance, created_at)`
- `transactions(id, sender_id, receiver_id, amount, sender/receiver_old/new_balance,
  timestamp, transaction_hash, signature, type)` – `type` là `transfer` hoặc `deposit`
- `tamper_backup(tx_id, original_amount)` – chỉ phục vụ nút demo giả mạo

**`wallet.db` cũ được tự động migrate** khi khởi động lần đầu: user cũ được giữ nguyên
(đăng nhập bằng mật khẩu cũ), file gốc được sao lưu thành `wallet.db.bak_<thời gian>`,
các bảng cũ được giữ lại với tên `legacy_*_backup`.

## Cơ chế bảo mật

**Chữ ký số giao dịch**

```
payload = sender_id|receiver_id|amount|số_dư_cũ_gửi|số_dư_mới_gửi|số_dư_cũ_nhận|số_dư_mới_nhận|thời_gian
hash      = SHA-256(payload)
signature = RSA-PKCS1v15-SHA256( payload, private_key_người_gửi )
```

Xác minh: tính lại `hash` từ dữ liệu *hiện có trong DB*, so với `transaction_hash`, rồi dùng
`public_key` người gửi kiểm tra `signature`. Sửa bất kỳ trường nào → cả hai bước đều thất bại.

**Bảo vệ tài khoản**

- Mật khẩu: PBKDF2-HMAC-SHA256, 200.000 vòng, salt ngẫu nhiên (tài khoản cũ dùng SHA-256 trần
  được tự động nâng cấp khi đăng nhập thành công).
- Private key được mã hóa bằng mật khẩu người dùng (PKCS#8); chỉ được giải mã trong RAM
  trong suốt phiên đăng nhập, không bao giờ lưu dạng thô.
- Chuyển tiền chạy trong một giao dịch SQLite (`BEGIN IMMEDIATE`): lỗi giữa chừng thì
  `ROLLBACK`, không bao giờ lệch số dư.
- Kiểm tra: số tiền nguyên dương ≤ 1 tỷ, đủ số dư, không tự chuyển cho mình,
  người dùng chỉ xem/xác minh được giao dịch của chính mình.

## Kịch bản demo cho báo cáo

1. Đăng ký 2 tài khoản A và B (ghi lại số tài khoản).
2. Đăng nhập A → Nạp tiền 2.000.000 → Chuyển 500.000 cho B.
3. Lịch sử → mở giao dịch → **Xác minh chữ ký** → *Hợp lệ*.
4. Trong chi tiết giao dịch bấm **Demo: sửa số tiền trong database**, rồi **Xác minh** lại
   → *Không hợp lệ* (hash và chữ ký đều sai). Ở Lịch sử, nút **Xác minh toàn bộ** sẽ đánh dấu
   giao dịch đó "Bị thay đổi".
5. Bấm **Khôi phục dữ liệu gốc** → xác minh lại → *Hợp lệ*.
6. `python -m core.database` để chụp nội dung bảng làm minh chứng.

## Giới hạn (do đây là ví mô phỏng)

- Một file SQLite cục bộ, chưa có server; không có OTP/2FA.
- Mã hóa private key dùng thiết lập mặc định của thư viện `cryptography`.
- Tiền nạp không đi qua cổng thanh toán thật.
