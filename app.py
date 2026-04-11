from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory
import csv
import os
import hashlib
import secrets
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(32)

USERS_CSV = 'users.csv'
CSV_FIELDS = ['id', 'first_name', 'last_name', 'email', 'phone', 'password_hash', 'created_at']


def init_csv():
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_email(email):
    if not os.path.exists(USERS_CSV):
        return None
    with open(USERS_CSV, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'].lower() == email.lower():
                return row
    return None

def save_user(user_data):
    with open(USERS_CSV, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(user_data)

def get_all_users():
    users = []
    if not os.path.exists(USERS_CSV):
        return users
    with open(USERS_CSV, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_copy = dict(row)
            row_copy.pop('password_hash', None)
            users.append(row_copy)
    return users


# ── Static HTML pages ────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/signin')
@app.route('/signin.html')
def signin():
    return send_from_directory('templates', 'signin.html')

@app.route('/dashboard')
@app.route('/dashboard.html')
def dashboard():
    if 'user_email' not in session:
        return redirect('/signin')
    return send_from_directory('templates', 'dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    first_name = (data.get('first_name') or '').strip()
    last_name  = (data.get('last_name')  or '').strip()
    email      = (data.get('email')      or '').strip().lower()
    phone      = (data.get('phone')      or '').strip()
    password   = (data.get('password')   or '').strip()

    if not all([first_name, last_name, email, password]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'}), 400

    if get_user_by_email(email):
        return jsonify({'success': False, 'message': 'An account with this email already exists.'}), 409

    user_id = secrets.token_hex(8)
    new_user = {
        'id': user_id,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'phone': phone,
        'password_hash': hash_password(password),
        'created_at': datetime.utcnow().isoformat()
    }
    save_user(new_user)

    session['user_email'] = email
    session['user_name']  = f"{first_name} {last_name}"
    session['user_id']    = user_id

    return jsonify({
        'success': True,
        'message': 'Account created successfully!',
        'user': {'name': f"{first_name} {last_name}", 'email': email}
    })


@app.route('/api/signin', methods=['POST'])
def signin_api():
    data     = request.get_json()
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    user = get_user_by_email(email)
    if not user or user['password_hash'] != hash_password(password):
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

    session['user_email'] = email
    session['user_name']  = f"{user['first_name']} {user['last_name']}"
    session['user_id']    = user['id']

    return jsonify({
        'success': True,
        'message': 'Signed in successfully!',
        'user': {'name': session['user_name'], 'email': email}
    })


@app.route('/api/session')
def get_session():
    if 'user_email' in session:
        return jsonify({
            'logged_in': True,
            'name': session.get('user_name', 'User'),
            'email': session.get('user_email', '')
        })
    return jsonify({'logged_in': False})


@app.route('/api/users')
def list_users():
    """Admin endpoint to view all registered users."""
    return jsonify(get_all_users())


if __name__ == '__main__':
    init_csv()
    print("🌿 AgroVerse backend running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
