import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    WEATHER_API_KEY = "0d8a42b258ff46f6b3b111338260304"
    WORQHAT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJIejIxeFBMMTc1VVJldUY1bndVQnpNUEpEVmEyIiwidXNlcklkIjoiSHoyMXhQTDE3NVVSZXVGNW53VUJ6TVBKRFZhMiIsInRlYW1JZCI6Ijk2YzkwZjRjLTAyZmQtNGFiZi1iZGVmLWEyOWQyZWVkMzAyNyIsInRlYW1Sb2xlIjoib3duZXIiLCJwcm9qZWN0SWQiOiIzOWFjN2I5Yy02YzNhLTQ0YzctOWU2OS04NjEzM2U4MWE3NzYiLCJpYXQiOjE3Nzk2MjU4NTUsImV4cCI6MTgyOTYyNTg1NX0.VdxIp28yg0kveK_NOBLys_SzrNtaxf0nlWeObVDdyCY"
    
    # Base directories
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(APP_DIR)
    DATA_DIR = os.path.join(ROOT_DIR, 'data')
    
    # Database and data files
    USERS_CSV = os.path.join(DATA_DIR, 'users.csv')
    REVIEWS_CSV = os.path.join(DATA_DIR, 'reviews.csv')
    DASHBOARD_DATA_FILE = os.path.join(DATA_DIR, 'dashboard_data.json')
    CROP_TRACKING_FILE = os.path.join(DATA_DIR, 'crop_tracking.json')
    MARKETPLACE_FILE = os.path.join(DATA_DIR, 'marketplace_listings.json')
    INDIA_DATA_FILE = os.path.join(DATA_DIR, 'india_data.json')
    MACHINES_CSV = os.path.join(DATA_DIR, 'machines.csv')
    SALES_LOGS_FILE = os.path.join(DATA_DIR, 'sales_logs.json')
    
    # Upload folders
    DISEASE_UPLOAD_DIR = os.path.join(ROOT_DIR, 'disease_uploads')
