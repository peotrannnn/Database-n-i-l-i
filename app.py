import csv
import io
import os
import re
import sqlite3
import unicodedata
from datetime import datetime
from functools import wraps

from flask import Flask, Response, flash, g, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lai.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def normalize_text(value):
    value = unicodedata.normalize("NFC", value or "")
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value


def count_words(value):
    text = normalize_text(value)
    if not text:
        return 0
    return len([part for part in text.split(" ") if part])


def make_pair_key(original_text, flipped_text):
    a = normalize_text(original_text)
    b = normalize_text(flipped_text)
    return "|".join(sorted([a, b]))


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Đăng nhập để tiếp tục.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Đăng nhập để tiếp tục.", "error")
            return redirect(url_for("login", next=request.path))
        if user["role"] != "admin":
            flash("Chỉ admin mới vào được.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


def table_columns(db, table_name):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}


def add_column_if_missing(db, table_name, column_name, column_sql):
    if column_name not in table_columns(db, table_name):
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS phrase_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT NOT NULL,
            flipped_text TEXT NOT NULL,
            pair_key TEXT NOT NULL UNIQUE,
            is_dirty INTEGER NOT NULL DEFAULT 0,
            is_intentional_typo INTEGER NOT NULL DEFAULT 0,
            is_sensitive INTEGER NOT NULL DEFAULT 0,
            is_forced INTEGER NOT NULL DEFAULT 0,
            is_not_meaningful INTEGER NOT NULL DEFAULT 0,
            fun_score INTEGER NOT NULL DEFAULT 5,
            status TEXT NOT NULL DEFAULT 'active',
            created_by INTEGER,
            approved_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(created_by) REFERENCES users(id),
            FOREIGN KEY(approved_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            original_text TEXT NOT NULL,
            flipped_text TEXT NOT NULL,
            pair_key TEXT NOT NULL,
            is_dirty INTEGER NOT NULL DEFAULT 0,
            is_intentional_typo INTEGER NOT NULL DEFAULT 0,
            is_sensitive INTEGER NOT NULL DEFAULT 0,
            is_forced INTEGER NOT NULL DEFAULT 0,
            is_not_meaningful INTEGER NOT NULL DEFAULT 0,
            fun_score INTEGER NOT NULL DEFAULT 5,
            status TEXT NOT NULL DEFAULT 'pending',
            reject_reason TEXT,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(reviewed_by) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions(status);
        CREATE INDEX IF NOT EXISTS idx_suggestions_user_id ON suggestions(user_id);
        CREATE INDEX IF NOT EXISTS idx_phrase_pairs_pair_key ON phrase_pairs(pair_key);

        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_password_resets_user_id ON password_resets(user_id);

        CREATE TABLE IF NOT EXISTS password_change_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            code_hash TEXT NOT NULL,
            new_password_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_password_change_requests_user_id ON password_change_requests(user_id);
        """
    )

    for table_name in ["phrase_pairs", "suggestions"]:
        add_column_if_missing(db, table_name, "is_sensitive", "is_sensitive INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(db, table_name, "is_forced", "is_forced INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(db, table_name, "is_not_meaningful", "is_not_meaningful INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(db, table_name, "fun_score", "fun_score INTEGER NOT NULL DEFAULT 5")

    admin_email = normalize_text(os.environ.get("ADMIN_EMAIL"))
    admin_username = normalize_text(os.environ.get("ADMIN_USERNAME"))
    admin_password = os.environ.get("ADMIN_PASSWORD") or ""

    if admin_email and admin_username and admin_password:
        admin = db.execute(
            "SELECT * FROM users WHERE email = ? OR lower(name) = lower(?) LIMIT 1",
            (admin_email, admin_username),
        ).fetchone()

        if admin:
            db.execute(
                """
                UPDATE users
                SET name = ?, email = ?, password_hash = ?, role = 'admin', status = 'active', updated_at = ?
                WHERE id = ?
                """,
                (admin_username, admin_email, generate_password_hash(admin_password), now_iso(), admin["id"]),
            )
            admin_id = admin["id"]
        else:
            cursor = db.execute(
                """
                INSERT INTO users (name, email, password_hash, role, status, created_at, updated_at)
                VALUES (?, ?, ?, 'admin', 'active', ?, ?)
                """,
                (admin_username, admin_email, generate_password_hash(admin_password), now_iso(), now_iso()),
            )
            admin_id = cursor.lastrowid

        db.execute(
            """
            UPDATE users
            SET status = 'blocked', updated_at = ?
            WHERE email = 'admin@lai.local' AND id != ?
            """,
            (now_iso(), admin_id),
        )
    else:
        print(
            "WARNING: ADMIN_EMAIL, ADMIN_USERNAME, and ADMIN_PASSWORD are not fully configured. "
            "No default admin account will be created."
        )

    db.commit()
    db.close()


def checkbox_value(name):
    return 1 if request.form.get(name) else 0


def score_value(name="fun_score", default=5):
    try:
        value = int(request.form.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(0, min(10, value))


def find_user_by_identifier(identifier):
    identifier = normalize_text(identifier)
    if not identifier:
        return None
    return get_db().execute(
        "SELECT * FROM users WHERE email = ? OR lower(name) = lower(?)",
        (identifier, identifier),
    ).fetchone()



def validate_pair(original_raw, flipped_raw):
    original_text = normalize_text(original_raw)
    flipped_text = normalize_text(flipped_raw)

    if not original_text or not flipped_text:
        return None, None, None, "Hai cụm không được để trống."

    original_count = count_words(original_text)
    flipped_count = count_words(flipped_text)

    if original_count < 2 or original_count > 3:
        return None, None, None, "Cụm ban đầu cần có từ 2 đến 3 từ."

    if flipped_count < 2 or flipped_count > 3:
        return None, None, None, "Cụm sau khi lái cần có từ 2 đến 3 từ."

    if original_text == flipped_text:
        return None, None, None, "Hai cụm này giống nhau rồi."

    pair_key = make_pair_key(original_text, flipped_text)
    return original_text, flipped_text, pair_key, None


@app.route("/")
def index():
    return render_template("index.html")




@app.route("/suggest", methods=["POST"])
@login_required
def suggest():
    user = current_user()
    if user["status"] == "blocked":
        flash("Tài khoản đang bị chặn đề xuất.", "error")
        return redirect(url_for("index"))

    original_text, flipped_text, pair_key, error = validate_pair(
        request.form.get("original_text"),
        request.form.get("flipped_text"),
    )
    if error:
        flash(error, "error")
        return redirect(url_for("index", open_modal="1"))

    db = get_db()
    existed_pair = db.execute(
        "SELECT id FROM phrase_pairs WHERE pair_key = ? AND status != 'deleted'",
        (pair_key,),
    ).fetchone()
    if existed_pair:
        flash("Cụm này đã có trong database.", "error")
        return redirect(url_for("index", open_modal="1"))

    existed_pending = db.execute(
        "SELECT id FROM suggestions WHERE pair_key = ? AND status = 'pending'",
        (pair_key,),
    ).fetchone()
    if existed_pending:
        flash("Cụm này đang chờ admin duyệt rồi.", "error")
        return redirect(url_for("index", open_modal="1"))

    db.execute(
        """
        INSERT INTO suggestions
        (user_id, original_text, flipped_text, pair_key, is_dirty, is_intentional_typo,
         is_sensitive, is_forced, is_not_meaningful, fun_score, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            user["id"],
            original_text,
            flipped_text,
            pair_key,
            checkbox_value("is_intentional_typo"),
            checkbox_value("is_sensitive"),
            checkbox_value("is_forced"),
            checkbox_value("is_not_meaningful"),
            score_value(),
            now_iso(),
            now_iso(),
        ),
    )
    db.commit()
    flash("Đã gửi đề xuất. Admin đang soi.", "success")
    return redirect(url_for("account"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = normalize_text(request.form.get("name"))
        email = normalize_text(request.form.get("email"))
        password = request.form.get("password") or ""

        if not name or not email or not password:
            flash("Username, email và mật khẩu không được trống.", "error")
            return render_template("register.html")

        if len(name) < 3:
            flash("Username cần ít nhất 3 ký tự.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Mật khẩu cần ít nhất 6 ký tự.", "error")
            return render_template("register.html")

        db = get_db()
        existed_email = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existed_email:
            flash("Email này đã có tài khoản.", "error")
            return render_template("register.html")

        existed_name = db.execute("SELECT id FROM users WHERE lower(name) = lower(?)", (name,)).fetchone()
        if existed_name:
            flash("Username này đã có người dùng rồi.", "error")
            return render_template("register.html")

        db.execute(
            """
            INSERT INTO users (name, email, password_hash, role, status, created_at, updated_at)
            VALUES (?, ?, ?, 'user', 'active', ?, ?)
            """,
            (name, email, generate_password_hash(password), now_iso(), now_iso()),
        )
        db.commit()
        flash("Đăng ký xong. Đăng nhập nha.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = normalize_text(request.form.get("identifier") or request.form.get("email"))
        password = request.form.get("password") or ""
        user = find_user_by_identifier(identifier)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Username/email hoặc mật khẩu sai.", "error")
            return render_template("login.html")

        if user["status"] == "blocked":
            flash("Tài khoản đang bị chặn.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        flash("Đăng nhập rồi đó.", "success")
        return redirect(request.args.get("next") or url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất.", "success")
    return redirect(url_for("index"))



@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    user = current_user()
    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "profile":
            name = normalize_text(request.form.get("name")) or user["name"]
            if len(name) < 3:
                flash("Username cần ít nhất 3 ký tự.", "error")
                return redirect(url_for("account"))
            existed_name = db.execute(
                "SELECT id FROM users WHERE lower(name) = lower(?) AND id != ?",
                (name, user["id"]),
            ).fetchone()
            if existed_name:
                flash("Username này đã có người dùng rồi.", "error")
                return redirect(url_for("account"))
            db.execute("UPDATE users SET name = ?, updated_at = ? WHERE id = ?", (name, now_iso(), user["id"]))
            db.commit()
            flash("Đã lưu tài khoản.", "success")
            return redirect(url_for("account"))

        if action == "password":
            current_password = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if not check_password_hash(user["password_hash"], current_password):
                flash("Mật khẩu hiện tại sai.", "error")
                return redirect(url_for("account"))

            if len(new_password) < 6:
                flash("Mật khẩu mới cần ít nhất 6 ký tự.", "error")
                return redirect(url_for("account"))

            if new_password != confirm_password:
                flash("Mật khẩu nhập lại không khớp.", "error")
                return redirect(url_for("account"))

            db.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (generate_password_hash(new_password), now_iso(), user["id"]),
            )
            db.commit()
            flash("Đổi mật khẩu xong.", "success")
            return redirect(url_for("account"))

    suggestions = db.execute(
        """
        SELECT * FROM suggestions
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    return render_template("account.html", suggestions=suggestions)



@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    page = max(int(request.args.get("page", 1)), 1)
    limit = int(request.args.get("limit", 20))
    if limit not in [10, 20, 50, 100]:
        limit = 20
    offset = (page - 1) * limit
    search = normalize_text(request.args.get("search"))
    filter_label = request.args.get("label", "all")

    where = ["p.status = 'active'"]
    params = []

    if search:
        where.append("(p.original_text LIKE ? OR p.flipped_text LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    label_map = {
        "sensitive": "p.is_sensitive = 1",
        "typo": "p.is_intentional_typo = 1",
        "forced": "p.is_forced = 1",
        "not_meaningful": "p.is_not_meaningful = 1",
        "none": "p.is_sensitive = 0 AND p.is_intentional_typo = 0 AND p.is_forced = 0 AND p.is_not_meaningful = 0",
    }
    if filter_label in label_map:
        where.append(label_map[filter_label])

    where_sql = " AND ".join(where)
    total = db.execute(f"SELECT COUNT(*) AS total FROM phrase_pairs p WHERE {where_sql}", params).fetchone()["total"]
    total_pages = max((total + limit - 1) // limit, 1)

    pairs = db.execute(
        f"""
        SELECT p.*, u.email AS created_email, a.email AS approved_email
        FROM phrase_pairs p
        LEFT JOIN users u ON p.created_by = u.id
        LEFT JOIN users a ON p.approved_by = a.id
        WHERE {where_sql}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    suggestions = db.execute(
        """
        SELECT s.*, u.email AS user_email, u.status AS user_status
        FROM suggestions s
        JOIN users u ON s.user_id = u.id
        WHERE s.status = 'pending'
        ORDER BY s.created_at ASC
        """
    ).fetchall()

    users = db.execute(
        """
        SELECT u.*,
        (SELECT COUNT(*) FROM suggestions s WHERE s.user_id = u.id) AS suggestion_count
        FROM users u
        ORDER BY u.created_at DESC
        """
    ).fetchall()

    return render_template(
        "admin.html",
        pairs=pairs,
        suggestions=suggestions,
        users=users,
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        search=search,
        filter_label=filter_label,
    )


@app.route("/admin/suggestions/<int:suggestion_id>/approve", methods=["POST"])
@admin_required
def approve_suggestion(suggestion_id):
    admin_user = current_user()
    db = get_db()
    suggestion = db.execute("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,)).fetchone()

    if not suggestion:
        flash("Không tìm thấy đề xuất.", "error")
        return redirect(url_for("admin"))

    if suggestion["status"] != "pending":
        flash("Đề xuất này đã được xử lý.", "error")
        return redirect(url_for("admin"))

    original_text, flipped_text, pair_key, error = validate_pair(
        request.form.get("original_text") or suggestion["original_text"],
        request.form.get("flipped_text") or suggestion["flipped_text"],
    )
    if error:
        flash(error, "error")
        return redirect(url_for("admin"))

    is_intentional_typo = checkbox_value("is_intentional_typo")
    is_sensitive = checkbox_value("is_sensitive")
    is_forced = checkbox_value("is_forced")
    is_not_meaningful = checkbox_value("is_not_meaningful")
    fun_score = score_value()

    existed_pair = db.execute(
        "SELECT id FROM phrase_pairs WHERE pair_key = ? AND status != 'deleted'",
        (pair_key,),
    ).fetchone()

    if existed_pair:
        db.execute(
            """
            UPDATE suggestions
            SET original_text = ?, flipped_text = ?, pair_key = ?, is_dirty = 0, is_intentional_typo = ?,
                is_sensitive = ?, is_forced = ?, is_not_meaningful = ?, fun_score = ?,
                status = 'rejected', reject_reason = ?, reviewed_by = ?, reviewed_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                original_text,
                flipped_text,
                pair_key,
                is_intentional_typo,
                is_sensitive,
                is_forced,
                is_not_meaningful,
                fun_score,
                "Cụm này đã có trong database.",
                admin_user["id"],
                now_iso(),
                now_iso(),
                suggestion_id,
            ),
        )
        db.commit()
        flash("Cụm này đã có trong database nên đã bỏ.", "error")
        return redirect(url_for("admin"))

    db.execute(
        """
        INSERT INTO phrase_pairs
        (original_text, flipped_text, pair_key, is_dirty, is_intentional_typo,
         is_sensitive, is_forced, is_not_meaningful, fun_score, status, created_by, approved_by, created_at, updated_at)
        VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
        """,
        (
            original_text,
            flipped_text,
            pair_key,
            is_intentional_typo,
            is_sensitive,
            is_forced,
            is_not_meaningful,
            fun_score,
            suggestion["user_id"],
            admin_user["id"],
            now_iso(),
            now_iso(),
        ),
    )
    db.execute(
        """
        UPDATE suggestions
        SET original_text = ?, flipped_text = ?, pair_key = ?, is_dirty = 0, is_intentional_typo = ?,
            is_sensitive = ?, is_forced = ?, is_not_meaningful = ?, fun_score = ?,
            status = 'approved', reviewed_by = ?, reviewed_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            original_text,
            flipped_text,
            pair_key,
            is_intentional_typo,
            is_sensitive,
            is_forced,
            is_not_meaningful,
            fun_score,
            admin_user["id"],
            now_iso(),
            now_iso(),
            suggestion_id,
        ),
    )
    db.commit()
    flash("Đã duyệt.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/suggestions/<int:suggestion_id>/reject", methods=["POST"])
@admin_required
def reject_suggestion(suggestion_id):
    admin_user = current_user()
    reason = request.form.get("reason") or "Admin đã bỏ đề xuất."
    db = get_db()
    db.execute(
        """
        UPDATE suggestions
        SET status = 'rejected', reject_reason = ?, reviewed_by = ?, reviewed_at = ?, updated_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (reason, admin_user["id"], now_iso(), now_iso(), suggestion_id),
    )
    db.commit()
    flash("Đã bỏ đề xuất.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/toggle-block", methods=["POST"])
@admin_required
def toggle_block_user(user_id):
    user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash("Không tìm thấy user.", "error")
        return redirect(url_for("admin"))
    if user["role"] == "admin":
        flash("Không chặn admin ở đây.", "error")
        return redirect(url_for("admin"))
    new_status = "active" if user["status"] == "blocked" else "blocked"
    get_db().execute("UPDATE users SET status = ?, updated_at = ? WHERE id = ?", (new_status, now_iso(), user_id))
    get_db().commit()
    flash("Đã cập nhật user.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_user_password(user_id):
    db = get_db()
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        flash("Không tìm thấy user.", "error")
        return redirect(url_for("admin"))
    if target["role"] == "admin":
        flash("Không đặt lại mật khẩu admin ở đây.", "error")
        return redirect(url_for("admin"))

    new_password = request.form.get("new_password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if len(new_password) < 6:
        flash("Mật khẩu mới cần ít nhất 6 ký tự.", "error")
        return redirect(url_for("admin"))
    if new_password != confirm_password:
        flash("Mật khẩu nhập lại không khớp.", "error")
        return redirect(url_for("admin"))

    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (generate_password_hash(new_password), now_iso(), user_id),
    )
    db.commit()
    flash(f"Đã đặt lại mật khẩu cho {target['email']}.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    db = get_db()
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        flash("Không tìm thấy user.", "error")
        return redirect(url_for("admin"))
    if target["role"] == "admin":
        flash("Không xóa admin ở đây.", "error")
        return redirect(url_for("admin"))

    # Giữ database cụm từ đã duyệt, chỉ gỡ liên kết tài khoản đã bị xóa.
    db.execute("UPDATE phrase_pairs SET created_by = NULL, updated_at = ? WHERE created_by = ?", (now_iso(), user_id))
    db.execute("UPDATE suggestions SET reviewed_by = NULL, updated_at = ? WHERE reviewed_by = ?", (now_iso(), user_id))
    db.execute("DELETE FROM suggestions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("Đã xóa tài khoản user. User có thể đăng ký lại từ đầu.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/pairs/<int:pair_id>/remove", methods=["POST"])
@admin_required
def remove_pair(pair_id):
    admin_user = current_user()
    db = get_db()
    pair = db.execute("SELECT * FROM phrase_pairs WHERE id = ?", (pair_id,)).fetchone()
    if not pair:
        flash("Không tìm thấy dòng này.", "error")
        return redirect(url_for("admin"))

    existing_pending = db.execute(
        "SELECT id FROM suggestions WHERE pair_key = ? AND status = 'pending'",
        (pair["pair_key"],),
    ).fetchone()

    if not existing_pending:
        owner_id = pair["created_by"] or admin_user["id"]
        db.execute(
            """
            INSERT INTO suggestions
            (user_id, original_text, flipped_text, pair_key, is_dirty, is_intentional_typo,
             is_sensitive, is_forced, is_not_meaningful, fun_score, status, reject_reason,
             reviewed_by, reviewed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, 'pending', NULL, NULL, NULL, ?, ?)
            """,
            (
                owner_id,
                pair["original_text"],
                pair["flipped_text"],
                pair["pair_key"],
                pair["is_intentional_typo"],
                pair["is_sensitive"],
                pair["is_forced"],
                pair["is_not_meaningful"],
                pair["fun_score"],
                now_iso(),
                now_iso(),
            ),
        )

    db.execute("DELETE FROM phrase_pairs WHERE id = ?", (pair_id,))
    db.commit()
    flash("Đã gỡ khỏi database và đưa lại vào mục duyệt.", "success")
    return redirect(url_for("admin"))


def export_rows():
    return get_db().execute(
        """
        SELECT p.id, p.original_text, p.flipped_text, p.is_sensitive, p.is_intentional_typo,
               p.is_forced, p.is_not_meaningful, p.fun_score,
               u.email AS created_by, a.email AS approved_by, p.created_at
        FROM phrase_pairs p
        LEFT JOIN users u ON p.created_by = u.id
        LEFT JOIN users a ON p.approved_by = a.id
        WHERE p.status = 'active'
        ORDER BY p.created_at DESC
        """
    ).fetchall()


@app.route("/admin/export/csv")
@admin_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "original_text",
        "flipped_text",
        "is_sensitive",
        "is_intentional_typo",
        "is_forced",
        "is_not_meaningful",
        "fun_score",
        "created_by",
        "approved_by",
        "created_at",
    ])
    for row in export_rows():
        writer.writerow([
            row["id"],
            row["original_text"],
            row["flipped_text"],
            bool(row["is_sensitive"]),
            bool(row["is_intentional_typo"]),
            bool(row["is_forced"]),
            bool(row["is_not_meaningful"]),
            row["fun_score"],
            row["created_by"] or "",
            row["approved_by"] or "",
            row["created_at"],
        ])
    data = output.getvalue().encode("utf-8-sig")
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=lai_database.csv"},
    )


@app.route("/admin/export/excel")
@admin_required
def export_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Lai Database"
    ws.append([
        "id",
        "original_text",
        "flipped_text",
        "is_sensitive",
        "is_intentional_typo",
        "is_forced",
        "is_not_meaningful",
        "fun_score",
        "created_by",
        "approved_by",
        "created_at",
    ])
    for row in export_rows():
        ws.append([
            row["id"],
            row["original_text"],
            row["flipped_text"],
            bool(row["is_sensitive"]),
            bool(row["is_intentional_typo"]),
            bool(row["is_forced"]),
            bool(row["is_not_meaningful"]),
            row["fun_score"],
            row["created_by"] or "",
            row["approved_by"] or "",
            row["created_at"],
        ])
    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 40)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="lai_database.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# Ensure database tables/admin account are created when the app is imported by Gunicorn/Render.
init_db()


if __name__ == "__main__":
    app.run(debug=True)
