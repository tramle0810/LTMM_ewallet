"""Màu sắc, font chữ và style sheet (QSS) của toàn bộ ứng dụng."""
import os

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ màu
class C:
    INK = "#1B263B"        # Deep Navy – chữ chính, nút
    NAVY = "#0D1B2A"       # Navy – nhấn đậm
    STEEL = "#3D5A80"      # Steel Blue – accent, icon
    AIRY = "#98B4C7"       # Airy Blue
    PALE = "#D8E6F2"       # Pale Blue
    ICE = "#EAF2F8"        # Ice Blue
    BEIGE = "#F2EFE7"
    MUTED = "#5F7C97"      # chữ phụ
    LINE = "#E6ECF3"       # viền input / đường kẻ
    PLACEHOLDER = "#9AA8B7"
    IN = "#2F7F73"         # tiền vào / hợp lệ
    OUT = "#C0524A"        # tiền ra / không hợp lệ


# ----------------------------------------------------------------- font
class Fonts:
    isometra = "Arial Black"      # dự phòng nếu thiếu Isometra
    regular = "Segoe UI"
    medium = "Segoe UI"
    medium_weight = 600


def load_fonts():
    """Nạp font từ ./fonts (hoặc thư mục gốc dự án). Gọi sau khi có QApplication."""
    folders = [os.path.join(ROOT, "fonts"), ROOT]

    def register(filename):
        for folder in folders:
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        return families[0]
        print(f"[font] Không tìm thấy {filename} - dùng font dự phòng")
        return None

    iso = register("Isometra-Regular.ttf")
    reg = register("Roboto-Regular.ttf")
    med = register("Roboto-Medium.ttf")

    if iso:
        Fonts.isometra = iso
    if reg:
        Fonts.regular = reg
    if med:
        Fonts.medium = med
        # Medium và Regular cùng family "Roboto" -> chọn Medium bằng weight 500
        Fonts.medium_weight = 500 if med == Fonts.regular else 400
    else:
        Fonts.medium = Fonts.regular
        Fonts.medium_weight = 600


# ------------------------------------------------------------------ QSS
_QSS = """
/* ---------- Chữ ---------- */
QLabel { background: transparent; color: @INK@; font-family: "@REG@"; font-size: 15px; }
QLabel#AppTitle  { font-family: "@ISO@"; font-size: 34px; }
QLabel#WordMark  { font-family: "@ISO@"; font-size: 30px; }
QLabel#H1 { font-family: "@MED@"; font-weight: @MEDW@; font-size: 34px; }
QLabel#H2 { font-family: "@MED@"; font-weight: @MEDW@; font-size: 22px; }
QLabel#H3 { font-family: "@MED@"; font-weight: @MEDW@; font-size: 17px; }
QLabel#Subtitle { font-family: "@MED@"; font-weight: @MEDW@; font-size: 15px; color: @MUTED@; }
QLabel#FieldLabel { font-size: 15px; }
QLabel#Muted { color: @MUTED@; font-size: 15px; }
QLabel#Tiny  { color: @MUTED@; font-size: 12px; }
QLabel#Hint  { color: @MUTED@; font-size: 13px; }
QLabel#HintOk  { color: @IN@;  font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px; }
QLabel#HintBad { color: @OUT@; font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px; }
QLabel#Empty { color: @MUTED@; font-size: 14px; padding: 18px 0; }

QLabel#CardCaption { font-family: "@MED@"; font-weight: @MEDW@; font-size: 15px; color: @AIRY@; }
QLabel#CardMeta    { font-size: 15px; color: @PALE@; }
QLabel#Balance     { font-family: "@MED@"; font-weight: @MEDW@; font-size: 32px; color: white; }

QLabel#RowTitle  { font-family: "@MED@"; font-weight: @MEDW@; font-size: 15px; }
QLabel#RowSub    { font-size: 12px; color: @MUTED@; }
QLabel#AmountIn  { font-family: "@MED@"; font-weight: @MEDW@; font-size: 15px; color: @IN@; }
QLabel#AmountOut { font-family: "@MED@"; font-weight: @MEDW@; font-size: 15px; color: @OUT@; }
QLabel#StatusOk  { font-family: "@MED@"; font-weight: @MEDW@; font-size: 11px; color: @IN@; }
QLabel#StatusBad { font-family: "@MED@"; font-weight: @MEDW@; font-size: 11px; color: @OUT@; }
QLabel#Badge     { background: @PALE@; border-radius: 22px; }

QLabel#Banner {
    background: @ICE@; color: @STEEL@; border-radius: 16px; padding: 12px 14px;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px;
}
QLabel#BannerOk {
    background: #E3F3EF; color: @IN@; border-radius: 16px; padding: 12px 14px;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px;
}
QLabel#BannerBad {
    background: #FBE9E7; color: @OUT@; border-radius: 16px; padding: 12px 14px;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px;
}

QLabel#InfoKey { color: @MUTED@; font-size: 13px; }
QLabel#InfoVal { font-family: "@MED@"; font-weight: @MEDW@; font-size: 14px; }
QLabel#Mono {
    font-family: "Consolas", "Menlo", "DejaVu Sans Mono", monospace; font-size: 12px;
    color: @INK@;
}
QLabel#BigIn  { font-family: "@MED@"; font-weight: @MEDW@; font-size: 30px; color: @IN@; }
QLabel#BigOut { font-family: "@MED@"; font-weight: @MEDW@; font-size: 30px; color: @OUT@; }

/* ---------- Khung ---------- */
QFrame#Card  { background: rgba(255,255,255,245); border-radius: 36px; }
QFrame#Panel { background: rgba(255,255,255,245); border-radius: 26px; }
QFrame#BalanceCard {
    border-radius: 28px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 @INK@, stop:1 @STEEL@);
}
QFrame#Line { background: @LINE@; border: none; }
QDialog#Sheet { background: white; }

/* ---------- Ô nhập ---------- */
QLineEdit {
    background: #F8FAFC; border: 2px solid @LINE@; border-radius: 26px;
    padding: 0 16px 0 20px; min-height: 48px;
    font-family: "@REG@"; font-size: 16px; color: @INK@;
    selection-background-color: @PALE@; selection-color: @INK@;
}
QLineEdit:focus { border: 2px solid @STEEL@; background: white; }

/* ---------- Nút ---------- */
QPushButton#Primary {
    color: white; border: none; border-radius: 28px; min-height: 56px;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 17px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @INK@, stop:1 @STEEL@);
}
QPushButton#Primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #24344F, stop:1 #4A6E9A);
}
QPushButton#Primary:pressed { background: @NAVY@; }
QPushButton#Primary:disabled { background: @AIRY@; }

QPushButton#Secondary {
    color: @INK@; background: white; border: 2px solid @LINE@; border-radius: 22px;
    min-height: 40px; font-family: "@MED@"; font-weight: @MEDW@; font-size: 14px;
}
QPushButton#Secondary:hover { background: @ICE@; border-color: @AIRY@; }

QPushButton#Link {
    background: transparent; border: none; color: @INK@;
    font-family: "@REG@"; font-size: 17px; min-height: 34px;
}
QPushButton#Link:hover { color: @STEEL@; }

QPushButton#TextLink {
    background: transparent; border: none; color: @STEEL@;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px; min-height: 28px;
}
QPushButton#TextLink:hover { color: @INK@; }

QPushButton#IconBtn { background: transparent; border: none; }
QPushButton#BackBtn {
    background: rgba(255,255,255,190); border: none; border-radius: 22px;
}
QPushButton#BackBtn:hover { background: white; }

QPushButton#Chip {
    background: #F1F5F9; border: 2px solid @LINE@; border-radius: 20px; min-height: 36px;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px; color: @INK@;
}
QPushButton#Chip:hover { background: @PALE@; }
QPushButton#Chip:checked { background: @INK@; border-color: @INK@; color: white; }

QToolButton#Tile {
    background: rgba(255,255,255,245); border: none; border-radius: 22px;
    color: @INK@; font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px;
    padding-top: 10px;
}
QToolButton#Tile:hover { background: @ICE@; }

/* ---------- Scroll (trong suốt, ẩn thanh cuộn) ---------- */
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { width: 0px; background: transparent; }

/* ---------- Hộp thoại ---------- */
QMessageBox { background: white; }
QMessageBox QLabel { color: @INK@; font-size: 14px; }
QMessageBox QPushButton {
    background: @STEEL@; color: white; border: none; border-radius: 14px;
    min-width: 84px; padding: 8px 16px;
    font-family: "@MED@"; font-weight: @MEDW@; font-size: 13px;
}
QMessageBox QPushButton:hover { background: @INK@; }
"""


def build_stylesheet():
    tokens = {
        "INK": C.INK, "NAVY": C.NAVY, "STEEL": C.STEEL, "AIRY": C.AIRY,
        "PALE": C.PALE, "ICE": C.ICE, "MUTED": C.MUTED, "LINE": C.LINE,
        "IN": C.IN, "OUT": C.OUT,
        "REG": Fonts.regular, "MED": Fonts.medium, "ISO": Fonts.isometra,
        "MEDW": str(Fonts.medium_weight),
    }
    qss = _QSS
    for key, value in tokens.items():
        qss = qss.replace(f"@{key}@", value)
    return qss


def apply_theme(app):
    """Nạp font, đặt font mặc định, style sheet và màu placeholder cho cả ứng dụng."""
    load_fonts()
    app.setFont(QFont(Fonts.regular, 11))
    app.setStyleSheet(build_stylesheet())
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(C.PLACEHOLDER))
    app.setPalette(palette)
