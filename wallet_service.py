
"""Tầng nghiệp vụ ví điện tử: đăng ký, đăng nhập, giao dịch và xác minh."""

from dataclasses import dataclass, field
from datetime import datetime
import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import crypto_utils as cu
from . import database as db


MAX_AMOUNT = 1_000_000_000
MIN_PASSWORD_LENGTH = 6
TAMPER_DELTA = 1_000_000

PASSWORD_ITERATIONS = 600_000
PRIVATE_KEY_PREFIX = "ENC1$"


class WalletError(Exception):
    """Lỗi nghiệp vụ có thông điệp hiển thị cho người dùng."""


# ============================================================
# MODELS
# ============================================================

@dataclass(frozen=True)
class Session:
    user_id: int
    account_number: str
    username: str
    private_key_pem: str = field(repr=False, default="")


@dataclass(frozen=True)
class AccountInfo:
    user_id: int
    account_number: str
    username: str
    balance: float


@dataclass(frozen=True)
class TransactionView:
    id: int
    kind: str
    amount: float
    timestamp: str
    counterparty_name: str
    counterparty_account: str
    sender_account: str
    receiver_account: str
    tx_hash: str
    signature: str
    tampered: bool = False


@dataclass(frozen=True)
class VerifyResult:
    valid: bool
    hash_ok: bool
    signature_ok: bool
    message: str


# ============================================================
# PASSWORD
# ============================================================

def _hash_password(password):
    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    return (
        f"PBKDF2${PASSWORD_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )


def _verify_password(password, stored):
    """Trả về (mật khẩu đúng, cần nâng cấp định dạng hay không)."""

    if not stored:
        return False, False

    if stored.startswith("PBKDF2$"):
        try:
            _, iterations, salt_b64, digest_b64 = stored.split("$")

            salt = base64.b64decode(salt_b64, validate=True)
            expected = base64.b64decode(digest_b64, validate=True)

            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                int(iterations),
            )

            return hmac.compare_digest(actual, expected), False

        except (ValueError, TypeError):
            return False, False

    # Tương thích SHA-256 thuần từ phiên bản cũ.
    if len(stored) == 64:
        try:
            int(stored, 16)
            actual = hashlib.sha256(
                password.encode("utf-8")
            ).hexdigest()

            if hmac.compare_digest(actual, stored.lower()):
                return True, True

            return False, False

        except ValueError:
            pass

    # Tương thích tài khoản cũ lưu mật khẩu dạng văn bản.
    if hmac.compare_digest(password, stored):
        return True, True

    return False, False


# ============================================================
# PRIVATE KEY ENCRYPTION
# ============================================================

def _encrypt_private_key(private_pem, password):
    """Mã hóa khóa RSA bằng AES-256-GCM."""

    salt = os.urandom(16)
    nonce = os.urandom(12)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
        dklen=32,
    )

    ciphertext = AESGCM(key).encrypt(
        nonce,
        private_pem.encode("utf-8"),
        None,
    )

    packed = salt + nonce + ciphertext

    return PRIVATE_KEY_PREFIX + base64.b64encode(
        packed
    ).decode("ascii")


def _is_encrypted_private_key(value):
    return (
        isinstance(value, str)
        and value.startswith(PRIVATE_KEY_PREFIX)
    )


def _decrypt_private_key(encrypted, password):
    """Giải mã khóa riêng; sai mật khẩu sẽ phát sinh lỗi."""

    packed = base64.b64decode(
        encrypted[len(PRIVATE_KEY_PREFIX):],
        validate=True,
    )

    if len(packed) < 44:
        raise ValueError("Dữ liệu khóa riêng không hợp lệ.")

    salt = packed[:16]
    nonce = packed[16:28]
    ciphertext = packed[28:]

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
        dklen=32,
    )

    plaintext = AESGCM(key).decrypt(
        nonce,
        ciphertext,
        None,
    )

    return plaintext.decode("utf-8")


# ============================================================
# HELPERS
# ============================================================

def transaction_payload(
    sender_id,
    receiver_id,
    amount,
    s_old,
    s_new,
    r_old,
    r_new,
    timestamp,
):
    """Chuỗi dữ liệu dùng chung khi ký và xác minh giao dịch."""

    return (
        f"{int(sender_id)}|{int(receiver_id)}|{float(amount)}|"
        f"{float(s_old)}|{float(s_new)}|"
        f"{float(r_old)}|{float(r_new)}|{timestamp}"
    )


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_TX_SELECT = """
    SELECT t.*,
           s.username AS sender_name,
           s.account_number AS sender_account,
           r.username AS receiver_name,
           r.account_number AS receiver_account,
           (b.tx_id IS NOT NULL) AS tampered
    FROM transactions t
    JOIN users s ON s.id = t.sender_id
    JOIN users r ON r.id = t.receiver_id
    LEFT JOIN tamper_backup b ON b.tx_id = t.id
"""


def _to_view(row, user_id):
    if row["type"] == "deposit":
        kind, name, account = "deposit", "", ""

    elif row["sender_id"] == user_id:
        kind = "transfer_out"
        name = row["receiver_name"]
        account = row["receiver_account"]

    else:
        kind = "transfer_in"
        name = row["sender_name"]
        account = row["sender_account"]

    return TransactionView(
        id=row["id"],
        kind=kind,
        amount=float(row["amount"]),
        timestamp=row["timestamp"],
        counterparty_name=name,
        counterparty_account=account,
        sender_account=row["sender_account"],
        receiver_account=row["receiver_account"],
        tx_hash=row["transaction_hash"],
        signature=row["signature"],
        tampered=bool(row["tampered"]),
    )


# ============================================================
# WALLET SERVICE
# ============================================================

class WalletService:

    def __init__(self, db_path=None):
        self.db_path = db_path or db.DATABASE
        db.init_db(self.db_path)

    # --------------------------------------------------------
    # ACCOUNT
    # --------------------------------------------------------

    def register(self, fullname, password, confirm_password):
        fullname = (fullname or "").strip()
        password = password or ""
        confirm_password = confirm_password or ""

        if len(fullname) < 2:
            raise WalletError(
                "Vui lòng nhập họ và tên (ít nhất 2 ký tự)."
            )

        if len(password) < MIN_PASSWORD_LENGTH:
            raise WalletError(
                f"Mật khẩu phải có ít nhất "
                f"{MIN_PASSWORD_LENGTH} ký tự."
            )

        if password != confirm_password:
            raise WalletError(
                "Mật khẩu xác nhận không trùng khớp."
            )

        private_pem, public_pem = cu.generate_key_pair()

        stored_private = _encrypt_private_key(
            private_pem, password
        )
        stored_password = _hash_password(password)

        with db.transaction(self.db_path) as conn:
            account_number = db.generate_account_number(conn)

            conn.execute(
                """
                INSERT INTO users(
                    account_number, username, password,
                    private_key, public_key, balance, created_at
                )
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    account_number,
                    fullname,
                    stored_password,
                    stored_private,
                    public_pem,
                    _now(),
                ),
            )

        return account_number

    def login(self, account_number, password):
        account_number = (account_number or "").strip()
        password = password or ""

        if not account_number or not password:
            raise WalletError(
                "Vui lòng nhập số tài khoản và mật khẩu."
            )

        generic = WalletError(
            "Sai số tài khoản hoặc mật khẩu."
        )

        with db.transaction(self.db_path) as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE account_number = ?",
                (account_number,),
            ).fetchone()

            if user is None:
                raise generic

            ok, needs_upgrade = _verify_password(
                password, user["password"]
            )

            if not ok:
                raise generic

            private_pem = user["private_key"]

            if _is_encrypted_private_key(private_pem):
                try:
                    private_plain = _decrypt_private_key(
                        private_pem, password
                    )
                except Exception:
                    raise WalletError(
                        "Không thể giải mã khóa ký của tài khoản. "
                        "Vui lòng kiểm tra mật khẩu hoặc dữ liệu khóa."
                    )

            else:
                # Khóa PEM cũ chưa mã hóa: giữ tương thích
                # và mã hóa lại sau khi đăng nhập thành công.
                private_plain = private_pem

                conn.execute(
                    """
                    UPDATE users
                    SET private_key = ?
                    WHERE id = ?
                    """,
                    (
                        _encrypt_private_key(
                            private_plain, password
                        ),
                        user["id"],
                    ),
                )

            if needs_upgrade:
                conn.execute(
                    "UPDATE users SET password = ? WHERE id = ?",
                    (
                        _hash_password(password),
                        user["id"],
                    ),
                )

        return Session(
            user_id=user["id"],
            account_number=user["account_number"],
            username=user["username"],
            private_key_pem=private_plain,
        )

    def get_account(self, session):
        with db.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session.user_id,),
            ).fetchone()

        if row is None:
            raise WalletError("Tài khoản không tồn tại.")

        return AccountInfo(
            row["id"],
            row["account_number"],
            row["username"],
            float(row["balance"]),
        )

    def lookup_account(self, account_number):
        account_number = (account_number or "").strip()

        if not account_number:
            return None

        with db.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT username FROM users
                WHERE account_number = ?
                """,
                (account_number,),
            ).fetchone()

        return row["username"] if row else None

    # --------------------------------------------------------
    # AMOUNT VALIDATION
    # --------------------------------------------------------

    @staticmethod
    def _check_amount(amount):
        try:
            value = float(amount)
        except (TypeError, ValueError, OverflowError):
            raise WalletError("Số tiền không hợp lệ.")

        if not __import__("math").isfinite(value):
            raise WalletError("Số tiền không hợp lệ.")

        if value <= 0:
            raise WalletError("Số tiền phải lớn hơn 0.")

        if value != int(value):
            raise WalletError(
                "Số tiền phải là số nguyên (VNĐ)."
            )

        if value > MAX_AMOUNT:
            raise WalletError(
                f"Mỗi giao dịch tối đa {MAX_AMOUNT:,.0f} VNĐ."
            )

        return float(value)

    # --------------------------------------------------------
    # DEPOSIT
    # --------------------------------------------------------

    def deposit(self, session, amount):
        amount = self._check_amount(amount)

        with db.transaction(self.db_path) as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session.user_id,),
            ).fetchone()

            if user is None:
                raise WalletError("Tài khoản không tồn tại.")

            old = float(user["balance"])
            new = old + amount
            timestamp = _now()

            payload = transaction_payload(
                user["id"], user["id"], amount,
                old, new, old, new, timestamp,
            )

            tx_hash = cu.hash_transaction(payload)
            signature = cu.sign_data(
                payload, session.private_key_pem
            )

            conn.execute(
                "UPDATE users SET balance = ? WHERE id = ?",
                (new, user["id"]),
            )

            cur = conn.execute(
                """
                INSERT INTO transactions(
                    sender_id, receiver_id, amount,
                    sender_old_balance, sender_new_balance,
                    receiver_old_balance, receiver_new_balance,
                    timestamp, transaction_hash, signature, type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'deposit')
                """,
                (
                    user["id"], user["id"], amount,
                    old, new, old, new,
                    timestamp, tx_hash, signature,
                ),
            )

            tx_id = cur.lastrowid

        return self.get_transaction(session, tx_id)

    # --------------------------------------------------------
    # TRANSFER
    # --------------------------------------------------------

    def transfer(self, session, receiver_account, amount):
        amount = self._check_amount(amount)
        receiver_account = (receiver_account or "").strip()

        if not receiver_account:
            raise WalletError(
                "Vui lòng nhập số tài khoản người nhận."
            )

        with db.transaction(self.db_path) as conn:
            sender = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session.user_id,),
            ).fetchone()

            receiver = conn.execute(
                "SELECT * FROM users WHERE account_number = ?",
                (receiver_account,),
            ).fetchone()

            if sender is None:
                raise WalletError("Tài khoản không tồn tại.")

            if receiver is None:
                raise WalletError(
                    "Không tìm thấy tài khoản người nhận."
                )

            if receiver["id"] == sender["id"]:
                raise WalletError(
                    "Không thể chuyển tiền cho chính mình."
                )

            s_old = float(sender["balance"])
            r_old = float(receiver["balance"])

            if amount > s_old:
                raise WalletError(
                    "Số dư không đủ để thực hiện giao dịch."
                )

            s_new = s_old - amount
            r_new = r_old + amount
            timestamp = _now()

            payload = transaction_payload(
                sender["id"], receiver["id"], amount,
                s_old, s_new, r_old, r_new, timestamp,
            )

            tx_hash = cu.hash_transaction(payload)
            signature = cu.sign_data(
                payload, session.private_key_pem
            )

            conn.execute(
                "UPDATE users SET balance = ? WHERE id = ?",
                (s_new, sender["id"]),
            )

            conn.execute(
                "UPDATE users SET balance = ? WHERE id = ?",
                (r_new, receiver["id"]),
            )

            cur = conn.execute(
                """
                INSERT INTO transactions(
                    sender_id, receiver_id, amount,
                    sender_old_balance, sender_new_balance,
                    receiver_old_balance, receiver_new_balance,
                    timestamp, transaction_hash, signature, type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'transfer')
                """,
                (
                    sender["id"], receiver["id"], amount,
                    s_old, s_new, r_old, r_new,
                    timestamp, tx_hash, signature,
                ),
            )

            tx_id = cur.lastrowid

        return self.get_transaction(session, tx_id)

    # --------------------------------------------------------
    # TRANSACTION HISTORY
    # --------------------------------------------------------

    def list_transactions(self, session, limit=None, kind=None):
        """kind: None = tất cả, in = tiền vào, out = tiền ra."""

        sql = _TX_SELECT + """
            WHERE (t.sender_id = ? OR t.receiver_id = ?)
        """
        params = [session.user_id, session.user_id]

        if kind == "in":
            sql += " AND t.receiver_id = ?"
            params.append(session.user_id)

        elif kind == "out":
            sql += """
                AND t.type = 'transfer'
                AND t.sender_id = ?
            """
            params.append(session.user_id)

        sql += " ORDER BY t.id DESC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, int(limit)))

        with db.connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            _to_view(row, session.user_id)
            for row in rows
        ]

    def _fetch_row(self, conn, session, tx_id):
        row = conn.execute(
            _TX_SELECT + """
                WHERE t.id = ?
                AND (t.sender_id = ? OR t.receiver_id = ?)
            """,
            (tx_id, session.user_id, session.user_id),
        ).fetchone()

        if row is None:
            raise WalletError("Không tìm thấy giao dịch.")

        return row

    def get_transaction(self, session, tx_id):
        with db.connect(self.db_path) as conn:
            row = self._fetch_row(conn, session, tx_id)

        return _to_view(row, session.user_id)

    # --------------------------------------------------------
    # VERIFY SHA-256 + RSA
    # --------------------------------------------------------

    def verify_transaction(self, session, tx_id):
        with db.connect(self.db_path) as conn:
            row = self._fetch_row(conn, session, tx_id)

            sender = conn.execute(
                "SELECT public_key FROM users WHERE id = ?",
                (row["sender_id"],),
            ).fetchone()

        if sender is None:
            raise WalletError(
                "Không tìm thấy khóa công khai người gửi."
            )

        payload = transaction_payload(
            row["sender_id"],
            row["receiver_id"],
            row["amount"],
            row["sender_old_balance"],
            row["sender_new_balance"],
            row["receiver_old_balance"],
            row["receiver_new_balance"],
            row["timestamp"],
        )

        hash_ok = (
            cu.hash_transaction(payload)
            == row["transaction_hash"]
        )

        signature_ok = cu.verify_signature(
            payload,
            row["signature"],
            sender["public_key"],
        )

        valid = hash_ok and signature_ok

        if valid:
            message = (
                "Hợp lệ: mã băm SHA-256 khớp "
                "và chữ ký RSA đúng."
            )
        elif not hash_ok and not signature_ok:
            message = (
                "Không hợp lệ: dữ liệu giao dịch đã bị thay đổi "
                "(hash và chữ ký đều sai)."
            )
        elif not hash_ok:
            message = (
                "Không hợp lệ: mã băm SHA-256 "
                "không khớp với dữ liệu hiện tại."
            )
        else:
            message = (
                "Không hợp lệ: chữ ký RSA không khớp "
                "với khóa công khai của người gửi."
            )

        return VerifyResult(
            valid, hash_ok, signature_ok, message
        )

    # --------------------------------------------------------
    # DEMO TAMPERING
    # --------------------------------------------------------

    def tamper_transaction(self, session, tx_id):
        """Demo chỉnh sửa số tiền giao dịch trong database."""

        with db.transaction(self.db_path) as conn:
            row = self._fetch_row(conn, session, tx_id)

            conn.execute(
                """
                INSERT OR IGNORE INTO tamper_backup(
                    tx_id, original_amount
                )
                VALUES (?, ?)
                """,
                (tx_id, row["amount"]),
            )

            conn.execute(
                """
                UPDATE transactions
                SET amount = amount + ?
                WHERE id = ?
                """,
                (TAMPER_DELTA, tx_id),
            )

    def restore_transaction(self, session, tx_id):
        """Khôi phục số tiền gốc đã lưu trước khi demo chỉnh sửa."""

        with db.transaction(self.db_path) as conn:
            self._fetch_row(conn, session, tx_id)

            backup = conn.execute(
                """
                SELECT original_amount
                FROM tamper_backup
                WHERE tx_id = ?
                """,
                (tx_id,),
            ).fetchone()

            if backup is None:
                raise WalletError(
                    "Giao dịch này chưa bị sửa."
                )

            conn.execute(
                """
                UPDATE transactions
                SET amount = ?
                WHERE id = ?
                """,
                (backup["original_amount"], tx_id),
            )

            conn.execute(
                "DELETE FROM tamper_backup WHERE tx_id = ?",
                (tx_id,),
            )