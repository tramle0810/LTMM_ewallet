"""Hộp thoại chi tiết / biên lai giao dịch, có xác minh SHA-256 + RSA."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout

from core.wallet_service import TAMPER_DELTA, WalletError

from .formatting import (
    format_time, is_incoming, money, signed_money, tx_type_label, wrap_chunks,
)
from .icons import svg_pixmap
from .theme import C
from .widgets import (
    clear_layout, confirm, make_label, make_line, make_link, make_primary, show_error,
)


class TransactionDialog(QDialog):
    def __init__(self, service, session, tx, receipt=False, parent=None):
        super().__init__(parent)
        self.setObjectName("Sheet")
        self.setWindowTitle("Chi tiết giao dịch")
        self.setModal(True)
        self.setMinimumWidth(370)

        self.service = service
        self.session = session
        self.tx = tx
        self.receipt = receipt
        self._result = None          # VerifyResult của lần xác minh gần nhất

        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(24, 24, 24, 18)
        self.body.setSpacing(0)
        self._render()

    # ----------------------------------------------------------- dựng UI
    def _info_row(self, key, value):
        row = QHBoxLayout()
        row.addWidget(make_label(key, "InfoKey"))
        row.addStretch()
        row.addWidget(make_label(value, "InfoVal", Qt.AlignRight))
        self.body.addLayout(row)
        self.body.addSpacing(10)

    def _mono_block(self, key, text):
        self.body.addWidget(make_label(key, "InfoKey"))
        self.body.addSpacing(4)
        label = make_label(text, "Mono")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.addWidget(label)
        self.body.addSpacing(12)

    def _render(self):
        clear_layout(self.body)
        tx, b = self.tx, self.body

        if self.receipt:
            icon = QLabel()
            icon.setPixmap(svg_pixmap("check_circle", C.IN, 52, 1.8))
            icon.setAlignment(Qt.AlignCenter)
            b.addWidget(icon)
            b.addSpacing(8)
            b.addWidget(make_label("Giao dịch thành công", "H2", Qt.AlignCenter))
        else:
            b.addWidget(make_label("Chi tiết giao dịch", "H2", Qt.AlignCenter))
        b.addSpacing(10)

        incoming = is_incoming(tx)
        b.addWidget(make_label(f"{signed_money(tx)} VNĐ", "BigIn" if incoming else "BigOut", Qt.AlignCenter))
        b.addSpacing(16)
        b.addWidget(make_line(1))
        b.addSpacing(16)

        self._info_row("Loại giao dịch", tx_type_label(tx))
        if tx.kind != "deposit":
            self._info_row("Người gửi" if tx.kind == "transfer_in" else "Người nhận", tx.counterparty_name)
            self._info_row("Số tài khoản", tx.counterparty_account)
        self._info_row("Thời gian", format_time(tx.timestamp, with_seconds=True))
        self._info_row("Mã giao dịch", f"#{tx.id}")

        b.addWidget(make_line(1))
        b.addSpacing(14)
    
        if self._result is not None:
            b.addWidget(make_label(self._result.message, "BannerOk" if self._result.valid else "BannerBad",
                                   wrap=True))
            b.addSpacing(14)

        b.addWidget(make_primary("XÁC MINH CHỮ KÝ", self._verify))
        b.addSpacing(10)
        b.addWidget(make_link("Đóng", self.accept))

    # ------------------------------------------------------------ hành động
    def _reload(self):
        self.tx = self.service.get_transaction(self.session, self.tx.id)
        self._result = None
        self._render()

    def _verify(self):
        try:
            self._result = self.service.verify_transaction(self.session, self.tx.id)
        except WalletError as exc:
            show_error(self, str(exc))
            return
        self._render()

    def _tamper(self):
        if not confirm(
            self, "Demo giả mạo dữ liệu",
            f"Số tiền của giao dịch #{self.tx.id} trong database sẽ bị cộng thêm "
            f"{money(TAMPER_DELTA)} VNĐ (không ảnh hưởng số dư).\n"
            "Bạn có thể khôi phục lại bất cứ lúc nào.",
            "Sửa dữ liệu",
        ):
            return
        try:
            self.service.tamper_transaction(self.session, self.tx.id)
            self._reload()
        except WalletError as exc:
            show_error(self, str(exc))

    def _restore(self):
        try:
            self.service.restore_transaction(self.session, self.tx.id)
            self._reload()
        except WalletError as exc:
            show_error(self, str(exc))
