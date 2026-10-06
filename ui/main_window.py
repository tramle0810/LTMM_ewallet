"""Cửa sổ chính: gắn các màn hình lại với nhau và điều hướng."""
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout

from core.wallet_service import WalletError

from .dialogs import TransactionDialog
from .screens.dashboard import DashboardScreen
from .screens.deposit import DepositScreen
from .screens.history import HistoryScreen
from .screens.login import LoginScreen
from .screens.register import RegisterScreen
from .screens.transfer import TransferScreen
from .widgets import GradientBackground, show_error


class MainWindow(QMainWindow):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.session = None

        self.setWindowTitle("E-Wallet")
        self.resize(390, 800)
        self.setMinimumSize(360, 700)

        background = GradientBackground()
        self.setCentralWidget(background)
        outer = QVBoxLayout(background)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        self.login = LoginScreen(service)
        self.register = RegisterScreen(service)
        self.dashboard = DashboardScreen(service)
        self.deposit = DepositScreen(service)
        self.transfer = TransferScreen(service)
        self.history = HistoryScreen(service)
        for screen in (self.login, self.register, self.dashboard,
                       self.deposit, self.transfer, self.history):
            self.stack.addWidget(screen)

        self._wire()
        self.stack.setCurrentWidget(self.login)

    # ----------------------------------------------------------- kết nối
    def _wire(self):
        self.login.register_requested.connect(lambda: self.stack.setCurrentWidget(self.register))
        self.login.logged_in.connect(self._on_login)

        self.register.login_requested.connect(lambda: self.stack.setCurrentWidget(self.login))
        self.register.registered.connect(self._on_registered)

        self.dashboard.deposit_requested.connect(self._open_deposit)
        self.dashboard.transfer_requested.connect(self._open_transfer)
        self.dashboard.history_requested.connect(self._open_history)
        self.dashboard.logout_requested.connect(self._logout)
        self.dashboard.transaction_opened.connect(self._open_transaction)

        for screen in (self.deposit, self.transfer, self.history):
            screen.back_requested.connect(self._show_dashboard)
        self.deposit.completed.connect(self._on_transaction_done)
        self.transfer.completed.connect(self._on_transaction_done)
        self.history.transaction_opened.connect(self._open_transaction)

    # ------------------------------------------------------- điều hướng
    def _show_dashboard(self):
        self.dashboard.refresh()
        self.stack.setCurrentWidget(self.dashboard)

    def _on_registered(self, account_number):
        self.login.prefill(account_number)
        self.stack.setCurrentWidget(self.login)

    def _on_login(self, session):
        self.session = session
        self.dashboard.set_session(session)
        self.deposit.set_session(session)
        self.transfer.set_session(session)
        self.history.set_session(session)
        self.stack.setCurrentWidget(self.dashboard)

    def _logout(self):
        self.session = None
        self.dashboard.clear_session()
        self.deposit.set_session(None)
        self.transfer.set_session(None)
        self.history.set_session(None)
        self.login.reset()
        self.stack.setCurrentWidget(self.login)

    def _open_deposit(self):
        self.deposit.set_session(self.session)
        self.stack.setCurrentWidget(self.deposit)

    def _open_transfer(self):
        self.transfer.set_session(self.session)      # làm mới số dư + xóa form
        self.stack.setCurrentWidget(self.transfer)

    def _open_history(self):
        self.history.set_session(self.session)
        self.stack.setCurrentWidget(self.history)

    # ------------------------------------------------------- giao dịch
    def _open_transaction(self, tx_id):
        try:
            tx = self.service.get_transaction(self.session, tx_id)
        except WalletError as exc:
            show_error(self, str(exc))
            return
        TransactionDialog(self.service, self.session, tx, parent=self).exec()
        # Demo sửa/khôi phục có thể làm đổi số tiền hiển thị -> tải lại từ DB
        self.dashboard.refresh()
        if self.stack.currentWidget() is self.history:
            self.history.refresh()

    def _on_transaction_done(self, tx):
        TransactionDialog(self.service, self.session, tx, receipt=True, parent=self).exec()
        self._show_dashboard()
