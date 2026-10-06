"""E-Wallet - ví điện tử mô phỏng (PySide6 + SQLite + SHA-256 + RSA).

Chạy:  python main.py
"""
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox


from core import database
from core.database import show_database
from core.wallet_service import WalletService
from ui.main_window import MainWindow
from ui.theme import apply_theme

def _excepthook(exc_type, exc, tb):
    traceback.print_exception(exc_type, exc, tb)
    QMessageBox.critical(None, "Lỗi hệ thống", f"{exc_type.__name__}: {exc}")


def main():
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    apply_theme(app)

    try:
        service = WalletService()          # tạo/migrate wallet.db nếu cần
    except Exception as exc:               # noqa: BLE001
        QMessageBox.critical(None, "Không mở được cơ sở dữ liệu", str(exc))
        return 1
    print(f"[db] {database.DATABASE}")

    window = MainWindow(service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    show_database()
    sys.exit(main())
