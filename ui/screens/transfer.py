"""Màn hình chuyển tiền (ký RSA)."""
from PySide6.QtCore import Signal

from core.wallet_service import WalletError

from ..formatting import money, money_vnd
from ..widgets import (
    SubScreen, attach_money_format, busy_cursor, confirm, make_input, make_label,
    make_primary, parse_amount, restyle, show_error,
)


class TransferScreen(SubScreen):
    completed = Signal(object)        # TransactionView

    def __init__(self, service):
        super().__init__("Chuyển tiền")
        self.service = service
        self.session = None
        lay = self.panel_layout

        lay.addWidget(make_label(
            "Giao dịch được băm SHA-256 và ký bằng khóa riêng RSA của bạn.", "Banner", wrap=True))
        lay.addSpacing(14)
        self.balance_label = make_label("", "Hint")
        lay.addWidget(self.balance_label)
        lay.addSpacing(14)

        lay.addWidget(make_label("Số tài khoản người nhận", "FieldLabel"))
        lay.addSpacing(8)
        self.account_input = make_input("Nhập số tài khoản nhận")
        lay.addWidget(self.account_input)
        lay.addSpacing(6)
        self.recipient_hint = make_label("", "Hint")
        lay.addWidget(self.recipient_hint)
        lay.addSpacing(10)

        lay.addWidget(make_label("Số tiền chuyển (VNĐ)", "FieldLabel"))
        lay.addSpacing(8)
        self.amount_input = make_input("Nhập số tiền")
        attach_money_format(self.amount_input)
        lay.addWidget(self.amount_input)
        lay.addSpacing(26)

        lay.addWidget(make_primary("CHUYỂN TIỀN", self.submit))

        self.account_input.textChanged.connect(self._update_recipient_hint)
        self.account_input.returnPressed.connect(lambda: self.amount_input.setFocus())
        self.amount_input.returnPressed.connect(self.submit)

    # ------------------------------------------------------------ dữ liệu
    def set_session(self, session):
        self.session = session
        self.refresh()

    def refresh(self):
        self.account_input.clear()
        self.amount_input.clear()
        self._set_hint("", "Hint")
        if self.session is None:
            return
        try:
            balance = self.service.get_account(self.session).balance
            self.balance_label.setText(f"Số dư khả dụng: {money_vnd(balance)}")
        except WalletError as exc:
            show_error(self, str(exc))

    def _set_hint(self, text, style):
        self.recipient_hint.setText(text)
        restyle(self.recipient_hint, style)

    def _update_recipient_hint(self, text):
        text = text.strip()
        if not text:
            self._set_hint("", "Hint")
        elif self.session is not None and text == self.session.account_number:
            self._set_hint("Không thể chuyển tiền cho chính mình", "HintBad")
        else:
            name = self.service.lookup_account(text)
            if name:
                self._set_hint(f"Người nhận: {name}", "HintOk")
            else:
                self._set_hint("Không tìm thấy tài khoản", "HintBad")

    def submit(self):
        if self.session is None:
            return
        account = self.account_input.text().strip()
        amount = parse_amount(self.amount_input.text())
        if not account or amount <= 0:
            show_error(self, "Vui lòng nhập số tài khoản và số tiền hợp lệ.", "Thiếu thông tin")
            return
        name = self.service.lookup_account(account)
        if name is None:
            show_error(self, "Không tìm thấy tài khoản người nhận.")
            return
        if not confirm(
            self, "Xác nhận chuyển tiền",
            f"Chuyển {money(amount)} VNĐ đến\n{name} (STK {account})?",
            "Ký & chuyển",
        ):
            return
        try:
            with busy_cursor():
                tx = self.service.transfer(self.session, account, amount)
        except WalletError as exc:
            show_error(self, str(exc), "Chuyển tiền thất bại")
            return
        self.completed.emit(tx)
