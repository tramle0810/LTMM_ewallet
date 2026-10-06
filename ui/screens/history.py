"""Lịch sử giao dịch: lọc, mở chi tiết, xác minh toàn bộ chữ ký."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QVBoxLayout

from core.wallet_service import WalletError

from ..widgets import (
    SubScreen, busy_cursor, fill_transaction_rows, make_label, make_secondary,
    restyle, show_error,
)

FILTERS = [("Tất cả", None), ("Tiền vào", "in"), ("Tiền ra", "out")]


class HistoryScreen(SubScreen):
    transaction_opened = Signal(int)

    def __init__(self, service):
        super().__init__("Lịch sử giao dịch")
        self.service = service
        self.session = None
        self._kind = None
        self._transactions = []
        self._statuses = {}
        lay = self.panel_layout
        lay.setContentsMargins(22, 20, 22, 14)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, (text, kind) in enumerate(FILTERS):
            btn = QPushButton(text)
            btn.setObjectName("Chip")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=kind: self._set_filter(k))
            self._group.addButton(btn, i)
            chips.addWidget(btn)
        lay.addLayout(chips)
        lay.addSpacing(12)

        lay.addWidget(make_secondary("Xác minh chữ ký toàn bộ giao dịch", self.verify_all))
        lay.addSpacing(10)
        self.summary_label = make_label("", "Banner", wrap=True)
        self.summary_label.hide()
        lay.addWidget(self.summary_label)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(0)
        lay.addLayout(self.rows_layout)

    def set_session(self, session):
        self.session = session
        self._kind = None
        self._group.button(0).setChecked(True)
        self.refresh()

    def _set_filter(self, kind):
        self._kind = kind
        self.refresh()

    def refresh(self, keep_statuses=False):
        if self.session is None:
            return
        if not keep_statuses:
            self._statuses = {}
            self.summary_label.hide()
        try:
            self._transactions = self.service.list_transactions(self.session, kind=self._kind)
        except WalletError as exc:
            show_error(self, str(exc))
            return
        fill_transaction_rows(self.rows_layout, self._transactions, self.transaction_opened.emit,
                              statuses=self._statuses)

    def verify_all(self):
        if not self._transactions:
            self._show_summary("Chưa có giao dịch nào để kiểm tra.", "Banner")
            return
        try:
            with busy_cursor():
                self._statuses = {
                    tx.id: self.service.verify_transaction(self.session, tx.id).valid
                    for tx in self._transactions
                }
        except WalletError as exc:
            show_error(self, str(exc))
            return
        bad = sum(1 for ok in self._statuses.values() if not ok)
        total = len(self._statuses)
        if bad:
            self._show_summary(f"Phát hiện {bad}/{total} giao dịch không hợp lệ (dữ liệu đã bị thay đổi).",
                               "BannerBad")
        else:
            self._show_summary(f"Cả {total} giao dịch đều hợp lệ: hash SHA-256 khớp, chữ ký RSA đúng.",
                               "BannerOk")
        self.refresh(keep_statuses=True)

    def _show_summary(self, text, style):
        self.summary_label.setText(text)
        restyle(self.summary_label, style)
        self.summary_label.show()
