"""Định dạng tiền, thời gian và tiêu đề giao dịch để hiển thị."""
from datetime import datetime


def money(value):
    return f"{value:,.0f}"


def money_vnd(value):
    return f"{money(value)} VNĐ"


def is_incoming(tx):
    return tx.kind in ("deposit", "transfer_in")


def signed_money(tx):
    return f"{'+' if is_incoming(tx) else '-'}{money(tx.amount)}"


def shorten(text, limit=20):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_time(timestamp, with_seconds=False):
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(timestamp)
    today = datetime.now().date()
    t = dt.strftime("%H:%M:%S" if with_seconds else "%H:%M")
    if dt.date() == today:
        return f"Hôm nay · {t}"
    if (today - dt.date()).days == 1:
        return f"Hôm qua · {t}"
    if dt.year == today.year:
        return f"{dt:%d/%m} · {t}"
    return f"{dt:%d/%m/%Y} · {t}"


def tx_title(tx):
    if tx.kind == "deposit":
        return "Nạp tiền vào ví"
    if tx.kind == "transfer_out":
        return f"Chuyển đến {shorten(tx.counterparty_name)}"
    return f"Nhận từ {shorten(tx.counterparty_name)}"


def tx_type_label(tx):
    return {"deposit": "Nạp tiền", "transfer_out": "Chuyển tiền", "transfer_in": "Nhận tiền"}[tx.kind]


def wrap_chunks(text, size=32):
    """Ngắt chuỗi dài (hash/chữ ký) thành nhiều dòng để hiển thị gọn."""
    return "\n".join(text[i:i + size] for i in range(0, len(text), size))
