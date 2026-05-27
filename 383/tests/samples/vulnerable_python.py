"""Python漏洞代码样本 - 用于测试Security Fixer"""

import sqlite3
import os
import subprocess
from flask import Flask, request, render_template, send_file

app = Flask(__name__)


@app.route("/user")
def get_user():
    user_id = request.args.get("id", "")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchall()


@app.route("/search")
def search():
    keyword = request.args.get("q", "")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    query = f"SELECT * FROM products WHERE name LIKE '%{keyword}%'"
    cursor.execute(query)
    return cursor.fetchall()


@app.route("/search_safe")
def search_safe():
    keyword = request.args.get("q", "")
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    query = "SELECT * FROM products WHERE name LIKE ?"
    cursor.execute(query, (f"%{keyword}%",))
    return cursor.fetchall()


@app.route("/page")
def show_page():
    content = request.args.get("content", "")
    return f"<html><body>{content}</body></html>"


@app.route("/profile")
def profile():
    name = request.args.get("name", "")
    template = f"<h1>Welcome {name}</h1>"
    return render_template("profile.html", content=template)


@app.route("/file")
def get_file():
    filename = request.args.get("name", "")
    filepath = "/var/www/files/" + filename
    with open(filepath, "r") as f:
        return f.read()


@app.route("/download")
def download_file():
    filename = request.args.get("file", "")
    return send_file("/var/www/files/" + filename)


@app.route("/run")
def run_command():
    cmd = request.args.get("cmd", "")
    os.system("ping -c 3 " + cmd)
    return "done"


@app.route("/process")
def process_data():
    input_data = request.args.get("data", "")
    result = subprocess.check_output(
        "echo " + input_data,
        shell=True
    )
    return result


@app.route("/run_safe")
def run_safe():
    cmd = request.args.get("cmd", "")
    allowed = ["ls", "cat", "grep"]
    if cmd not in allowed:
        return "invalid"
    subprocess.run([cmd], shell=False)
    return "done"


if __name__ == "__main__":
    app.run()
