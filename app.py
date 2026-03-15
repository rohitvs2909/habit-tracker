from calendar import month_name, monthrange
from datetime import datetime
from functools import wraps
import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-in-production")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "habit_tracker")

APP_USER_1 = os.getenv("APP_USER_1", "rohit")
APP_PASS_1 = os.getenv("APP_PASS_1", "pass123")
APP_USER_2 = os.getenv("APP_USER_2", "partner")
APP_PASS_2 = os.getenv("APP_PASS_2", "pass123")

DAILY_DEFAULTS = [
    "No more than 3 coffees",
    "Bed by 10pm",
    "8 Hours Sleep",
    "Go to Gym",
    "Wake up at 7am",
    "Read before Bed",
    "Make Bed",
    "Eat Healthy Dinner",
    "No Sugar",
    "Meditate for 30 Minutes",
]

WEEKLY_DEFAULTS = ["Clean House", "Laundry", "Visit Family"]
MONTHLY_DEFAULTS = ["Save $50", "Pay Credit Card", "Pay Bills"]


def get_server_db():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def get_db():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )


def fetch_all_dict(cursor):
    rows = cursor.fetchall()
    columns = cursor.column_names
    return [dict(zip(columns, row)) for row in rows]


def fetch_one_value(cursor):
    row = cursor.fetchone()
    return row[0] if row else 0


def get_current_user_id():
    return session.get("user_id")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if get_current_user_id():
            return fn(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required"}), 401

        return redirect(url_for("login"))

    return wrapper


def get_user_by_username(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
    }


def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
    }


def create_user_if_missing(conn, username, password):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, generate_password_hash(password, method="pbkdf2:sha256")),
        )
    cur.close()


def create_user(conn, username, password):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (username, generate_password_hash(password, method="pbkdf2:sha256")),
    )
    user_id = cur.lastrowid
    cur.close()
    return user_id


def seed_if_empty(conn, table, values, owner_user_id):
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE owner_user_id = %s", (owner_user_id,))
    if fetch_one_value(cur):
        cur.close()
        return
    cur.close()

    cur = conn.cursor()
    cur.executemany(
        f"INSERT INTO {table} (name, position, owner_user_id) VALUES (%s, %s, %s)",
        [(name, idx + 1, owner_user_id) for idx, name in enumerate(values)],
    )
    cur.close()


def ensure_owned_habit(cursor, habit_type, habit_id, user_id):
    table = {
        "daily": "daily_habits",
        "weekly": "weekly_habits",
        "monthly": "monthly_habits",
    }.get(habit_type)
    if not table:
        return False

    cursor.execute(
        f"SELECT id FROM {table} WHERE id = %s AND owner_user_id = %s",
        (habit_id, user_id),
    )
    return cursor.fetchone() is not None


def init_db():
    bootstrap_conn = get_server_db()
    bootstrap_cur = bootstrap_conn.cursor()
    bootstrap_cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
    bootstrap_conn.commit()
    bootstrap_cur.close()
    bootstrap_conn.close()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_habits (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            position INT NOT NULL,
            owner_user_id INT NOT NULL,
            INDEX idx_daily_owner (owner_user_id),
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_habits (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            position INT NOT NULL,
            owner_user_id INT NOT NULL,
            INDEX idx_weekly_owner (owner_user_id),
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_habits (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            position INT NOT NULL,
            owner_user_id INT NOT NULL,
            INDEX idx_monthly_owner (owner_user_id),
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_completions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            habit_id INT NOT NULL,
            year INT NOT NULL,
            month INT NOT NULL,
            day INT NOT NULL,
            completed TINYINT(1) NOT NULL DEFAULT 0,
            UNIQUE(habit_id, year, month, day),
            FOREIGN KEY (habit_id) REFERENCES daily_habits(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_completions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            habit_id INT NOT NULL,
            year INT NOT NULL,
            month INT NOT NULL,
            week INT NOT NULL,
            completed TINYINT(1) NOT NULL DEFAULT 0,
            UNIQUE(habit_id, year, month, week),
            FOREIGN KEY (habit_id) REFERENCES weekly_habits(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_completions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            habit_id INT NOT NULL,
            year INT NOT NULL,
            month INT NOT NULL,
            completed TINYINT(1) NOT NULL DEFAULT 0,
            UNIQUE(habit_id, year, month),
            FOREIGN KEY (habit_id) REFERENCES monthly_habits(id) ON DELETE CASCADE
        )
        """
    )

    # Supports migration from older schema without ownership columns.
    tables = ["daily_habits", "weekly_habits", "monthly_habits"]
    for table in tables:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s AND column_name = 'owner_user_id'
            """,
            (DB_NAME, table),
        )
        has_owner_col = fetch_one_value(cur)
        if not has_owner_col:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN owner_user_id INT NOT NULL DEFAULT 1")
    cur.close()

    create_user_if_missing(conn, APP_USER_1, APP_PASS_1)
    create_user_if_missing(conn, APP_USER_2, APP_PASS_2)
    conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (APP_USER_1,))
    user_1_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = %s", (APP_USER_2,))
    user_2_id = cur.fetchone()[0]
    cur.close()

    seed_if_empty(conn, "daily_habits", DAILY_DEFAULTS, user_1_id)
    seed_if_empty(conn, "daily_habits", DAILY_DEFAULTS, user_2_id)
    seed_if_empty(conn, "weekly_habits", WEEKLY_DEFAULTS, user_1_id)
    seed_if_empty(conn, "weekly_habits", WEEKLY_DEFAULTS, user_2_id)
    seed_if_empty(conn, "monthly_habits", MONTHLY_DEFAULTS, user_1_id)
    seed_if_empty(conn, "monthly_habits", MONTHLY_DEFAULTS, user_2_id)

    conn.commit()
    conn.close()


def fetch_stats(conn, year, month, days_in_month, user_id):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_habits WHERE owner_user_id = %s", (user_id,))
    daily_count = fetch_one_value(cur)
    total = daily_count * days_in_month

    cur.execute(
        """
        SELECT COUNT(*)
        FROM daily_completions dc
        JOIN daily_habits dh ON dh.id = dc.habit_id
        WHERE dc.year = %s AND dc.month = %s AND dc.completed = 1 AND dh.owner_user_id = %s
        """,
        (year, month, user_id),
    )
    complete = fetch_one_value(cur)
    cur.close()

    incomplete = max(total - complete, 0)
    percentage = round((complete / total) * 100, 1) if total else 0.0
    return {
        "complete": complete,
        "incomplete": incomplete,
        "percentage": percentage,
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if get_current_user_id():
        return redirect(url_for("index"))

    if request.method in ("GET", "HEAD"):
        return render_template("login.html")

    payload = request.form if request.form else (request.get_json(silent=True) or {})
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid username or password"), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if get_current_user_id():
        return redirect(url_for("index"))

    if request.method in ("GET", "HEAD"):
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    confirm_password = (request.form.get("confirm_password") or "").strip()

    if len(username) < 3:
        return render_template("register.html", error="Username must be at least 3 characters."), 400

    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters."), 400

    if password != confirm_password:
        return render_template("register.html", error="Password and confirm password do not match."), 400

    if get_user_by_username(username):
        return render_template("register.html", error="Username already exists."), 400

    conn = get_db()
    user_id = create_user(conn, username, password)
    conn.commit()

    seed_if_empty(conn, "daily_habits", DAILY_DEFAULTS, user_id)
    seed_if_empty(conn, "weekly_habits", WEEKLY_DEFAULTS, user_id)
    seed_if_empty(conn, "monthly_habits", MONTHLY_DEFAULTS, user_id)
    conn.commit()
    conn.close()

    session["user_id"] = user_id
    session["username"] = username
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "GET":
        return render_template("change_password.html", username=session.get("username"))

    current_password = (request.form.get("current_password") or "").strip()
    new_password = (request.form.get("new_password") or "").strip()
    confirm_password = (request.form.get("confirm_password") or "").strip()

    if not current_password or not new_password or not confirm_password:
        return render_template(
            "change_password.html",
            username=session.get("username"),
            error="Please fill all password fields.",
        ), 400

    user = get_user_by_id(get_current_user_id())
    if not user or not check_password_hash(user["password_hash"], current_password):
        return render_template(
            "change_password.html",
            username=session.get("username"),
            error="Current password is incorrect.",
        ), 400

    if len(new_password) < 6:
        return render_template(
            "change_password.html",
            username=session.get("username"),
            error="New password must be at least 6 characters.",
        ), 400

    if new_password != confirm_password:
        return render_template(
            "change_password.html",
            username=session.get("username"),
            error="New password and confirm password do not match.",
        ), 400

    if check_password_hash(user["password_hash"], new_password):
        return render_template(
            "change_password.html",
            username=session.get("username"),
            error="New password must be different from current password.",
        ), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (generate_password_hash(new_password, method="pbkdf2:sha256"), user["id"]),
    )
    conn.commit()
    cur.close()
    conn.close()

    return render_template(
        "change_password.html",
        username=session.get("username"),
        success="Password updated successfully.",
    )


@app.route("/")
@login_required
def index():
    now = datetime.now()
    year = now.year
    month = now.month
    days_in_month = monthrange(year, month)[1]
    user_id = get_current_user_id()

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name FROM daily_habits WHERE owner_user_id = %s ORDER BY position, id",
        (user_id,),
    )
    daily_habits = fetch_all_dict(cur)

    cur.execute(
        "SELECT id, name FROM weekly_habits WHERE owner_user_id = %s ORDER BY position, id",
        (user_id,),
    )
    weekly_habits = fetch_all_dict(cur)

    cur.execute(
        "SELECT id, name FROM monthly_habits WHERE owner_user_id = %s ORDER BY position, id",
        (user_id,),
    )
    monthly_habits = fetch_all_dict(cur)

    cur.execute(
        """
        SELECT dc.habit_id, dc.day, dc.completed
        FROM daily_completions dc
        JOIN daily_habits dh ON dh.id = dc.habit_id
        WHERE dc.year = %s AND dc.month = %s AND dh.owner_user_id = %s
        """,
        (year, month, user_id),
    )
    daily_rows = fetch_all_dict(cur)

    cur.execute(
        """
        SELECT wc.habit_id, wc.week, wc.completed
        FROM weekly_completions wc
        JOIN weekly_habits wh ON wh.id = wc.habit_id
        WHERE wc.year = %s AND wc.month = %s AND wh.owner_user_id = %s
        """,
        (year, month, user_id),
    )
    weekly_rows = fetch_all_dict(cur)

    cur.execute(
        """
        SELECT mc.habit_id, mc.completed
        FROM monthly_completions mc
        JOIN monthly_habits mh ON mh.id = mc.habit_id
        WHERE mc.year = %s AND mc.month = %s AND mh.owner_user_id = %s
        """,
        (year, month, user_id),
    )
    monthly_rows = fetch_all_dict(cur)
    cur.close()

    daily_status = {(r["habit_id"], r["day"]): r["completed"] for r in daily_rows}
    weekly_status = {(r["habit_id"], r["week"]): r["completed"] for r in weekly_rows}
    monthly_status = {r["habit_id"]: r["completed"] for r in monthly_rows}
    stats = fetch_stats(conn, year, month, days_in_month, user_id)
    conn.close()

    return render_template(
        "index.html",
        daily_habits=daily_habits,
        weekly_habits=weekly_habits,
        monthly_habits=monthly_habits,
        daily_status=daily_status,
        weekly_status=weekly_status,
        monthly_status=monthly_status,
        month_name=month_name[month],
        month=month,
        year=year,
        days_in_month=days_in_month,
        stats=stats,
        username=session.get("username"),
    )


@app.route("/api/habits", methods=["POST"])
@login_required
def add_habit():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    category = (payload.get("category") or "daily").strip().lower()

    if not name:
        return jsonify({"error": "Habit name is required"}), 400

    table_by_category = {
        "daily": "daily_habits",
        "weekly": "weekly_habits",
        "monthly": "monthly_habits",
    }
    table = table_by_category.get(category)
    if not table:
        return jsonify({"error": "Invalid habit category"}), 400

    user_id = get_current_user_id()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        f"SELECT COALESCE(MAX(position), 0) + 1 FROM {table} WHERE owner_user_id = %s",
        (user_id,),
    )
    next_position = fetch_one_value(cur)
    cur.execute(
        f"INSERT INTO {table} (name, position, owner_user_id) VALUES (%s, %s, %s)",
        (name, next_position, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Habit added"}), 201


@app.route("/api/habits/<category>/<int:habit_id>", methods=["PUT"])
@login_required
def edit_habit(category, habit_id):
    payload = request.get_json(silent=True) or {}
    new_name = (payload.get("name") or "").strip()
    category = category.strip().lower()

    if not new_name:
        return jsonify({"error": "Habit name is required"}), 400

    table_by_category = {
        "daily": "daily_habits",
        "weekly": "weekly_habits",
        "monthly": "monthly_habits",
    }
    table = table_by_category.get(category)
    if not table:
        return jsonify({"error": "Invalid habit category"}), 400

    user_id = get_current_user_id()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE {table} SET name = %s WHERE id = %s AND owner_user_id = %s",
        (new_name, habit_id, user_id),
    )
    conn.commit()
    changed = cursor.rowcount
    cursor.close()
    conn.close()

    if changed == 0:
        return jsonify({"error": "Habit not found"}), 404

    return jsonify({"message": "Habit updated"})


@app.route("/api/habits/<category>/<int:habit_id>", methods=["DELETE"])
@login_required
def delete_habit(category, habit_id):
    category = category.strip().lower()

    table_by_category = {
        "daily": "daily_habits",
        "weekly": "weekly_habits",
        "monthly": "monthly_habits",
    }
    table = table_by_category.get(category)
    if not table:
        return jsonify({"error": "Invalid habit category"}), 400

    user_id = get_current_user_id()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table} WHERE id = %s AND owner_user_id = %s", (habit_id, user_id))
    conn.commit()
    changed = cursor.rowcount
    cursor.close()
    conn.close()

    if changed == 0:
        return jsonify({"error": "Habit not found"}), 404

    return jsonify({"message": "Habit deleted"})


@app.route("/api/toggle", methods=["POST"])
@login_required
def toggle_completion():
    payload = request.get_json(silent=True) or {}
    habit_type = payload.get("type")
    habit_id = payload.get("habit_id")
    checked = 1 if payload.get("checked") else 0

    if not habit_type or not habit_id:
        return jsonify({"error": "Missing required fields"}), 400

    now = datetime.now()
    year = now.year
    month = now.month
    user_id = get_current_user_id()

    conn = get_db()
    cursor = conn.cursor()

    if not ensure_owned_habit(cursor, habit_type, habit_id, user_id):
        cursor.close()
        conn.close()
        return jsonify({"error": "Habit not found"}), 404

    if habit_type == "daily":
        day = payload.get("day")
        if day is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "Day is required for daily habits"}), 400

        cursor.execute(
            """
            INSERT INTO daily_completions (habit_id, year, month, day, completed)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE completed = VALUES(completed)
            """,
            (habit_id, year, month, day, checked),
        )

    elif habit_type == "weekly":
        week = payload.get("week")
        if week is None:
            cursor.close()
            conn.close()
            return jsonify({"error": "Week is required for weekly habits"}), 400

        cursor.execute(
            """
            INSERT INTO weekly_completions (habit_id, year, month, week, completed)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE completed = VALUES(completed)
            """,
            (habit_id, year, month, week, checked),
        )

    elif habit_type == "monthly":
        cursor.execute(
            """
            INSERT INTO monthly_completions (habit_id, year, month, completed)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE completed = VALUES(completed)
            """,
            (habit_id, year, month, checked),
        )

    else:
        cursor.close()
        conn.close()
        return jsonify({"error": "Invalid completion type"}), 400

    conn.commit()
    cursor.close()
    days_in_month = monthrange(year, month)[1]
    stats = fetch_stats(conn, year, month, days_in_month, user_id)
    conn.close()

    return jsonify({"message": "Updated", "stats": stats})


@app.route("/api/stats")
@login_required
def stats_api():
    now = datetime.now()
    year = now.year
    month = now.month
    days_in_month = monthrange(year, month)[1]
    user_id = get_current_user_id()

    conn = get_db()
    stats = fetch_stats(conn, year, month, days_in_month, user_id)
    conn.close()
    return jsonify(stats)


init_db()


if __name__ == "__main__":
    app.run(debug=True)
