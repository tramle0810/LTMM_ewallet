"""Màn hình đăng nhập."""
from PySide6.QtCore import Qt, Signal

from core.wallet_service import WalletError

from ..widgets import (
    AuthScreen, busy_cursor, make_divider, make_input, make_label, make_link,
    make_primary, show_error,
)


class LoginScreen(AuthScreen):
    logged_in = Signal(object)        # Session
    register_requested = Signal()

    def __init__(self, service):
        super().__init__()
        self.service = service
        lay = self.card_layout

        lay.addWidget(make_label("Xin chào", "H1"))
        lay.addSpacing(2)
        lay.addWidget(make_label("Đăng nhập để quản lý ví của bạn", "Subtitle"))
        lay.addSpacing(22)

        lay.addWidget(make_label("Số tài khoản", "FieldLabel"))
        lay.addSpacing(8)
        self.account_input = make_input("Nhập số tài khoản")
        lay.addWidget(self.account_input)
        lay.addSpacing(16)

        lay.addWidget(make_label("Mật khẩu", "FieldLabel"))
        lay.addSpacing(8)
        self.password_input = make_input("Nhập mật khẩu", password=True)
        lay.addWidget(self.password_input)
        lay.addSpacing(26)

        lay.addWidget(make_primary("ĐĂNG NHẬP", self.submit))
        lay.addSpacing(22)
        lay.addLayout(make_divider("Hoặc"))
        lay.addSpacing(14)
        lay.addWidget(make_label("Bạn chưa có tài khoản?", "Muted", Qt.AlignCenter))
        lay.addWidget(make_link("Đăng ký tài khoản", self.register_requested.emit))

        self.account_input.returnPressed.connect(lambda: self.password_input.setFocus())
        self.password_input.returnPressed.connect(self.submit)

    def prefill(self, account_number):
        self.account_input.setText(account_number)
        self.password_input.clear()
        self.password_input.setFocus()

    def reset(self):
        self.password_input.clear()

    def submit(self):
        try:
            with busy_cursor():
                session = self.service.login(self.account_input.text(), self.password_input.text())
        except WalletError as exc:
            show_error(self, str(exc), "Đăng nhập thất bại")
            return
        self.password_input.clear()
        self.logged_in.emit(session)
