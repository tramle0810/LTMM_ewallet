"""Chạy: python -m unittest discover -s tests -v   (không cần PySide6)"""
import hashlib
import os
import shutil
import sqlite3
import tempfile
import unittest

from core import database as db
from core.wallet_service import WalletError, WalletService

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "test.db")
        self.svc = WalletService(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_user(self, name, password="123456"):
        account = self.svc.register(name, password, password)
        return account, self.svc.login(account, password)


class TestAccounts(ServiceTestCase):
    def test_register_and_login(self):
        account, session = self.make_user("Nguyen Van A")
        self.assertEqual(account, "10000001")
        self.assertEqual(session.username, "Nguyen Van A")
        self.assertEqual(self.svc.get_account(session).balance, 0)

    def test_account_numbers_increment(self):
        a, _ = self.make_user("Alice")
        b, _ = self.make_user("Bob")
        self.assertEqual(int(b), int(a) + 1)

    def test_wrong_password_and_unknown_account(self):
        account, _ = self.make_user("Alice")
        with self.assertRaises(WalletError):
            self.svc.login(account, "sai-mat-khau")
        with self.assertRaises(WalletError):
            self.svc.login("99999999", "123456")

    def test_register_validation(self):
        with self.assertRaises(WalletError):
            self.svc.register("", "123456", "123456")
        with self.assertRaises(WalletError):
            self.svc.register("A", "123", "123")
        with self.assertRaises(WalletError):
            self.svc.register("Abc", "123456", "654321")

    def test_private_key_and_password_are_protected(self):
        account, _ = self.make_user("Alice")
        with db.connect(self.path) as conn:
            row = conn.execute("SELECT * FROM users").fetchone()
        self.assertIn("ENCRYPTED", row["private_key"].splitlines()[0])
        self.assertTrue(row["password"].startswith("pbkdf2_sha256$"))

    def test_lookup_account(self):
        account, _ = self.make_user("Tran B")
        self.assertEqual(self.svc.lookup_account(account), "Tran B")
        self.assertIsNone(self.svc.lookup_account("000"))


class TestTransactions(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.acc_a, self.a = self.make_user("Alice")
        self.acc_b, self.b = self.make_user("Bob")

    def test_deposit_updates_balance_and_is_signed(self):
        tx = self.svc.deposit(self.a, 2_000_000)
        self.assertEqual(tx.kind, "deposit")
        self.assertEqual(self.svc.get_account(self.a).balance, 2_000_000)
        self.assertTrue(self.svc.verify_transaction(self.a, tx.id).valid)

    def test_transfer(self):
        self.svc.deposit(self.a, 1_000_000)
        tx = self.svc.transfer(self.a, self.acc_b, 400_000)
        self.assertEqual(tx.kind, "transfer_out")
        self.assertEqual(self.svc.get_account(self.a).balance, 600_000)
        self.assertEqual(self.svc.get_account(self.b).balance, 400_000)
        # người nhận thấy giao dịch dạng "tiền vào" và xác minh được
        incoming = self.svc.list_transactions(self.b)[0]
        self.assertEqual(incoming.kind, "transfer_in")
        self.assertTrue(self.svc.verify_transaction(self.b, incoming.id).valid)

    def test_transfer_rejections(self):
        self.svc.deposit(self.a, 100_000)
        with self.assertRaises(WalletError):
            self.svc.transfer(self.a, self.acc_b, 200_000)      # không đủ số dư
        with self.assertRaises(WalletError):
            self.svc.transfer(self.a, self.acc_a, 1_000)        # tự chuyển cho mình
        with self.assertRaises(WalletError):
            self.svc.transfer(self.a, "00000000", 1_000)        # không có người nhận
        with self.assertRaises(WalletError):
            self.svc.transfer(self.a, self.acc_b, 0)
        with self.assertRaises(WalletError):
            self.svc.transfer(self.a, self.acc_b, 10.5)
        self.assertEqual(self.svc.get_account(self.a).balance, 100_000)
        self.assertEqual(self.svc.get_account(self.b).balance, 0)

    def test_failed_transfer_is_atomic(self):
        """Lỗi giữa chừng không được làm lệch số dư."""
        self.svc.deposit(self.a, 500_000)
        bad = type(self.a)(self.a.user_id, self.a.account_number, self.a.username, "khong-phai-pem")
        with self.assertRaises(Exception):
            self.svc.transfer(bad, self.acc_b, 100_000)   # ký thất bại sau khi tính số dư
        self.assertEqual(self.svc.get_account(self.a).balance, 500_000)
        self.assertEqual(self.svc.get_account(self.b).balance, 0)
        self.assertEqual(len(self.svc.list_transactions(self.b)), 0)

    def test_history_filters_and_permissions(self):
        self.svc.deposit(self.a, 1_000_000)
        out = self.svc.transfer(self.a, self.acc_b, 100_000)
        self.assertEqual(len(self.svc.list_transactions(self.a)), 2)
        self.assertEqual([t.kind for t in self.svc.list_transactions(self.a, kind="out")], ["transfer_out"])
        self.assertEqual([t.kind for t in self.svc.list_transactions(self.a, kind="in")], ["deposit"])
        self.assertEqual([t.kind for t in self.svc.list_transactions(self.b, kind="in")], ["transfer_in"])
        self.assertEqual(self.svc.list_transactions(self.b, kind="out"), [])
        _, c = self.make_user("Carol")
        with self.assertRaises(WalletError):
            self.svc.get_transaction(c, out.id)               # người ngoài không xem được

    def test_tamper_detected_and_restore(self):
        self.svc.deposit(self.a, 1_000_000)
        tx = self.svc.transfer(self.a, self.acc_b, 100_000)
        self.assertTrue(self.svc.verify_transaction(self.a, tx.id).valid)

        self.svc.tamper_transaction(self.a, tx.id)
        result = self.svc.verify_transaction(self.a, tx.id)
        self.assertFalse(result.valid)
        self.assertFalse(result.hash_ok)
        self.assertFalse(result.signature_ok)
        self.assertTrue(self.svc.get_transaction(self.a, tx.id).tampered)

        self.svc.restore_transaction(self.a, tx.id)
        self.assertTrue(self.svc.verify_transaction(self.a, tx.id).valid)
        self.assertFalse(self.svc.get_transaction(self.a, tx.id).tampered)


class TestLegacyMigration(unittest.TestCase):
    """DB đời đầu (password_hash, tx_id, ...) phải được migrate mà user vẫn đăng nhập được."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "legacy.db")
        from core.crypto_utils import generate_key_pair
        self.private_pem, public_pem = generate_key_pair()
        conn = sqlite3.connect(self.path)
        conn.executescript("""
            CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                password_hash TEXT NOT NULL, account_number TEXT UNIQUE NOT NULL,
                balance INTEGER DEFAULT 0, private_key TEXT NOT NULL, public_key TEXT NOT NULL,
                created_at TEXT NOT NULL);
            CREATE TABLE transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, tx_id TEXT UNIQUE NOT NULL,
                sender_account TEXT, receiver_account TEXT, amount INTEGER NOT NULL, description TEXT,
                tx_hash TEXT NOT NULL, signature TEXT NOT NULL, created_at TEXT NOT NULL,
                status TEXT DEFAULT 'SUCCESS');
        """)
        conn.execute("INSERT INTO users(username,password_hash,account_number,balance,private_key,"
                     "public_key,created_at) VALUES (?,?,?,?,?,?,?)",
                     ("thtram", hashlib.sha256(b"123456").hexdigest(), "1074051611", 0,
                      self.private_pem, public_pem, "01/10/2026 16:48:51"))
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_migrate_and_login_upgrades_security(self):
        svc = WalletService(self.path)
        self.assertTrue(any(f.startswith("legacy.db.bak_") for f in os.listdir(self.tmp)))
        session = svc.login("1074051611", "123456")
        self.assertEqual(session.username, "thtram")
        with db.connect(self.path) as conn:
            row = conn.execute("SELECT * FROM users").fetchone()
        self.assertTrue(row["password"].startswith("pbkdf2_sha256$"))
        self.assertIn("ENCRYPTED", row["private_key"].splitlines()[0])
        # đăng nhập lại sau khi nâng cấp vẫn được, và ký giao dịch được
        session = svc.login("1074051611", "123456")
        self.assertTrue(svc.deposit(session, 50_000).amount == 50_000)
        # bảng cũ được giữ làm bản lưu
        with db.connect(self.path) as conn:
            names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("legacy_users_backup", names)
        self.assertIn("legacy_transactions_backup", names)


if __name__ == "__main__":
    unittest.main()
