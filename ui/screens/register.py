"""Màn hình đăng ký tài khoản."""
from PySide6.QtCore import Qt, Signal

from core.wallet_service import WalletError

from ..widgets import (
    AuthScreen, busy_cursor, make_divider, make_input, make_label, make_link,
    make_primary, show_error, show_info,
)


class RegisterScreen(AuthScreen):
    registered = Signal(str)          # số tài khoản vừa tạo
    login_requested = Signal()

    def __init__(self, service):
        super().__init__()
        self.service = service
        lay = self.card_layout

        lay.addWidget(make_label("Đăng ký", "H1"))
        lay.addSpacing(2)
        lay.addWidget(make_label("Tạo tài khoản mới để sử dụng ví", "Subtitle"))
        lay.addSpacing(20)

        lay.addWidget(make_label("Họ và tên", "FieldLabel"))
        lay.addSpacing(8)
        self.name_input = make_input("Nhập họ và tên đầy đủ")
        lay.addWidget(self.name_input)
        lay.addSpacing(14)

        lay.addWidget(make_label("Mật khẩu", "FieldLabel"))
        lay.addSpacing(8)
        self.password_input = make_input("Tối thiểu 6 ký tự", password=True)
        lay.addWidget(self.password_input)
        lay.addSpacing(14)

        lay.addWidget(make_label("Nhập lại mật khẩu", "FieldLabel"))
        lay.addSpacing(8)
        self.confirm_input = make_input("Xác nhận lại mật khẩu", password=True)
        lay.addWidget(self.confirm_input)
        lay.addSpacing(24)

        lay.addWidget(make_primary("ĐĂNG KÝ TÀI KHOẢN", self.submit))
        lay.addSpacing(18)
        lay.addLayout(make_divider("Hoặc"))
        lay.addSpacing(10)
        lay.addWidget(make_label("Đã có tài khoản?", "Muted", Qt.AlignCenter))
        lay.addWidget(make_link("Quay lại đăng nhập", self.login_requested.emit))

        self.name_input.returnPressed.connect(lambda: self.password_input.setFocus())
        self.password_input.returnPressed.connect(lambda: self.confirm_input.setFocus())
        self.confirm_input.returnPressed.connect(self.submit)

    def reset(self):
        for edit in (self.name_input, self.password_input, self.confirm_input):
            edit.clear()

    def submit(self):
        name = self.name_input.text().strip()
        try:
            with busy_cursor():   # sinh cặp khóa RSA-2048 mất khoảng 1 giây
                account = self.service.register(
                    name, self.password_input.text(), self.confirm_input.text())
        except WalletError as exc:
            show_error(self, str(exc), "Đăng ký thất bại")
            return
        show_info(
            self, "Đăng ký thành công",
            f"Chủ tài khoản: {name}\nSố tài khoản: {account}\n\n"
            "Hãy ghi nhớ số tài khoản để đăng nhập.",
        )
        self.reset()
        self.registered.emit(account)
