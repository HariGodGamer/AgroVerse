import csv
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, session, redirect, render_template, current_app
from app.config import Config

machinery_bp = Blueprint('machinery', __name__)

MACHINE_CONFIG = {
    "Tractor":            {"emoji": "🚜", "image": "tractor.png"},
    "Combine Harvester":  {"emoji": "🌾", "image": "combine_harvester.png"},
    "Rotavator":          {"emoji": "⚙️",  "image": "rotavator.png"},
    "Plough":             {"emoji": "🪛",  "image": "plough.png"},
    "Cultivator":         {"emoji": "🌱",  "image": "cultivator.png"},
    "Harrow":             {"emoji": "🔧",  "image": "Harrow.png"},
    "Seed Drill":         {"emoji": "🌿",  "image": "drill.png"},
    "Power Tiller":       {"emoji": "⚡",  "image": "power_tiller.png"},
    "Baler":              {"emoji": "📦",  "image": "baler.png"},
    "Sprayer":            {"emoji": "💧",  "image": "sprayer.png"},
    "Rice Transplanter":  {"emoji": "🌾",  "image": "rice_transplanter.png"},
    "Straw Reaper":       {"emoji": "🌾",  "image": "straw_reaper.png"},
    "Laser Land Leveler": {"emoji": "📡",  "image": "laser_land_eveler.png"},
    "Potato Planter":     {"emoji": "🥔",  "image": "potato_planter.png"},
    "Backhoe Loader":     {"emoji": "🏗️",  "image": "backhoe_loader.png"},
}
MACHINE_TYPES = list(MACHINE_CONFIG.keys())

def ensure_csv():
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    if not os.path.exists(Config.MACHINES_CSV):
        fields = ['id', 'state', 'district', 'machine_type', 'owner_name', 'rent_per_day', 'phone', 'address', 'added_on']
        with open(Config.MACHINES_CSV, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()

def read_all():
    ensure_csv()
    with open(Config.MACHINES_CSV, 'r', newline='', encoding='utf-8') as f:
        return [dict(r) for r in csv.DictReader(f)]

def append_row(row):
    ensure_csv()
    fields = ['id', 'state', 'district', 'machine_type', 'owner_name', 'rent_per_day', 'phone', 'address', 'added_on']
    with open(Config.MACHINES_CSV, 'a', newline='', encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=fields).writerow({k: row.get(k, '') for k in fields})

def image_url(machine_type, static_folder):
    cfg      = MACHINE_CONFIG.get(machine_type, {})
    filename = cfg.get('image', '')
    disk     = os.path.join(static_folder, 'images', 'machines', filename)
    return f"/static/images/machines/{filename}" if filename and os.path.exists(disk) else ""

def enrich(row, static_folder):
    cfg = MACHINE_CONFIG.get(row['machine_type'], {})
    row['emoji']     = cfg.get('emoji', '🚜')
    row['image_url'] = image_url(row['machine_type'], static_folder)
    return row

def machines_for(state, district, static_folder):
    s, d = state.strip().lower(), district.strip().lower()
    return [enrich(r, static_folder) for r in read_all()
            if r['state'].strip().lower() == s
            and r['district'].strip().lower() == d]

def save_machine(state, district, d):
    row = {
        'id':           str(uuid.uuid4()),
        'state':        state,
        'district':     district,
        'machine_type': d['machine_type'],
        'owner_name':   d['owner_name'],
        'rent_per_day': str(d['rent_per_day']),
        'phone':        d['phone'],
        'address':      d['address'],
        'added_on':     datetime.now().strftime('%d %b %Y'),
    }
    append_row(row)
    return row


@machinery_bp.route('/machinery', strict_slashes=False)
def machinery_page():
    if 'user_email' not in session:
        return redirect('/signin')
    from app import STATES_DISTRICTS
    return render_template('machinery.html',
                           states=sorted(STATES_DISTRICTS),
                           machine_types=MACHINE_TYPES,
                           machine_config=MACHINE_CONFIG)


@machinery_bp.route('/api/machinery/districts/<state>')
def api_districts(state):
    from app import STATES_DISTRICTS
    return jsonify(sorted(STATES_DISTRICTS.get(state, [])))


@machinery_bp.route('/api/machinery/list')
def api_machines():
    s = request.args.get('state', '').strip()
    d = request.args.get('district', '').strip()
    if not s or not d:
        return jsonify({'error': 'state and district required'}), 400
    return jsonify(machines_for(s, d, current_app.static_folder))


@machinery_bp.route('/api/machinery/add', methods=['POST'])
def api_add():
    try:
        from app import STATES_DISTRICTS
        d            = request.get_json(force=True)
        state        = d.get('state', '').strip()
        district     = d.get('district', '').strip()
        machine_type = d.get('machine_type', '').strip()
        owner_name   = d.get('owner_name', '').strip()
        rent_per_day = str(d.get('rent_per_day', '')).strip()
        phone        = d.get('phone', '').strip()
        address      = d.get('address', '').strip()

        if not all([state, district, machine_type, owner_name, rent_per_day, phone, address]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        if state not in STATES_DISTRICTS:
            return jsonify({'success': False, 'error': 'Invalid state'}), 400
        if district not in STATES_DISTRICTS[state]:
            return jsonify({'success': False, 'error': 'Invalid district'}), 400
        if machine_type not in MACHINE_TYPES:
            return jsonify({'success': False, 'error': 'Invalid machine type'}), 400
        try:
            rent = float(rent_per_day)
            assert rent > 0
        except Exception:
            return jsonify({'success': False, 'error': 'Rent must be a positive number'}), 400
        if not phone.isdigit() or len(phone) != 10:
            return jsonify({'success': False, 'error': 'Phone must be 10 digits'}), 400

        row = save_machine(state, district,
                           dict(machine_type=machine_type, owner_name=owner_name,
                                rent_per_day=rent, phone=phone, address=address))
        enriched = enrich(row, current_app.static_folder)
        return jsonify({'success': True, 'machine': enriched})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
