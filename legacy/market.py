from flask import Flask, request, jsonify, session, redirect, send_from_directory
from flask_cors import CORS
import csv, os, hashlib, secrets
from datetime import datetime

from weather import get_weather_by_coords
from chatbot import get_bot_reply

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
app.secret_key = secrets.token_hex(32)

USERS_CSV  = "users.csv"
CSV_FIELDS = ["id", "first_name", "last_name", "email", "phone", "password_hash", "created_at"]

def init_csv():
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def get_user_by_email(email):
    if not os.path.exists(USERS_CSV):
        return None
    with open(USERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["email"].lower() == email.lower():
                return row
    return None

def save_user(u):
    with open(USERS_CSV, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(u)

def get_all_users():
    if not os.path.exists(USERS_CSV):
        return []
    with open(USERS_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.pop("password_hash", None)
    return rows

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")

@app.route("/signin")
@app.route("/signin.html")
def signin_page():
    return send_from_directory("templates", "signin.html")

@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():
    if "user_email" not in session:
        return redirect("/signin")
    return send_from_directory("templates", "dashboard.html")

@app.route("/market_data")
@app.route("/market_data.html")
def market_data():
    if "user_email" not in session:
        return redirect("/signin")
    return send_from_directory("templates", "market_data.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/signup", methods=["POST"])
def signup():
    d  = request.get_json()
    fn = (d.get("first_name") or "").strip()
    ln = (d.get("last_name")  or "").strip()
    em = (d.get("email")      or "").strip().lower()
    ph = (d.get("phone")      or "").strip()
    pw = (d.get("password")   or "").strip()
    if not all([fn, ln, em, pw]):
        return jsonify({"success": False, "message": "All fields are required."}), 400
    if len(pw) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
    if get_user_by_email(em):
        return jsonify({"success": False, "message": "Email already registered."}), 409
    uid = secrets.token_hex(8)
    save_user({
        "id": uid, "first_name": fn, "last_name": ln, "email": em, "phone": ph,
        "password_hash": hash_password(pw), "created_at": datetime.utcnow().isoformat()
    })
    session.update({"user_email": em, "user_name": f"{fn} {ln}", "user_id": uid})
    return jsonify({"success": True, "message": "Account created!", "user": {"name": f"{fn} {ln}", "email": em}})

@app.route("/api/signin", methods=["POST"])
def signin_api():
    d  = request.get_json()
    em = (d.get("email")    or "").strip().lower()
    pw = (d.get("password") or "").strip()
    if not em or not pw:
        return jsonify({"success": False, "message": "Email and password required."}), 400
    u = get_user_by_email(em)
    if not u or u["password_hash"] != hash_password(pw):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401
    session.update({"user_email": em, "user_name": f"{u['first_name']} {u['last_name']}", "user_id": u["id"]})
    return jsonify({"success": True, "message": "Signed in!", "user": {"name": session["user_name"], "email": em}})

@app.route("/api/session")
def get_session():
    if "user_email" in session:
        return jsonify({"logged_in": True, "name": session.get("user_name", "User"), "email": session.get("user_email", "")})
    return jsonify({"logged_in": False})

@app.route("/api/users")
def list_users():
    return jsonify(get_all_users())


@app.route("/api/weather")
def weather():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "lat and lon required"}), 400
    result = get_weather_by_coords(float(lat), float(lon))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def chat():
    body    = request.get_json() or {}
    message = (body.get("message") or "").strip()
    history = body.get("history", [])
    if not message:
        return jsonify({"error": "message is required"}), 400
    reply = get_bot_reply(message, history)
    return jsonify({"reply": reply})


import requests as http_requests

AGMARKNET_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_KEY = "579b464db66ec23bdd000001a1b52af66a2c48af777e69cb854bc3a7"

@app.route("/prices")
def get_prices():
    try:
        state     = request.args.get("state")
        district  = request.args.get("district")
        commodity = request.args.get("commodity")

        url = f"{AGMARKNET_URL}?api-key={AGMARKNET_KEY}&format=json&limit=100"
        if state:     url += f"&filters[state]={state}"
        if district:  url += f"&filters[district]={district}"
        if commodity: url += f"&filters[commodity]={commodity}"

        resp      = http_requests.get(url, timeout=10)
        data_json = resp.json()

        result = []
        for item in data_json.get("records", []):
            try:
                price_quintal = float(item.get("modal_price", 0))
                price_kg      = round(price_quintal / 100, 2)
            except Exception:
                price_kg = 0

            result.append({
                "state":            item.get("state"),
                "district":         item.get("district"),
                "mandi":            item.get("market"),
                "crop":             item.get("commodity"),
                "price_per_quintal": item.get("modal_price"),
                "price_per_kg":     price_kg,
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_csv()
    print("🌿 AgroVerse → http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
