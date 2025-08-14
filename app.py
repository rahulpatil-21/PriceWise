from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from scrapping import aggregate_basic
import pickle
import pandas as pd
import numpy as np

from datetime import datetime
from pandas.tseries.offsets import DateOffset
import pandas as pd
import pickle
from flask import request, render_template
app = Flask(__name__)
app.secret_key = "a983049ef1d954ffeb668d0c724a9e04"
DB_PATH = "users.db"

# ✅ DB INIT
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                phno TEXT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

# ✅ DB QUERIES
def get_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user

def insert_user(username, phno, email, password_hash):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, phno, email, password) VALUES (?, ?, ?, ?)",
                (username, phno, email, password_hash))
    conn.commit()
    conn.close()


def login_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect("/login")
        return func(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        phno = request.form["phno"]
        email = request.form["email"]
        password = request.form["password"]

        if get_user_by_email(email):
            flash("Email already registered. Try logging in.", "error")
            return redirect("/login")

        password_hash = generate_password_hash(password)
        insert_user(username, phno, email, password_hash)
        flash("Signup successful! Please log in.", "success")
        return redirect("/login")

    return render_template("signup.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = get_user_by_email(email)
        if user and check_password_hash(user[4], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash("Login successful!", "success")
            return redirect("/")  
        else:
            flash("Invalid credentials. Try again.", "error")
            return redirect("/login")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/login")

@app.route('/search', methods=['POST'])
@login_required
def search():
    query = request.form.get("product")
    results = aggregate_basic(query)
    return jsonify(results)

@app.route("/details")
@login_required


def show_details():
   
    raw_discount = request.args.get("discount", "0")
    cleaned_discount = ''.join(c for c in raw_discount if c.isdigit() or c == '.')
    discount_value = float(cleaned_discount) if cleaned_discount else 0.0

    raw_rating = request.args.get("rating", "0")
    cleaned_rating = ''.join(c for c in raw_rating if c.isdigit() or c == '.')
    rating_value = float(cleaned_rating) if cleaned_rating else 0.0

    
    data = {
        "platform": request.args.get("platform", "N/A"),
        "title": request.args.get("title", "N/A"),
        "price": request.args.get("price", "N/A"),
        "mrp": request.args.get("mrp", "N/A"),
        "discount": discount_value,
        "rating": rating_value,
        "image_url": request.args.get("image_url", "#"),
        "category": request.args.get("category", "Fashion")
    }


    try:
        with open("fprice_forecast_model.pkl", "rb") as f:
            model = pickle.load(f)

        
        np.random.seed(42)
        rating_variation = np.clip(rating_value + np.random.normal(0, 0.2, 4), 1, 5)
        stock_variation = np.clip(100 + np.random.normal(0, 10, 4), 10, 500).astype(int)
        discount_variation = np.clip(discount_value + np.random.normal(0, 2, 4), 0, 100)
        month_number_start = 32  
        future_months = pd.date_range(start=datetime.now() + DateOffset(months=1), periods=4, freq="MS")

    
        future_data = pd.DataFrame({
            "Category": [data["category"]] * 4,
            "Rating": data["rating"],
            "Stock": stock_variation,
            "Discount (%)": data["discount"],
            "MonthNumber": [month_number_start + i for i in range(4)],
            "Month": future_months
        })

     
        future_data["PredictedPrice"] = model.predict(future_data[["Category", "Rating", "Stock", "Discount (%)", "MonthNumber"]])

   
        data["future_predictions"] = future_data[["Month", "PredictedPrice"]].to_dict(orient="records")

    except Exception as e:
        print("ML Prediction error:", e)
        data["future_predictions"] = []

  
    return render_template("more_info.html", **data)



    

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
