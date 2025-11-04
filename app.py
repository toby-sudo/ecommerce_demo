from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from passlib.hash import pbkdf2_sha256

app = Flask(__name__)
app.secret_key = "change-this-secret"
DB = "shop.sqlite3"

def get_db():
    return sqlite3.connect(DB)

def init_db():
    with get_db() as cnx:
        cnx.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )""")
        cnx.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL
        )""")
        if cnx.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            cnx.executemany("INSERT INTO products(name, price) VALUES(?,?)",
                            [("Laptop Sleeve", 999.0),
                             ("USB-C Cable", 299.0),
                             ("Wireless Mouse", 799.0)])

@app.before_first_request
def setup():
    init_db()

@app.route("/")
def home():
    with get_db() as cnx:
        products = cnx.execute("SELECT id, name, price FROM products").fetchall()
    return render_template("index.html", products=products)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pwd = pbkdf2_sha256.hash(request.form["password"])
        try:
            with get_db() as cnx:
                cnx.execute("INSERT INTO users(email,password) VALUES(?,?)",(email,pwd))
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Email already registered")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pwd = request.form["password"]
        with get_db() as cnx:
            row = cnx.execute("SELECT id, password FROM users WHERE email=?", (email,)).fetchone()
        if row and pbkdf2_sha256.verify(pwd, row[1]):
            session["uid"] = row[0]
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/add/<int:pid>")
def add_to_cart(pid):
    cart = session.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + 1
    session["cart"] = cart
    return redirect(url_for("home"))

@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    items, total = [], 0.0
    if cart:
        with get_db() as cnx:
            for pid, qty in cart.items():
                row = cnx.execute("SELECT id, name, price FROM products WHERE id=?", (pid,)).fetchone()
                if row:
                    items.append({"name": row[1], "price": row[2], "qty": qty, "sub": row[2]*qty})
                    total += row[2]*qty
    return render_template("cart.html", items=items, total=total)

if __name__ == "__main__":
    app.run(debug=True)
