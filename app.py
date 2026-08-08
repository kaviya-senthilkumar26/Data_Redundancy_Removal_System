from flask import Flask, render_template, request, redirect
import sqlite3
import psycopg2
import psycopg2.extras
import os
import re
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


# =========================================================
# DATABASE CONNECTION WRAPPER
# =========================================================

class PostgreSQLConnection:

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):

        query = query.replace("?", "%s")

        cursor = self.connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        cursor.execute(query, parameters)

        return PostgreSQLCursor(cursor)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


class PostgreSQLCursor:

    def __init__(self, cursor):
        self.cursor = cursor

    def fetchone(self):

        row = self.cursor.fetchone()

        if row is None:
            return None

        return RowWrapper(row)

    def fetchall(self):

        rows = self.cursor.fetchall()

        return [
            RowWrapper(row)
            for row in rows
        ]


class RowWrapper:

    def __init__(self, row):
        self.row = row

    def __getitem__(self, key):

        # Allow [0] for COUNT queries
        if isinstance(key, int):

            values = list(self.row.values())

            return values[key]

        # Allow ["id"], ["name"], etc.
        return self.row[key]

    def __iter__(self):
        return iter(self.row.values())

# =========================================================
# VALIDATE USER INPUT
# =========================================================

def validate_data(name, email):

    if not name:
        return "❌ Name cannot be empty."

    if not re.match(r"^[A-Za-z ]+$", name):
        return "❌ Name can contain only letters and spaces."

    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    if not re.match(email_pattern, email):
        return "❌ Please enter a valid email address."

    return None


# =========================================================
# NORMALIZE DATA
# =========================================================

def normalize_text(value):

    return " ".join(
        value.strip().lower().split()
    )


# =========================================================
# NAME SIMILARITY
# =========================================================

def names_are_similar(name1, name2):

    name1 = normalize_text(name1)
    name2 = normalize_text(name2)

    if name1 == name2:
        return True

    words1 = set(name1.split())
    words2 = set(name2.split())

    if not words1 or not words2:
        return False

    common_words = words1.intersection(words2)

    similarity = len(common_words) / max(
        len(words1),
        len(words2)
    )

    return similarity >= 0.5


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    database_url = os.getenv("DATABASE_URL")

    # -----------------------------------------------------
    # CLOUD - POSTGRESQL
    # -----------------------------------------------------

    if database_url:

        connection = psycopg2.connect(
            database_url
        )

        return PostgreSQLConnection(connection)

    # -----------------------------------------------------
    # LOCAL - SQLITE
    # -----------------------------------------------------

    conn = sqlite3.connect(
        "database.db"
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# CREATE DATABASE AND TABLE
# =========================================================

def init_db():

    database_url = os.getenv("DATABASE_URL")

    # -----------------------------------------------------
    # POSTGRESQL
    # -----------------------------------------------------

    if database_url:

        conn = psycopg2.connect(
            database_url
        )

        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)

        conn.commit()

        cursor.close()
        conn.close()

    # -----------------------------------------------------
    # SQLITE
    # -----------------------------------------------------

    else:

        conn = sqlite3.connect(
            "database.db"
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)

        conn.commit()
        conn.close()


init_db()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def home():

    conn = get_db_connection()

    # Total records
    total_records = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    # Unique records
    unique_records = conn.execute(
        """
        SELECT COUNT(DISTINCT LOWER(TRIM(email)))
        FROM users
        """
    ).fetchone()[0]

    # Duplicate records
    duplicate_records = conn.execute("""
        SELECT COALESCE(
            SUM(record_count - 1), 0
        )
        FROM (
            SELECT COUNT(*) AS record_count
            FROM users
            GROUP BY
                LOWER(TRIM(name)),
                LOWER(TRIM(email))
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
    """).fetchone()[0]

    # Data Quality Score
    if total_records > 0:

        quality_score = round(
            (unique_records / total_records) * 100,
            2
        )

    else:

        quality_score = 100

    # Redundancy Percentage
    if total_records > 0:

        redundancy_percentage = round(
            (duplicate_records / total_records) * 100,
            2
        )

    else:

        redundancy_percentage = 0

    conn.close()

    return render_template(
        "index.html",
        total_records=total_records,
        unique_records=unique_records,
        duplicate_records=duplicate_records,
        quality_score=quality_score,
        redundancy_percentage=redundancy_percentage
    )


# =========================================================
# ADD RECORD
# =========================================================

@app.route("/add", methods=["GET", "POST"])
def add():

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()

        # Validate input
        validation_error = validate_data(
            name,
            email
        )

        if validation_error:

            return render_template(
                "add.html",
                message=validation_error
            )

        conn = get_db_connection()

        # Check duplicate email
        existing_email = conn.execute(
            """
            SELECT * FROM users
            WHERE LOWER(TRIM(email)) = ?
            """,
            (email,)
        ).fetchone()

        # Check logical duplicate
        existing_record = conn.execute(
            """
            SELECT * FROM users
            WHERE LOWER(TRIM(name)) = ?
            AND LOWER(TRIM(email)) = ?
            """,
            (
                normalize_text(name),
                email
            )
        ).fetchone()

        if existing_email:

            message = (
                "❌ Duplicate Record! "
                "This email already exists."
            )

        elif existing_record:

            message = (
                "❌ Redundant Record! "
                "This person already exists."
            )

        else:

            try:

                conn.execute(
                    """
                    INSERT INTO users (name, email)
                    VALUES (?, ?)
                    """,
                    (
                        name,
                        email
                    )
                )

                conn.commit()

                message = (
                    "✅ Unique record added successfully!"
                )

            except Exception:

                conn.rollback()

                message = (
                    "❌ Unable to add record."
                )

        conn.close()

    return render_template(
        "add.html",
        message=message
    )


# =========================================================
# VIEW / SEARCH RECORDS
# =========================================================

@app.route("/records")
def records():

    search = request.args.get(
        "search",
        ""
    ).strip()

    conn = get_db_connection()

    if search:

        data = conn.execute(
            """
            SELECT * FROM users
            WHERE name LIKE ?
               OR email LIKE ?
            ORDER BY id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%"
            )
        ).fetchall()

    else:

        data = conn.execute(
            """
            SELECT * FROM users
            ORDER BY id DESC
            """
        ).fetchall()

    conn.close()

    return render_template(
        "records.html",
        data=data,
        search=search
    )


# =========================================================
# EDIT RECORD
# =========================================================

@app.route(
    "/edit/<int:id>",
    methods=["GET", "POST"]
)
def edit(id):

    conn = get_db_connection()

    record = conn.execute(
        """
        SELECT * FROM users
        WHERE id = ?
        """,
        (id,)
    ).fetchone()

    if record is None:

        conn.close()

        return "Record not found", 404

    message = ""

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()

        validation_error = validate_data(
            name,
            email
        )

        if validation_error:

            conn.close()

            return render_template(
                "edit.html",
                record=record,
                message=validation_error
            )

        # Check another record using email
        existing = conn.execute(
            """
            SELECT * FROM users
            WHERE LOWER(TRIM(email)) = ?
            AND id != ?
            """,
            (
                email,
                id
            )
        ).fetchone()

        if existing:

            message = (
                "❌ Another record already "
                "uses this email."
            )

        else:

            conn.execute(
                """
                UPDATE users
                SET name = ?, email = ?
                WHERE id = ?
                """,
                (
                    name,
                    email,
                    id
                )
            )

            conn.commit()
            conn.close()

            return redirect("/records")

    conn.close()

    return render_template(
        "edit.html",
        record=record,
        message=message
    )


# =========================================================
# DELETE RECORD
# =========================================================

@app.route("/delete/<int:id>")
def delete(id):

    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/records")


# =========================================================
# ADVANCED DUPLICATE SCANNER
# =========================================================

@app.route("/duplicates")
def duplicates():

    conn = get_db_connection()

    records = conn.execute(
        """
        SELECT * FROM users
        ORDER BY id ASC
        """
    ).fetchall()

    duplicate_groups = []

    # Compare every pair
    for i in range(len(records)):

        for j in range(i + 1, len(records)):

            record1 = records[i]
            record2 = records[j]

            name1 = normalize_text(
                record1["name"]
            )

            name2 = normalize_text(
                record2["name"]
            )

            email1 = normalize_text(
                record1["email"]
            )

            email2 = normalize_text(
                record2["email"]
            )

            # Exact duplicate
            if name1 == name2 and email1 == email2:

                duplicate_groups.append({
                    "id1": record1["id"],
                    "id2": record2["id"],
                    "name1": record1["name"],
                    "name2": record2["name"],
                    "email1": record1["email"],
                    "email2": record2["email"],
                    "type": "Exact Duplicate"
                })

            # Potential duplicate
            elif names_are_similar(
                name1,
                name2
            ):

                duplicate_groups.append({
                    "id1": record1["id"],
                    "id2": record2["id"],
                    "name1": record1["name"],
                    "name2": record2["name"],
                    "email1": record1["email"],
                    "email2": record2["email"],
                    "type": "Potential Duplicate"
                })

    conn.close()

    return render_template(
        "duplicates.html",
        duplicate_groups=duplicate_groups
    )


# =========================================================
# REVIEW DUPLICATE
# =========================================================

@app.route(
    "/review-duplicate",
    methods=["POST"]
)
def review_duplicate():

    delete_id = request.form.get(
        "delete_id"
    )

    if not delete_id:

        return redirect("/duplicates")

    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM users
        WHERE id = ?
        """,
        (delete_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/duplicates")


# =========================================================
# REMOVE EXACT DUPLICATES
# =========================================================

@app.route(
    "/remove-duplicates",
    methods=["POST"]
)
def remove_duplicates():

    conn = get_db_connection()

    groups = conn.execute("""
        SELECT
            LOWER(TRIM(name)) AS clean_name,
            LOWER(TRIM(email)) AS clean_email
        FROM users
        GROUP BY
            LOWER(TRIM(name)),
            LOWER(TRIM(email))
        HAVING COUNT(*) > 1
    """).fetchall()

    removed_count = 0

    for group in groups:

        records = conn.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(TRIM(name)) = ?
              AND LOWER(TRIM(email)) = ?
            ORDER BY id ASC
            """,
            (
                group["clean_name"],
                group["clean_email"]
            )
        ).fetchall()

        # Keep oldest record
        for record in records[1:]:

            conn.execute(
                """
                DELETE FROM users
                WHERE id = ?
                """,
                (record["id"],)
            )

            removed_count += 1

    conn.commit()
    conn.close()

    return render_template(
        "cleanup_result.html",
        removed_count=removed_count
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    try:

        conn = get_db_connection()

        conn.execute(
            "SELECT 1"
        ).fetchone()

        conn.close()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )