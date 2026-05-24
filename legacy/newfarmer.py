"""
AgroSense Smart Farming Dashboard — Python Flask Backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import uuid
import math


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

USE_MONGODB = False

if USE_MONGODB:
    from pymongo import MongoClient
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/agrosense')
    client = MongoClient(MONGODB_URI)
    db = client['agrosense']
    crop_plans_col = db['crop_plans']
    listings_col = db['marketplace_listings']
else:
    DATA_FILE = 'data.json'
    def load_data():
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except:
            return {'crop_plans': [], 'listings': [], 'analyses': []}
    
    def save_data(data):
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)

CROPS_DB = {
    "wheat": {
        "id": "wheat", "name": "Wheat", "emoji": "🌾", "season": "Rabi",
        "soilTypes": ["loamy", "clay loam"], "waterNeed": "Moderate",
        "duration": "120-150 days", "riskLevel": "low",
        "profitRange": "₹18,000–₹28,000/acre",
        "suitScore": 92, "costPerAcre": 15000, "yieldPerAcre": 18, "pricePerKg": 22,
    },
    "rice": {
        "id": "rice", "name": "Rice", "emoji": "🍚", "season": "Kharif",
        "soilTypes": ["clay", "alluvial"], "waterNeed": "High",
        "duration": "90-120 days", "riskLevel": "medium",
        "profitRange": "₹20,000–₹35,000/acre",
        "suitScore": 78, "costPerAcre": 18000, "yieldPerAcre": 22, "pricePerKg": 24,
    },
    "mustard": {
        "id": "mustard", "name": "Mustard", "emoji": "🟡", "season": "Rabi",
        "soilTypes": ["sandy loam", "loamy"], "waterNeed": "Low",
        "duration": "90-110 days", "riskLevel": "low",
        "profitRange": "₹15,000–₹22,000/acre",
        "suitScore": 85, "costPerAcre": 9000, "yieldPerAcre": 10, "pricePerKg": 55,
    },
    "potato": {
        "id": "potato", "name": "Potato", "emoji": "🥔", "season": "Rabi",
        "soilTypes": ["sandy loam", "loamy"], "waterNeed": "Moderate",
        "duration": "75-100 days", "riskLevel": "medium",
        "profitRange": "₹25,000–₹45,000/acre",
        "suitScore": 80, "costPerAcre": 25000, "yieldPerAcre": 100, "pricePerKg": 10,
    },
    "maize": {
        "id": "maize", "name": "Maize", "emoji": "🌽", "season": "Kharif",
        "soilTypes": ["sandy loam", "loamy", "alluvial"], "waterNeed": "Moderate",
        "duration": "80-95 days", "riskLevel": "low",
        "profitRange": "₹16,000–₹26,000/acre",
        "suitScore": 88, "costPerAcre": 12000, "yieldPerAcre": 25, "pricePerKg": 20,
    },
}

SEASON_MONTHS = {
    "Kharif": [6, 7, 8, 9, 10],
    "Rabi": [10, 11, 12, 1, 2, 3],
    "Zaid": [3, 4, 5, 6]
}

SOIL_MAP = {
    "Uttar Pradesh": "Alluvial / Loamy",
    "Punjab": "Loamy",
    "Haryana": "Sandy Loam",
    "Maharashtra": "Black Cotton Soil",
    "Karnataka": "Red Laterite",
    "Rajasthan": "Sandy",
    "West Bengal": "Alluvial",
    "Madhya Pradesh": "Black / Loamy",
}


def get_season():
    month = datetime.now().month
    for season, months in SEASON_MONTHS.items():
        if month in months:
            return season
    return "Rabi"

def calculate_feasibility(crop_id, area, plan_inputs):
    crop = CROPS_DB.get(crop_id)
    if not crop:
        return None
    total_cost = crop['costPerAcre'] * area
    total_yield_kg = crop['yieldPerAcre'] * area * 1000
    total_revenue = total_yield_kg * crop['pricePerKg']
    profit = total_revenue - total_cost
    break_even_kg = total_cost / crop['pricePerKg'] if crop['pricePerKg'] > 0 else 0
    roi = (profit / total_cost * 100) if total_cost > 0 else 0
    return {
        "cropId": crop_id,
        "cropName": crop['name'],
        "area": round(area, 1),
        "totalCost": round(total_cost),
        "totalYieldKg": round(total_yield_kg),
        "totalRevenue": round(total_revenue),
        "profit": round(profit),
        "breakEvenKg": round(break_even_kg),
        "roi": round(roi, 1),
        "riskLevel": crop['riskLevel'],
        "duration": crop['duration'],
    }

@app.route('/api/location/season', methods=['GET'])
def get_location_season():
    season = get_season()
    month = datetime.now().month
    return jsonify({
        "season": season,
        "month": month,
        "description": f"Currently in {season} season"
    })

@app.route('/api/location/reverse-geocode', methods=['POST'])
def reverse_geocode():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    
    return jsonify({
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Mathura",
        "lat": lat, "lon": lon
    })


@app.route('/api/weather', methods=['GET'])
def get_weather():
    
    lat = request.args.get('lat', 27.5)
    lon = request.args.get('lon', 77.6)
    
   

    # MOCK weather
    return jsonify({
        "temperature": 26.4,
        "windspeed": 12,
        "weathercode": 1,
        "description": "Partly Cloudy",
        "humidity": 65,
        "rainfall_chance": 20
    })


@app.route('/api/crops/recommend', methods=['POST'])
def recommend_crops():
    """Get crop recommendations based on location and season"""
    data = request.json
    state_name = data.get('state', '')
    season = data.get('season') or get_season()
    soil_type = SOIL_MAP.get(state_name, 'Loamy').lower()
    
    recommendations = []
    for crop_id, crop in CROPS_DB.items():
        # Calculate suitability score
        score = crop['suitScore']
        # Boost score for season match
        if crop['season'] == season:
            score = min(100, score + 10)
        else:
            score = max(10, score - 20)
        # Soil compatibility check
        soil_match = any(s.lower() in soil_type for s in crop['soilTypes'])
        if soil_match:
            score = min(100, score + 5)
        recommendations.append({
            **crop,
            'calculatedSuitScore': score,
            'seasonMatch': crop['season'] == season,
            'soilMatch': soil_match,
        })
    
    recommendations.sort(key=lambda x: x['calculatedSuitScore'], reverse=True)
    return jsonify({"crops": recommendations, "season": season, "soilType": soil_type})

@app.route('/api/crops/feasibility', methods=['POST'])
def get_feasibility():
    """Calculate feasibility for selected crops"""
    data = request.json
    crop_ids = data.get('cropIds', [])
    area = float(data.get('area', 1))
    plan_inputs = data.get('planInputs', {})
    
    results = []
    for crop_id in crop_ids:
        result = calculate_feasibility(crop_id, area, plan_inputs)
        if result:
            results.append(result)
    
    # Mark best options
    if results:
        best_profit = max(results, key=lambda x: x['profit'])
        lowest_cost = min(results, key=lambda x: x['totalCost'])
        best_profit['isBestProfit'] = True
        lowest_cost['isBudgetFriendly'] = True
    
    return jsonify({"feasibility": results})


@app.route('/api/crop-plans', methods=['POST'])
def create_crop_plan():
    """Create a new crop plan (save to DB)"""
    data = request.json
    plans = data.get('plans', [])
    
    if USE_MONGODB:
        for plan in plans:
            plan['_id'] = str(uuid.uuid4())
            crop_plans_col.insert_one(plan)
        return jsonify({"success": True, "count": len(plans)})
    else:
        db_data = load_data()
        for plan in plans:
            plan['id'] = str(uuid.uuid4())
            plan['createdAt'] = datetime.now().isoformat()
            db_data['crop_plans'].append(plan)
        save_data(db_data)
        return jsonify({"success": True, "plans": plans})

@app.route('/api/crop-plans', methods=['GET'])
def get_crop_plans():
    """Get all crop plans"""
    if USE_MONGODB:
        plans = list(crop_plans_col.find({}, {'_id': 0}))
    else:
        db_data = load_data()
        plans = db_data.get('crop_plans', [])
    
    # Add computed progress
    for plan in plans:
        start = datetime.fromisoformat(plan.get('startDate', datetime.now().isoformat()))
        harvest = datetime.fromisoformat(plan.get('harvestDate', (datetime.now() + timedelta(days=120)).isoformat()))
        now = datetime.now()
        total_days = max(1, (harvest - start).days)
        elapsed = max(0, (now - start).days)
        plan['progress'] = min(100, round(elapsed / total_days * 100))
        plan['daysLeft'] = max(0, (harvest - now).days)
    
    return jsonify({"plans": plans})

@app.route('/api/crop-plans/<plan_id>', methods=['GET'])
def get_crop_plan(plan_id):
    """Get a specific crop plan by ID"""
    if USE_MONGODB:
        plan = crop_plans_col.find_one({'id': plan_id}, {'_id': 0})
    else:
        db_data = load_data()
        plan = next((p for p in db_data['crop_plans'] if p.get('id') == plan_id), None)
    
    if not plan:
        return jsonify({"error": "Crop plan not found"}), 404
    return jsonify(plan)

@app.route('/api/crop-plans/<plan_id>/harvest', methods=['PUT'])
def update_harvest(plan_id):
    """Mark a crop plan as harvested"""
    data = request.json
    harvest_method = data.get('method', 'manual')
    
    if USE_MONGODB:
        crop_plans_col.update_one(
            {'id': plan_id},
            {'$set': {'status': 'harvested', 'harvestMethod': harvest_method, 'harvestedAt': datetime.now().isoformat()}}
        )
    else:
        db_data = load_data()
        for plan in db_data['crop_plans']:
            if plan.get('id') == plan_id:
                plan['status'] = 'harvested'
                plan['harvestMethod'] = harvest_method
                plan['harvestedAt'] = datetime.now().isoformat()
                break
        save_data(db_data)
    
    return jsonify({"success": True, "planId": plan_id, "method": harvest_method})


@app.route('/api/marketplace/listings', methods=['POST'])
def create_listing():
    """Create a new marketplace listing"""
    data = request.json
    listing = {
        'id': str(uuid.uuid4()),
        'crop': data.get('crop'),
        'emoji': data.get('emoji', '🌾'),
        'qty': data.get('qty'),
        'price': float(data.get('price', 0)),
        'loc': data.get('loc'),
        'contact': data.get('contact'),
        'seller': data.get('seller', 'Farmer'),
        'listed': datetime.now().isoformat().split('T')[0],
        'status': 'active'
    }
    
    if USE_MONGODB:
        listings_col.insert_one({**listing, '_id': listing['id']})
    else:
        db_data = load_data()
        db_data['listings'].append(listing)
        save_data(db_data)
    
    return jsonify({"success": True, "listing": listing}), 201

@app.route('/api/marketplace/listings', methods=['GET'])
def get_listings():
    """Get all marketplace listings"""
    if USE_MONGODB:
        listings = list(listings_col.find({'status': 'active'}, {'_id': 0}))
    else:
        db_data = load_data()
        listings = db_data.get('listings', [])
    
    return jsonify({"listings": listings})


@app.route('/api/analyze-crop', methods=['POST'])
def analyze_crop():
    
    files = request.files.getlist('images')
    
    if not files:
        return jsonify({"error": "No images provided"}), 400
    
 
    return jsonify({
        "status": "completed",
        "imageCount": len(files),
        "results": {
            "overallHealth": "moderate",
            "healthScore": 72,
            "diseases": [],
            "nutrientDeficiency": "Nitrogen deficiency suspected - leaves showing yellowing",
            "waterStress": "low",
            "pestActivity": "none detected",
            "recommendation": "Apply 10kg/acre Urea fertilizer. Monitor for 7 days.",
            "nextInspection": (datetime.now() + timedelta(days=14)).isoformat().split('T')[0]
        }
    })


@app.route('/api/market-prices', methods=['GET'])
def get_market_prices():
    
    crop = request.args.get('crop', 'Wheat')
    state_ = request.args.get('state', 'Uttar Pradesh')
    
    
    mock_prices = {
        "Wheat": {"minPrice": 2015, "maxPrice": 2200, "modalPrice": 2150, "unit": "quintal"},
        "Rice": {"minPrice": 1940, "maxPrice": 2100, "modalPrice": 2020, "unit": "quintal"},
        "Mustard": {"minPrice": 5000, "maxPrice": 5800, "modalPrice": 5400, "unit": "quintal"},
        "Potato": {"minPrice": 800, "maxPrice": 1500, "modalPrice": 1100, "unit": "quintal"},
        "Maize": {"minPrice": 1700, "maxPrice": 2000, "modalPrice": 1850, "unit": "quintal"},
    }
    price_data = mock_prices.get(crop, {"minPrice": 1800, "maxPrice": 2200, "modalPrice": 2000, "unit": "quintal"})
    return jsonify({"crop": crop, "state": state_, **price_data})


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "AgroSense API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🌱 AgroSense Smart Farming Backend Starting...")
    print("=" * 60)
    print(f"📡 API running at: http://localhost:5000")
    print(f"🔧 Mode: {'MongoDB' if USE_MONGODB else 'JSON File Storage'}")
    print()
    print("⚠️  APIs to connect (see README):")
    print("   1. Weather: Open-Meteo (FREE, no key needed)")
    print("   2. Geocoding: Nominatim (FREE, no key needed)")
    print("   3. Crop Prices: Agmarknet API (FREE, data.gov.in key)")
    print("   4. Disease AI: Plant.id or OpenAI GPT-4V (paid)")
    print()
    app.run(debug=True, port=5000)
