"""Widget dùng chung: nền gradient, ô nhập, nút, dòng giao dịch, khung màn hình."""
from contextlib import contextmanager

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget, QToolButton
)

from .formatting import is_incoming, signed_money, format_time, tx_title
from .icons import svg_icon, svg_pixmap
from .theme import C


# ------------------------------------------------------------------ nền
class GradientBackground(QWidget):
    """Nền gradient xanh navy + các vòng tròn mờ trang trí."""

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, w * 0.35, h)
        grad.setColorAt(0.00, QColor(C.ICE))
        grad.setColorAt(0.45, QColor("#8FA9BE"))
        grad.setColorAt(1.00, QColor("#3F5F86"))
        p.fillRect(self.rect(), grad)

        p.setPen(Qt.NoPen)
        circles = [  # (tâm x, tâm y, bán kính, độ mờ)
            (0.88 * w, 0.02 * h, 0.40 * w, 55),
            (-0.04 * w, 0.28 * h, 0.17 * w, 35),
            (0.04 * w, 0.79 * h + 0.52 * w, 0.52 * w, 28),
        ]
        for cx, cy, r, alpha in circles:
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))


# ------------------------------------------------------------- tiện ích
def add_shadow(widget, blur=40, dy=12, color=QColor(13, 27, 42, 70)):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(color)
    widget.setGraphicsEffect(effect)


@contextmanager
def busy_cursor():
    """Hiện con trỏ chờ trong lúc xử lý nặng (tạo khóa RSA, băm mật khẩu...)."""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def restyle(widget, object_name):
    """Đổi objectName và áp lại QSS ngay lập tức."""
    widget.setObjectName(object_name)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def make_label(text, name=None, align=None, wrap=False):
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    if align is not None:
        label.setAlignment(align)
    label.setWordWrap(wrap)
    return label


def make_input(placeholder, password=False):
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)

    if password:
        edit.setEchoMode(QLineEdit.Password)

        eye_button = QToolButton(edit)

        eye_button.setIcon(svg_icon("eye_off", C.STEEL, 20))
        eye_button.setIconSize(QSize(20, 20))

        # Kích thước vùng chứa icon
        eye_button.setFixedSize(35, 35)

        # Vị trí icon
        eye_button.move(
            edit.width() - 45,   # X: sang trái/phải
            0                    # Y: lên/xuống
        )

        eye_button.setCursor(Qt.PointingHandCursor)
        eye_button.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                padding: 0px;
            }
        """)

        def toggle():
            hidden = edit.echoMode() == QLineEdit.Password

            edit.setEchoMode(
                QLineEdit.Normal if hidden else QLineEdit.Password
            )

            eye_button.setIcon(
                svg_icon(
                    "eye" if hidden else "eye_off",
                    C.STEEL,
                    20
                )
            )

        eye_button.clicked.connect(toggle)

        # Khi kích thước QLineEdit thay đổi,
        # cập nhật lại vị trí icon
        def reposition():
            eye_button.move(
                edit.width() - 45,
                (edit.height() - eye_button.height()) // 2
            )

        edit.resizeEvent = lambda event: (
            QLineEdit.resizeEvent(edit, event),
            reposition()
        )

        reposition()

        # Chừa khoảng trống bên phải cho icon
        edit.setTextMargins(0, 0, 45, 0)

    return edit


def attach_money_format(edit, max_digits=10):
    """Tự thêm dấu phẩy ngăn cách hàng nghìn khi gõ số tiền."""
    edit.setMaxLength(max_digits + (max_digits - 1) // 3)

    def reformat(text):
        digits = "".join(ch for ch in text if ch.isdigit())[:max_digits]
        formatted = f"{int(digits):,}" if digits else ""
        if formatted != text:
            edit.blockSignals(True)
            edit.setText(formatted)
            edit.blockSignals(False)

    edit.textChanged.connect(reformat)


def parse_amount(text):
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0


def make_primary(text, slot):
    btn = QPushButton(text)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(lambda _=False: slot())
    add_shadow(btn, blur=28, dy=10, color=QColor(27, 38, 59, 90))
    return btn


def make_secondary(text, slot):
    btn = QPushButton(text)
    btn.setObjectName("Secondary")
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(lambda _=False: slot())
    return btn


def make_link(text, slot, name="Link"):
    btn = QPushButton(text)
    btn.setObjectName(name)
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(lambda _=False: slot())
    return btn


def make_line(height=2):
    line = QFrame()
    line.setObjectName("Line")
    line.setFixedHeight(height)
    return line


def make_divider(text):
    """Đường kẻ – chữ – đường kẻ, ví dụ: ───── Hoặc ─────"""
    row = QHBoxLayout()
    row.setSpacing(14)
    row.addWidget(make_line(), 1)
    row.addWidget(make_label(text, "Tiny"))
    row.addWidget(make_line(), 1)
    return row


def make_card(name="Card"):
    frame = QFrame()
    frame.setObjectName(name)
    add_shadow(frame)
    return frame


def make_round_button(icon_name, slot, color=C.INK):
    btn = QPushButton()
    btn.setObjectName("BackBtn")
    btn.setIcon(svg_icon(icon_name, color, 22))
    btn.setIconSize(QSize(22, 22))
    btn.setFixedSize(44, 44)
    btn.setCursor(Qt.PointingHandCursor)
    btn.clicked.connect(lambda _=False: slot())
    return btn


# ------------------------------------------------------------ hộp thoại
def show_error(parent, text, title="Không thể thực hiện"):
    QMessageBox.warning(parent, title, text)


def show_info(parent, title, text):
    QMessageBox.information(parent, title, text)


def confirm(parent, title, text, ok_text="Xác nhận"):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    yes = box.addButton(ok_text, QMessageBox.AcceptRole)
    box.addButton("Hủy", QMessageBox.RejectRole)
    box.exec()
    return box.clickedButton() is yes


# ------------------------------------------------------ dòng giao dịch
class TransactionRow(QWidget):
    clicked = Signal(int)

    def __init__(self, tx, verified=None):
        """verified: None (chưa kiểm tra) | True (hợp lệ) | False (bị thay đổi)."""
        super().__init__()
        self.tx_id = tx.id
        self.setCursor(Qt.PointingHandCursor)
        incoming = is_incoming(tx)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 10, 0, 10)
        row.setSpacing(14)

        badge = QLabel()
        badge.setObjectName("Badge")
        badge.setFixedSize(44, 44)
        badge.setAlignment(Qt.AlignCenter)
        badge.setPixmap(svg_pixmap("arrow_down_left" if incoming else "arrow_up_right", C.STEEL, 22))
        row.addWidget(badge)

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(make_label(tx_title(tx), "RowTitle"))
        text.addWidget(make_label(format_time(tx.timestamp), "RowSub"))
        row.addLayout(text, 1)

        right = QVBoxLayout()
        right.setSpacing(2)
        right.addWidget(make_label(signed_money(tx), "AmountIn" if incoming else "AmountOut", Qt.AlignRight))
        if verified is not None:
            right.addWidget(make_label(
                "Hợp lệ" if verified else "Bị thay đổi",
                "StatusOk" if verified else "StatusBad", Qt.AlignRight))
        row.addLayout(right)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.tx_id)
        super().mouseReleaseEvent(event)


def fill_transaction_rows(layout, transactions, on_click, statuses=None, empty_text="Chưa có giao dịch nào"):
    """Xóa và dựng lại danh sách dòng giao dịch trong `layout`."""
    clear_layout(layout)
    if not transactions:
        layout.addWidget(make_label(empty_text, "Empty", Qt.AlignCenter))
        return
    for i, tx in enumerate(transactions):
        if i:
            layout.addWidget(make_line(1))
        row = TransactionRow(tx, (statuses or {}).get(tx.id))
        row.clicked.connect(on_click)
        layout.addWidget(row)


# ------------------------------------------------------- khung màn hình
class ScrollScreen(QScrollArea):
    """Màn hình cuộn được, nền trong suốt để thấy gradient phía sau."""

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.setWidget(self.content)
        self.root = QVBoxLayout(self.content)
        self.root.setSpacing(0)


class AuthScreen(ScrollScreen):
    """Khung Đăng nhập / Đăng ký: tiêu đề E-WALLET + card trắng + icon khiên."""

    def __init__(self):
        super().__init__()
        self.root.setContentsMargins(24, 40, 24, 24)
        self.root.addWidget(make_label("E-WALLET", "AppTitle", Qt.AlignCenter))
        self.root.addSpacing(30)

        card = make_card("Card")
        self.card_layout = QVBoxLayout(card)
        self.card_layout.setContentsMargins(30, 32, 30, 28)
        self.card_layout.setSpacing(0)
        self.root.addWidget(card)

        shield = QLabel()
        shield.setPixmap(svg_pixmap("shield", C.STEEL, 30, 1.8))
        shield.setAlignment(Qt.AlignCenter)
        self.root.addSpacing(24)
        self.root.addWidget(shield)
        self.root.addStretch()


class SubScreen(ScrollScreen):
    """Khung trang con: nút quay lại + tiêu đề + panel trắng."""

    back_requested = Signal()

    def __init__(self, title):
        super().__init__()
        self.root.setContentsMargins(24, 28, 24, 24)

        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(make_round_button("arrow_left", self.back_requested.emit))
        head.addWidget(make_label(title, "H2"))
        head.addStretch()
        self.root.addLayout(head)
        self.root.addSpacing(24)

        panel = make_card("Panel")
        self.panel_layout = QVBoxLayout(panel)
        self.panel_layout.setContentsMargins(24, 24, 24, 24)
        self.panel_layout.setSpacing(0)
        self.root.addWidget(panel)
        self.root.addStretch()
