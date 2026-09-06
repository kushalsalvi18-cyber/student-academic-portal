import os

import psycopg
from psycopg.rows import dict_row

from flask import Flask, render_template, request, redirect, url_for, session, flash


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "student-academic-portal-secret-key"
)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


# ---------------- DATABASE ----------------

def db():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        row_factory=dict_row,
        sslmode="require"
    )


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS student_data (
            id BIGINT PRIMARY KEY,
            name TEXT,
            branch TEXT,
            semester BIGINT,
            total_marks DOUBLE PRECISION
        )
    """)

    conn.commit()
    conn.close()


# ---------------- HELPERS ----------------

def grade(marks):
    if marks >= 90:
        return "A+"
    elif marks >= 80:
        return "A"
    elif marks >= 70:
        return "B+"
    elif marks >= 60:
        return "B"
    elif marks >= 50:
        return "C"
    else:
        return "F"


def formdata(form):
    try:
        student_id = int(form["id"])
        name = form["name"].strip()
        branch = form["branch"].strip()
        semester = int(form["semester"])
        total_marks = float(form["total_marks"])

        if not name or not branch:
            return None, "Name and branch are required."

        if not 1 <= semester <= 12:
            return None, "Semester must be between 1 and 12."

        if not 0 <= total_marks <= 100:
            return None, "Marks must be between 0 and 100."

        return (
            student_id,
            name,
            branch,
            semester,
            total_marks
        ), None

    except Exception:
        return None, "Please enter valid values."


# ---------------- STUDENT LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "").strip()

        conn = db()

        student = conn.execute(
            "SELECT * FROM student_data WHERE id=%s",
            (student_id,)
        ).fetchone()

        conn.close()

        if student and password == f"{student_id}@123":

            session.clear()
            session["student_id"] = int(student_id)

            return redirect(url_for("dashboard"))

        error = "Invalid Student ID or Password."

    return render_template(
        "login.html",
        error=error
    )


# ---------------- STUDENT DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    student_id = session.get("student_id")

    if not student_id:
        return redirect(url_for("login"))

    conn = db()

    student = conn.execute(
        "SELECT * FROM student_data WHERE id=%s",
        (student_id,)
    ).fetchone()

    rank = conn.execute(
        """
        SELECT COUNT(*) + 1 AS rank
        FROM student_data
        WHERE total_marks >
        (
            SELECT total_marks
            FROM student_data
            WHERE id=%s
        )
        """,
        (student_id,)
    ).fetchone()

    conn.close()

    if not student:

        session.clear()

        return redirect(url_for("login"))

    marks = float(student["total_marks"])

    return render_template(
        "dashboard.html",
        student=student,
        percentage=marks,
        grade=grade(marks),
        rank=rank["rank"]
    )


# ---------------- STUDENT LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    error = None

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session.clear()
            session["admin"] = True

            return redirect(url_for("admin"))

        error = "Invalid admin username or password."

    return render_template(
        "admin_login.html",
        error=error
    )


# ---------------- ADMIN LOGOUT ----------------

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("admin_login"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = db()

    students = conn.execute(
        "SELECT * FROM student_data ORDER BY id"
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        students=students
    )


# ---------------- ADD STUDENT ----------------

@app.route("/admin/add", methods=["POST"])
def add():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    data, error = formdata(request.form)

    if error:

        flash(error, "error")

        return redirect(url_for("admin"))

    conn = db()

    existing = conn.execute(
        "SELECT 1 FROM student_data WHERE id=%s",
        (data[0],)
    ).fetchone()

    if existing:

        conn.close()

        flash(
            "Student ID already exists.",
            "error"
        )

        return redirect(url_for("admin"))

    conn.execute(
        """
        INSERT INTO student_data
        (id, name, branch, semester, total_marks)
        VALUES (%s, %s, %s, %s, %s)
        """,
        data
    )

    conn.commit()
    conn.close()

    flash(
        f"Student {data[0]} added successfully.",
        "success"
    )

    return redirect(url_for("admin"))


# ---------------- UPDATE STUDENT ----------------

@app.route("/admin/update/<int:sid>", methods=["POST"])
def update(sid):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    data, error = formdata(request.form)

    if error:

        flash(error, "error")

        return redirect(url_for("admin"))

    conn = db()

    if data[0] != sid:

        existing = conn.execute(
            "SELECT 1 FROM student_data WHERE id=%s",
            (data[0],)
        ).fetchone()

        if existing:

            conn.close()

            flash(
                "New Student ID already exists.",
                "error"
            )

            return redirect(url_for("admin"))

    conn.execute(
        """
        UPDATE student_data
        SET id=%s,
            name=%s,
            branch=%s,
            semester=%s,
            total_marks=%s
        WHERE id=%s
        """,
        (
            data[0],
            data[1],
            data[2],
            data[3],
            data[4],
            sid
        )
    )

    conn.commit()
    conn.close()

    flash(
        "Student record updated successfully.",
        "success"
    )

    return redirect(url_for("admin"))


# ---------------- DELETE STUDENT ----------------

@app.route("/admin/delete/<int:sid>", methods=["POST"])
def delete(sid):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = db()

    conn.execute(
        "DELETE FROM student_data WHERE id=%s",
        (sid,)
    )

    conn.commit()
    conn.close()

    flash(
        f"Student {sid} deleted.",
        "success"
    )

    return redirect(url_for("admin"))


# ---------------- START APP ----------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True
    )