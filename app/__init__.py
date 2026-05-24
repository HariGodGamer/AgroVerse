import os
import csv
import json
from flask import Flask
from flask_cors import CORS
from app.config import Config

STATES_DISTRICTS = {}

def load_india_data():
    global STATES_DISTRICTS
    try:
        if os.path.exists(Config.INDIA_DATA_FILE):
            with open(Config.INDIA_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            states_districts = {}
            for state in data:
                states_districts[state['state']] = state['districts']
            STATES_DISTRICTS = states_districts
            print(f"[OK] India geographic data loaded: {len(STATES_DISTRICTS)} states.")
        else:
            print(f"[!] India geographic data file not found at {Config.INDIA_DATA_FILE}")
    except Exception as e:
        print(f"[FAIL] Error loading india_data.json: {e}")

def init_csv():
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    
    # Initialize users CSV
    if not os.path.exists(Config.USERS_CSV):
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'password_hash', 'firebase_uid', 'created_at']
        with open(Config.USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()
            
    # Initialize reviews CSV
    if not os.path.exists(Config.REVIEWS_CSV):
        fields = ['id', 'user_id', 'user_name', 'user_initial', 'rating', 'review', 'features', 'created_at']
        with open(Config.REVIEWS_CSV, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()
            
    # Initialize machines CSV
    if not os.path.exists(Config.MACHINES_CSV):
        fields = ['id', 'state', 'district', 'machine_type', 'owner_name', 'rent_per_day', 'phone', 'address', 'added_on']
        with open(Config.MACHINES_CSV, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=fields).writeheader()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    
    CORS(app, supports_credentials=True)
    
    # Initialize CSV databases and load geographic data
    init_csv()
    load_india_data()
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.machinery import machinery_bp
    from app.routes.disease import disease_bp
    from app.routes.chat import chat_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(machinery_bp)
    app.register_blueprint(disease_bp)
    app.register_blueprint(chat_bp)
    
    return app

def load_disease_model():
    from app.utils.disease_model import load_model
    load_model()
