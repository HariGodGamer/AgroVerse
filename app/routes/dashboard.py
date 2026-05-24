import os
import csv
import json
import secrets
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, session, redirect, render_template, send_from_directory
from app.config import Config

dashboard_bp = Blueprint('dashboard', __name__)

# JSON helpers
def load_json_file(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def default_dashboard_stats():
    return {
        'land_area': 0,
        'soil_moisture': {
            'value': 0,
            'status': 'Hardware integration coming soon'
        },
        'monthly_revenue': 0,
        'active_alerts': 'Under Development'
    }

def get_dashboard_store():
    return load_json_file(Config.DASHBOARD_DATA_FILE, {})

def get_user_dashboard(user_id):
    store = get_dashboard_store()
    return store.get(user_id, default_dashboard_stats())

def save_user_dashboard(user_id, dashboard_data):
    store = get_dashboard_store()
    store[user_id] = dashboard_data
    save_json_file(Config.DASHBOARD_DATA_FILE, store)

def get_crop_tracking_store():
    return load_json_file(Config.CROP_TRACKING_FILE, {})

def save_crop_tracking_store(data):
    save_json_file(Config.CROP_TRACKING_FILE, data)

def get_sales_logs_store():
    return load_json_file(Config.SALES_LOGS_FILE, {})

def save_sales_logs_store(data):
    save_json_file(Config.SALES_LOGS_FILE, data)

def get_marketplace_store():
    return load_json_file(Config.MARKETPLACE_FILE, [])

def save_marketplace_store(data):
    save_json_file(Config.MARKETPLACE_FILE, data)


@dashboard_bp.route('/dashboard')
@dashboard_bp.route('/dashboard.html')
def dashboard_page():
    if 'user_email' not in session:
        return redirect('/signin')
    return render_template('dashboard.html')


@dashboard_bp.route('/newfarmer')
@dashboard_bp.route('/newfarmer.html')
def new_farmer():
    if 'user_email' not in session:
        return redirect('/signin')
    # Import STATES_DISTRICTS dynamically on request to avoid circular dependency
    from app import STATES_DISTRICTS
    return render_template('newfarmer.html',
                           states=sorted(STATES_DISTRICTS),
                           india_data=STATES_DISTRICTS,
                           user_name=session.get('user_name', 'User'),
                           user_email=session.get('user_email', ''))


@dashboard_bp.route('/reviews')
def reviews():
    if 'user_email' not in session:
        return redirect('/signin')
    return render_template('reviews.html')


@dashboard_bp.route('/market_data')
@dashboard_bp.route('/market_data.html')
def market_data_page():
    if 'user_email' not in session:
        return redirect('/signin')
    return render_template('market_data.html')


@dashboard_bp.route('/account')
def account_page():
    if 'user_email' not in session:
        return redirect('/signin')
    return render_template('account.html', 
                           user_name=session.get('user_name', ''), 
                           user_email=session.get('user_email', ''))


@dashboard_bp.route('/india_data.json')
def india_data_json():
    return send_from_directory(Config.DATA_DIR, 'india_data.json')


@dashboard_bp.route('/api/dashboard/data')
def get_dashboard_data():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    return jsonify({
        'success': True,
        'dashboard': get_user_dashboard(session.get('user_id'))
    })


@dashboard_bp.route('/api/dashboard/data', methods=['POST'])
def update_dashboard_data():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    payload = request.get_json() or {}
    current = get_user_dashboard(session.get('user_id'))
    current['land_area'] = float(payload.get('land_area', current.get('land_area', 0)) or 0)
    current['monthly_revenue'] = float(payload.get('monthly_revenue', current.get('monthly_revenue', 0)) or 0)
    moisture_value = payload.get('soil_moisture')
    if moisture_value not in (None, ''):
        current['soil_moisture']['value'] = float(moisture_value)
    current['soil_moisture']['status'] = 'Sensor-ready placeholder for upcoming hardware integration'
    current['active_alerts'] = 'Under Development'
    save_user_dashboard(session.get('user_id'), current)
    return jsonify({'success': True, 'dashboard': current})


@dashboard_bp.route('/api/guide/crops', methods=['GET'])
def get_tracked_crops():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    store = get_crop_tracking_store()
    return jsonify({'success': True, 'crops': store.get(session.get('user_id'), [])})


@dashboard_bp.route('/api/guide/crops', methods=['POST'])
def save_tracked_crops():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    payload = request.get_json() or {}
    plans = payload.get('plans', [])
    store = get_crop_tracking_store()
    existing = store.get(session.get('user_id'), [])
    existing.extend(plans)
    store[session.get('user_id')] = existing
    save_crop_tracking_store(store)
    return jsonify({'success': True, 'crops': existing})


@dashboard_bp.route('/api/guide/crops/<crop_id>', methods=['DELETE'])
def delete_tracked_crop(crop_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    store = get_crop_tracking_store()
    existing = store.get(session.get('user_id'), [])
    updated = [crop for crop in existing if crop.get('id') != crop_id]
    store[session.get('user_id')] = updated
    save_crop_tracking_store(store)
    return jsonify({'success': True, 'crops': updated})


@dashboard_bp.route('/api/guide/crops/<crop_id>/harvest', methods=['POST'])
def harvest_tracked_crop(crop_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    store = get_crop_tracking_store()
    crops = store.get(session.get('user_id'), [])
    for crop in crops:
        if crop.get('id') == crop_id:
            crop['status'] = 'harvested'
            crop['progress'] = 100
            break
    store[session.get('user_id')] = crops
    save_crop_tracking_store(store)
    return jsonify({'success': True, 'crops': crops})


@dashboard_bp.route('/api/dashboard/sales', methods=['GET'])
def get_sales_logs():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    store = get_sales_logs_store()
    user_id = session.get('user_id')
    return jsonify({'success': True, 'sales': store.get(user_id, [])})


@dashboard_bp.route('/api/dashboard/sales', methods=['POST'])
def save_sales_log():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    payload = request.get_json() or {}
    crop_name = (payload.get('crop_name') or '').strip()
    buyer_name = (payload.get('buyer_name') or '').strip()
    
    try:
        price_per_kg = float(payload.get('price_per_kg') or 0)
        quantity = float(payload.get('quantity') or 0)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid price or quantity.'}), 400
        
    if not crop_name or not buyer_name or price_per_kg <= 0 or quantity <= 0:
        return jsonify({'success': False, 'message': 'All fields are required and must be positive numbers.'}), 400
        
    user_id = session.get('user_id')
    store = get_sales_logs_store()
    user_sales = store.get(user_id, [])
    
    sale_entry = {
        'id': secrets.token_hex(6),
        'crop_name': crop_name,
        'buyer_name': buyer_name,
        'price_per_kg': price_per_kg,
        'quantity': quantity,
        'total_amount': round(price_per_kg * quantity, 2),
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    user_sales.append(sale_entry)
    store[user_id] = user_sales
    save_sales_logs_store(store)
    
    return jsonify({'success': True, 'sales': user_sales, 'new_sale': sale_entry})


@dashboard_bp.route('/api/guide/listings', methods=['GET'])
def get_guide_listings():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    listings = get_marketplace_store()
    user_id = session.get('user_id')
    my_listings = [item for item in listings if item.get('user_id') == user_id and item.get('status', 'active') == 'active']
    browse = [item for item in listings if item.get('status', 'active') == 'active']
    return jsonify({'success': True, 'my_listings': my_listings, 'browse_listings': browse})


@dashboard_bp.route('/api/guide/listings', methods=['POST'])
def create_guide_listing():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    payload = request.get_json() or {}
    item_name = (payload.get('item_name') or '').strip()
    crop_type = (payload.get('crop_type') or '').strip()
    phone = (payload.get('phone') or '').strip()
    price = str(payload.get('price') or '').strip()
    quantity = str(payload.get('quantity') or '').strip()
    location = (payload.get('location') or '').strip()
    listing_type = (payload.get('listing_type') or 'produce').strip()

    if not all([item_name, crop_type, phone, price]):
        return jsonify({'success': False, 'message': 'Item name, crop type, phone, and price are required.'}), 400
    if not phone.isdigit() or len(phone) != 10:
        return jsonify({'success': False, 'message': 'Phone number must be exactly 10 digits.'}), 400

    listings = get_marketplace_store()
    listing = {
        'id': secrets.token_hex(8),
        'user_id': session.get('user_id'),
        'seller_name': session.get('user_name', 'User'),
        'item_name': item_name,
        'crop_type': crop_type,
        'phone': phone,
        'price': float(price),
        'quantity': quantity,
        'location': location,
        'listing_type': listing_type,
        'status': 'active',
        'created_at': datetime.utcnow().isoformat()
    }
    listings.append(listing)
    save_marketplace_store(listings)
    return jsonify({'success': True, 'listing': listing})


@dashboard_bp.route('/api/guide/listings/<listing_id>', methods=['DELETE'])
def delete_guide_listing(listing_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    listings = get_marketplace_store()
    for listing in listings:
        if listing.get('id') == listing_id and listing.get('user_id') == session.get('user_id'):
            listing['status'] = 'deleted'
    save_marketplace_store(listings)
    return jsonify({'success': True})


@dashboard_bp.route('/api/reviews/submit', methods=['POST'])
def submit_review():
    if 'user_email' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    d = request.get_json() or {}
    rating = d.get('rating')
    review_text = (d.get('review') or '').strip()
    features = d.get('features', [])
    
    if not rating or not (1 <= rating <= 5):
        return jsonify({'success': False, 'message': 'Invalid rating'}), 400
    if not review_text:
        return jsonify({'success': False, 'message': 'Review text required'}), 400
    
    user_name = session.get('user_name', 'User')
    user_id = session.get('user_id', 'unknown')
    user_initial = user_name[0].upper() if user_name else 'U'
    features_str = '|'.join(features) if features else ''
    
    review_id = secrets.token_hex(8)
    review_entry = {
        'id': review_id,
        'user_id': user_id,
        'user_name': user_name,
        'user_initial': user_initial,
        'rating': str(rating),
        'review': review_text,
        'features': features_str,
        'created_at': datetime.utcnow().isoformat()
    }
    
    fields = ['id', 'user_id', 'user_name', 'user_initial', 'rating', 'review', 'features', 'created_at']
    with open(Config.REVIEWS_CSV, 'a', newline='', encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=fields).writerow(review_entry)
    
    return jsonify({'success': True, 'message': 'Review submitted!', 'review_id': review_id})


@dashboard_bp.route('/api/reviews')
def get_reviews():
    if not os.path.exists(Config.REVIEWS_CSV):
        return jsonify({'reviews': []})
    
    reviews = []
    fields = ['id', 'user_id', 'user_name', 'user_initial', 'rating', 'review', 'features', 'created_at']
    with open(Config.REVIEWS_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('id'):
                row['rating'] = int(row['rating']) if row['rating'].isdigit() else 0
                row['features'] = row['features'].split('|') if row['features'] else []
                reviews.append(row)
    
    reviews.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify({'reviews': reviews})


AGMARKNET_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

def get_fallback_prices(state, district, commodity=None):
    import random
    crops = [
        {"crop": "Wheat", "base_price": 2275},
        {"crop": "Paddy (Rice)", "base_price": 2183},
        {"crop": "Mustard", "base_price": 5450},
        {"crop": "Potato", "base_price": 1300},
        {"crop": "Onion", "base_price": 1900},
        {"crop": "Tomato", "base_price": 2200},
        {"crop": "Maize", "base_price": 1960},
        {"crop": "Cotton", "base_price": 6620},
        {"crop": "Moong Dal (Green Gram)", "base_price": 7200},
        {"crop": "Arhar Dal (Tur)", "base_price": 7000},
        {"crop": "Chana (Gram)", "base_price": 5335},
        {"crop": "Urad Dal (Black Gram)", "base_price": 6600},
        {"crop": "Masur Dal (Lentil)", "base_price": 6000},
        {"crop": "Sugarcane", "base_price": 315},
        {"crop": "Soyabean", "base_price": 4600},
        {"crop": "Groundnut", "base_price": 5850},
        {"crop": "Sunflower", "base_price": 6400},
        {"crop": "Garlic", "base_price": 8000},
        {"crop": "Ginger", "base_price": 9000},
        {"crop": "Chilli", "base_price": 7500},
        {"crop": "Apple", "base_price": 9500},
        {"crop": "Mango", "base_price": 6000},
        {"crop": "Banana", "base_price": 1800},
        {"crop": "Cauliflower", "base_price": 2000},
        {"crop": "Brinjal", "base_price": 1500},
        {"crop": "Pea", "base_price": 3500}
    ]
    
    seed_str = f"{state or ''}{district or ''}"
    random.seed(abs(hash(seed_str)))
    
    result = []
    mandis = [f"{district or state or 'Local'} Mandi", f"{district or state or 'Central'} APMC"]
    
    for mandi in mandis:
        # Choose 12-18 random crops
        num_crops = random.randint(12, 18)
        selected_crops = random.sample(crops, min(num_crops, len(crops)))
        for c in selected_crops:
            price_var = random.randint(-150, 150)
            price_quintal = c["base_price"] + price_var
            # Ensure sugarcane doesn't get divided incorrectly since its base is low
            if c["crop"] == "Sugarcane":
                price_quintal = max(280, c["base_price"] + random.randint(-20, 20))
            price_kg = round(price_quintal / 100, 2)
            
            result.append({
                "state": state or "Punjab",
                "district": district or state or "Amritsar",
                "mandi": mandi,
                "crop": c["crop"],
                "price_per_quintal": str(price_quintal),
                "price_per_kg": price_kg
            })
            
    if commodity:
        result = [r for r in result if commodity.lower() in r["crop"].lower()]
        
    return result


@dashboard_bp.route('/prices')
def get_prices():
    state = request.args.get('state')
    district = request.args.get('district')
    commodity = request.args.get('commodity')
    
    try:
        url = f"{AGMARKNET_URL}?api-key={AGMARKNET_KEY}&format=json&limit=100"
        if state:
            url += f"&filters[state]={state}"
        if district:
            url += f"&filters[district]={district}"
        if commodity:
            url += f"&filters[commodity]={commodity}"

        resp = requests.get(url, timeout=4)
        if resp.status_code != 200:
            raise Exception(f"API returned status code {resp.status_code}")
            
        data_json = resp.json()
        records = data_json.get("records", [])
        
        # If no records found, try uppercase filters as a fallback query
        if not records and state:
            url_upper = f"{AGMARKNET_URL}?api-key={AGMARKNET_KEY}&format=json&limit=100"
            url_upper += f"&filters[state]={state.upper()}"
            if district:
                url_upper += f"&filters[district]={district.upper()}"
            if commodity:
                url_upper += f"&filters[commodity]={commodity}"
                
            resp_upper = requests.get(url_upper, timeout=4)
            if resp_upper.status_code == 200:
                data_json = resp_upper.json()
                records = data_json.get("records", [])

        if not records:
            raise Exception("No records returned from data.gov.in API")

        result = []
        for item in records:
            try:
                price_quintal = float(item.get("modal_price", 0))
                price_kg = round(price_quintal / 100, 2)
            except Exception:
                price_kg = 0

            result.append({
                "state": item.get("state"),
                "district": item.get("district"),
                "mandi": item.get("market"),
                "crop": item.get("commodity"),
                "price_per_quintal": item.get("modal_price"),
                "price_per_kg": price_kg,
            })

        return jsonify(result)
    except Exception as e:
        print(f"[!] Agmarknet API error: {e}. Serving fallback mock prices.")
        fallback_data = get_fallback_prices(state, district, commodity)
        return jsonify(fallback_data)


@dashboard_bp.route('/api/weather')
def weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    if not lat or not lon:
        return jsonify({'error': 'lat and lon required'}), 400
    try:
        r = requests.get(
            f"http://api.weatherapi.com/v1/current.json?key={Config.WEATHER_API_KEY}&q={lat},{lon}",
            timeout=10)
        data = r.json()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    if 'error' in data:
        return jsonify({'error': data['error']['message']}), 400
    c = data['current']; loc = data['location']
    temp = c['temp_c']; hum = c['humidity']; wind = c['wind_kph']
    rain = c['precip_mm']; uv = c['uv']; vis = c['vis_km']
    feels = c.get('feelslike_c', temp)
    return jsonify({
        'location':   f"{loc['name']}, {loc['region']}, {loc['country']}",
        'condition':  c['condition']['text'],
        'temperature': temp, 'humidity': hum, 'wind_speed': wind,
        'rain': rain, 'uv_index': uv, 'visibility': vis,
        'feelslike': feels,
        'bars': {
            'temp':       min(100, max(0, round((temp + 10) / 60 * 100))),
            'feelslike':  min(100, max(0, round((feels + 10) / 60 * 100))),
            'humidity':   int(hum),
            'wind':       min(100, round(wind)),
            'rain':       min(100, round(rain / 50 * 100)),
            'uv':         min(100, round(uv / 12 * 100)),
            'visibility': min(100, round(vis / 20 * 100)),
        }
    })
