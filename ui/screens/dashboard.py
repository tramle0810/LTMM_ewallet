"""Màn hình chính: số dư, thao tác nhanh, giao dịch gần đây (đọc từ wallet.db)."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QToolButton, QVBoxLayout,
)

from core.wallet_service import WalletError

from ..formatting import money_vnd, shorten
from ..icons import svg_icon, svg_pixmap
from ..theme import C
from ..widgets import (
    ScrollScreen, add_shadow, fill_transaction_rows, make_card, make_label,
    make_round_button, show_error,
)

RECENT_LIMIT = 4


class DashboardScreen(ScrollScreen):
    deposit_requested = Signal()
    transfer_requested = Signal()
    history_requested = Signal()
    logout_requested = Signal()
    transaction_opened = Signal(int)

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.session = None
        self._balance_text = ""
        self._balance_hidden = False

        root = self.root
        root.setContentsMargins(24, 28, 24, 24)

        top = QHBoxLayout()
        top.addWidget(make_label("E-WALLET", "WordMark"))
        top.addStretch()
        top.addWidget(make_round_button("log_out", self.logout_requested.emit))
        root.addLayout(top)

        root.addSpacing(20)
        root.addWidget(make_label("Xin chào,", "Muted"))
        self.name_label = make_label("", "H2")
        root.addWidget(self.name_label)

        root.addSpacing(18)
        root.addWidget(self._build_balance_card())

        root.addSpacing(18)
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        tiles.addWidget(self._tile("deposit", "Nạp tiền", self.deposit_requested.emit))
        tiles.addWidget(self._tile("send", "Chuyển tiền", self.transfer_requested.emit))
        tiles.addWidget(self._tile("clock", "Lịch sử", self.history_requested.emit))
        root.addLayout(tiles)

        root.addSpacing(18)
        panel = make_card("Panel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(22, 18, 22, 10)
        pl.setSpacing(0)
        head = QHBoxLayout()
        head.addWidget(make_label("Giao dịch gần đây", "H3"))
        head.addStretch()
        see_all = QPushButton("Xem tất cả")
        see_all.setObjectName("TextLink")
        see_all.setCursor(Qt.PointingHandCursor)
        see_all.clicked.connect(lambda _=False: self.history_requested.emit())
        head.addWidget(see_all)
        pl.addLayout(head)
        pl.addSpacing(4)
        self.recent_layout = QVBoxLayout()
        self.recent_layout.setSpacing(0)
        pl.addLayout(self.recent_layout)
        root.addWidget(panel)
        root.addStretch()

    # ----------------------------------------------------------- dựng UI
    def _build_balance_card(self):
        card = QFrame()
        card.setObjectName("BalanceCard")
        add_shadow(card, blur=36, dy=14, color=QColor(13, 27, 42, 90))
        v = QVBoxLayout(card)
        v.setContentsMargins(24, 20, 20, 22)
        v.setSpacing(0)

        top = QHBoxLayout()
        top.addWidget(make_label("SỐ DƯ KHẢ DỤNG", "CardCaption"))
        top.addStretch()
        self.eye_button = QPushButton()
        self.eye_button.setObjectName("IconBtn")
        self.eye_button.setIcon(svg_icon("eye", C.PALE, 22))
        self.eye_button.setIconSize(QSize(22, 22))
        self.eye_button.setFixedSize(34, 34)
        self.eye_button.setCursor(Qt.PointingHandCursor)
        self.eye_button.clicked.connect(lambda _=False: self._toggle_balance())
        top.addWidget(self.eye_button)
        v.addLayout(top)

        self.balance_label = make_label("", "Balance")
        v.addWidget(self.balance_label)
        v.addSpacing(14)

        self.account_label = make_label("", "CardMeta")
        v.addWidget(self.account_label)
        v.addSpacing(10)

        return card

    def _tile(self, icon_name, text, slot):
        btn = QToolButton()
        btn.setObjectName("Tile")
        btn.setIcon(svg_icon(icon_name, C.STEEL, 26))
        btn.setIconSize(QSize(26, 26))
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setStyleSheet("""
        QToolButton {
            padding-top: 17px;
            padding-bottom: 0px;
        }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(88)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.clicked.connect(lambda _=False: slot())
        return btn

    # ------------------------------------------------------------ dữ liệu
    def set_session(self, session):
        self.session = session
        self._balance_hidden = False
        self.refresh()

    def clear_session(self):
        self.session = None
        self.name_label.setText("")
        self.balance_label.setText("")
        self.account_label.setText("")
        fill_transaction_rows(self.recent_layout, [], self.transaction_opened.emit)

    def refresh(self):
        if self.session is None:
            return
        try:
            account = self.service.get_account(self.session)
            transactions = self.service.list_transactions(self.session, limit=RECENT_LIMIT)
        except WalletError as exc:
            show_error(self, str(exc))
            return
        self.name_label.setText(shorten(account.username, 24))
        self.account_label.setText(f"STK: {account.account_number}")
        self._balance_text = money_vnd(account.balance)
        self._apply_balance_visibility()
        fill_transaction_rows(self.recent_layout, transactions, self.transaction_opened.emit,
                              empty_text="Chưa có giao dịch nào.\nHãy nạp tiền để bắt đầu.")

    def _toggle_balance(self):
        self._balance_hidden = not self._balance_hidden
        self._apply_balance_visibility()

    def _apply_balance_visibility(self):
        if self._balance_hidden:
            self.balance_label.setText("••••••••")
            self.eye_button.setIcon(svg_icon("eye_off", C.PALE, 22))
        else:
            self.balance_label.setText(self._balance_text)
            self.eye_button.setIcon(svg_icon("eye", C.PALE, 22))
