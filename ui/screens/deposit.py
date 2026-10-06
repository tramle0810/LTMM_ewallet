"""Màn hình nạp tiền."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QPushButton

from core.wallet_service import WalletError

from ..widgets import (
    SubScreen, attach_money_format, busy_cursor, make_input, make_label, make_primary,
    parse_amount, show_error,
)

QUICK_AMOUNTS = [100_000, 200_000, 500_000, 1_000_000]


class DepositScreen(SubScreen):
    completed = Signal(object)        # TransactionView

    def __init__(self, service):
        super().__init__("Nạp tiền vào ví")
        self.service = service
        self.session = None
        lay = self.panel_layout

        lay.addWidget(make_label(
            "Ví mô phỏng: khoản nạp được ghi vào database, băm SHA-256 và ký bằng RSA.",
            "Banner", wrap=True))
        lay.addSpacing(18)
        lay.addWidget(make_label("Số tiền muốn nạp (VNĐ)", "FieldLabel"))
        lay.addSpacing(8)
        self.amount_input = make_input("Nhập số tiền")
        attach_money_format(self.amount_input)
        lay.addWidget(self.amount_input)
        lay.addSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, value in enumerate(QUICK_AMOUNTS):
            chip = QPushButton(f"{value:,}")
            chip.setObjectName("Chip")
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _=False, v=value: self.amount_input.setText(f"{v:,}"))
            grid.addWidget(chip, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addSpacing(26)
        lay.addWidget(make_primary("XÁC NHẬN NẠP TIỀN", self.submit))

        self.amount_input.returnPressed.connect(self.submit)

    def set_session(self, session):
        self.session = session
        self.amount_input.clear()

    def submit(self):
        if self.session is None:
            return
        amount = parse_amount(self.amount_input.text())
        if amount <= 0:
            show_error(self, "Vui lòng nhập số tiền lớn hơn 0.", "Số tiền không hợp lệ")
            return
        try:
            with busy_cursor():
                tx = self.service.deposit(self.session, amount)
        except WalletError as exc:
            show_error(self, str(exc))
            return
        self.amount_input.clear()
        self.completed.emit(tx)
