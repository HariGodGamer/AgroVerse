import csv
import os
import hashlib
import secrets
from datetime import datetime
from flask import Blueprint, request, jsonify, session, redirect, render_template
from app.config import Config

main_bp = Blueprint('main', __name__)

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def get_user_by_email(email):
    if not os.path.exists(Config.USERS_CSV):
        return None
    with open(Config.USERS_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['email'].lower() == email.lower():
                return row
    return None

def save_user(u):
    fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'password_hash', 'firebase_uid', 'created_at', 'land_owned', 'device_connected', 'soil_moisture', 'soil_n', 'soil_p', 'soil_k']
    with open(Config.USERS_CSV, 'a', newline='', encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=fields).writerow(u)

def update_user(updated_user):
    if not os.path.exists(Config.USERS_CSV):
        return False
    fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'password_hash', 'firebase_uid', 'created_at', 'land_owned', 'device_connected', 'soil_moisture', 'soil_n', 'soil_p', 'soil_k']
    rows = []
    updated = False
    with open(Config.USERS_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['id'] == updated_user['id']:
                row.update(updated_user)
                updated = True
            rows.append(row)
    if not updated:
        return False
    with open(Config.USERS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return True

def get_all_users():
    if not os.path.exists(Config.USERS_CSV):
        return []
    with open(Config.USERS_CSV, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.pop('password_hash', None)
    return rows


@main_bp.route('/')
@main_bp.route('/index')
@main_bp.route('/index.html')
def index():
    return render_template('index.html')


@main_bp.route('/signin')
@main_bp.route('/signin.html')
def signin_page():
    return render_template('signin.html')


@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@main_bp.route('/api/signup', methods=['POST'])
def signup():
    d = request.get_json() or {}
    fn = (d.get('first_name') or '').strip()
    ln = (d.get('last_name') or '').strip()
    em = (d.get('email') or '').strip().lower()
    ph = (d.get('phone') or '').strip()
    pw = d.get('password')
    
    if not all([fn, ln, em, pw]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
    if ph and (not ph.isdigit() or len(ph) != 10):
        return jsonify({'success': False, 'message': 'Phone number must be exactly 10 digits.'}), 400
    if get_user_by_email(em):
        return jsonify({'success': False, 'message': 'Email already registered.'}), 409
        
    uid = secrets.token_hex(8)
    pw_hash = hash_password(pw)
    save_user({
        'id': uid,
        'first_name': fn,
        'last_name': ln,
        'email': em,
        'phone': ph,
        'password_hash': pw_hash,
        'firebase_uid': 'disabled',
        'created_at': datetime.utcnow().isoformat()
    })
    return jsonify({'success': True, 'message': 'Account created successfully!'})


@main_bp.route('/api/signin', methods=['POST'])
def signin_api():
    d = request.get_json() or {}
    em = (d.get('email') or '').strip().lower()
    pw = d.get('password')
    
    if not em or not pw:
        return jsonify({'success': False, 'message': 'Email and password required.'}), 400
    u = get_user_by_email(em)
    if not u:
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401
        
    pw_hash = hash_password(pw)
    if u.get('password_hash') != pw_hash:
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401
        
    session.update({
        'user_email': em,
        'user_name': f"{u['first_name']} {u['last_name']}",
        'user_id': u['id']
    })
    return jsonify({'success': True, 'message': 'Signed in!', 'user': {'name': session['user_name'], 'email': em}})


@main_bp.route('/api/session')
def get_session():
    if 'user_email' in session:
        user = get_user_by_email(session['user_email']) or {}
        return jsonify({
            'logged_in': True,
            'name': session.get('user_name', 'User'),
            'email': session.get('user_email', ''),
            'phone': user.get('phone', ''),
            'land_owned': user.get('land_owned', '0'),
            'device_connected': user.get('device_connected', 'none'),
            'soil_moisture': user.get('soil_moisture', '0'),
            'soil_n': user.get('soil_n', '0'),
            'soil_p': user.get('soil_p', '0'),
            'soil_k': user.get('soil_k', '0')
        })
    return jsonify({'logged_in': False})


@main_bp.route('/api/users')
def list_users():
    return jsonify(get_all_users())


@main_bp.route('/api/account/settings', methods=['POST'])
def update_account_settings():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    current_user = get_user_by_email(session['user_email'])
    if not current_user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    data = request.get_json() or {}
    full_name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    password = (data.get('password') or '').strip()
    confirm_password = (data.get('confirm_password') or '').strip()

    if full_name:
        parts = full_name.split()
        current_user['first_name'] = parts[0]
        current_user['last_name'] = ' '.join(parts[1:]) if len(parts) > 1 else ''

    if phone:
        if not phone.isdigit() or len(phone) != 10:
            return jsonify({'success': False, 'message': 'Phone number must be exactly 10 digits.'}), 400
        current_user['phone'] = phone

    if password or confirm_password:
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'}), 400
        if password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match.'}), 400
        current_user['password_hash'] = hash_password(password)

    # Handle new farm configuration and soil intelligence fields
    if 'land_owned' in data:
        try:
            current_user['land_owned'] = str(float(data['land_owned'] or 0))
        except ValueError:
            current_user['land_owned'] = '0'

    if 'device_connected' in data:
        current_user['device_connected'] = str(data['device_connected'] or 'none')

    for field in ['soil_moisture', 'soil_n', 'soil_p', 'soil_k']:
        if field in data:
            try:
                current_user[field] = str(float(data[field] or 0))
            except ValueError:
                current_user[field] = '0'

    if not update_user(current_user):
        return jsonify({'success': False, 'message': 'Could not update account.'}), 500

    session['user_name'] = f"{current_user['first_name']} {current_user['last_name']}".strip()
    if phone:
        session['user_phone'] = phone

    return jsonify({
        'success': True,
        'message': 'Account updated successfully.',
        'user': {
            'name': session['user_name'],
            'email': session.get('user_email', ''),
            'phone': current_user.get('phone', ''),
            'land_owned': current_user.get('land_owned', '0'),
            'device_connected': current_user.get('device_connected', 'none'),
            'soil_moisture': current_user.get('soil_moisture', '0'),
            'soil_n': current_user.get('soil_n', '0'),
            'soil_p': current_user.get('soil_p', '0'),
            'soil_k': current_user.get('soil_k', '0')
        }
    })
