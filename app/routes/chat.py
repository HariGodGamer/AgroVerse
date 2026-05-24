import requests
from flask import Blueprint, request, jsonify, session, redirect, render_template
from app.config import Config

chat_bp = Blueprint('chat', __name__)

WORQHAT_API_URL = "https://api.worqhat.com/api/ai/content/v4"

SYSTEM_PROMPT = """You are AgroBot, an expert AI farming assistant for AgroVerse — India's smart farming platform.

Your expertise covers:
- Indian crop varieties, seasons (Kharif, Rabi, Zaid), and best practices
- Crop disease identification, prevention, and organic/chemical treatments
- Soil health, fertilizers, irrigation methods, and water management
- Weather-based farming decisions and climate-smart agriculture
- Market prices (mandi rates), MSP, and best time to sell crops
- Government schemes (PM-KISAN, PMFBY, KCC, etc.) and subsidies
- Farm machinery, modern farming techniques, and precision agriculture
- Pest management, integrated pest management (IPM)
- Post-harvest handling, storage, and value addition

Guidelines:
- Be concise but thorough. Use bullet points for lists.
- Give practical, actionable advice that Indian farmers can use immediately.
- When discussing crops, mention relevant Indian states/regions.
- Mention government schemes when relevant.
- If asked about something outside farming/agriculture, politely redirect.
- Be respectful and use simple language. You may use common Hindi farming terms.
- Always end with a helpful follow-up suggestion when appropriate."""


@chat_bp.route('/chat')
def chat_page():
    if 'user_email' not in session:
        return redirect('/signin')
    return render_template('chat.html')


@chat_bp.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    message = (data.get('q') or data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'No message provided'}), 400

    # Build conversation history for context
    history = data.get('history', [])
    
    # Build the question with conversation context
    conversation_context = ""
    if history:
        # Include last few messages for context
        recent = history[-8:]  # Last 8 messages for context
        for msg in recent:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'user':
                conversation_context += f"User: {content}\n"
            elif role in ('assistant', 'bot'):
                conversation_context += f"AgroBot: {content}\n"
    
    # Build the full question
    if conversation_context:
        full_question = f"Previous conversation:\n{conversation_context}\nUser's latest message: {message}"
    else:
        full_question = message

    try:
        response = requests.post(
            WORQHAT_API_URL,
            headers={
                'Authorization': f'Bearer {Config.WORQHAT_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'question': full_question,
                'model': 'aicon-v4-nano-160824',
                'randomness': 0.4,
                'stream_data': False,
                'training_data': SYSTEM_PROMPT,
                'response_type': 'text'
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"WorqHat API returned status {response.status_code}")
        
        result = response.json()
        
        # WorqHat returns content in 'content' field
        reply = result.get('content', '')
        
        if not reply:
            # Try alternative response fields
            reply = result.get('response', '') or result.get('text', '') or result.get('message', '')
        
        if not reply:
            raise Exception(f"Empty response from WorqHat API: {result}")
            
        return jsonify({'reply': reply})
        
    except requests.exceptions.Timeout:
        return jsonify({'reply': 'AgroBot is taking longer than usual. Please try again in a moment.'})
    except Exception as e:
        print(f"[!] WorqHat AI error: {e}")
        # Fallback to basic responses if API fails
        return jsonify({'reply': get_fallback_reply(message)})


def get_fallback_reply(message):
    """Basic fallback responses when AI API is unavailable."""
    lower = message.lower()
    
    if any(w in lower for w in ['weather', 'rain', 'temperature', 'climate']):
        return '🌦️ Check the Weather section on your dashboard for real-time weather data. For irrigation, water early morning or late evening to reduce evaporation.'
    
    if any(w in lower for w in ['disease', 'pest', 'blight', 'wilt', 'fungus', 'insect']):
        return '🔬 Use our Disease Detection feature — upload a photo of the affected crop leaf and get instant AI diagnosis with treatment recommendations. Go to Dashboard → Disease Detection.'
    
    if any(w in lower for w in ['crop', 'seed', 'plant', 'grow', 'kharif', 'rabi']):
        return '🌾 For crop recommendations based on your soil type, region, and season, check the New Farmer Guide on your dashboard. It provides step-by-step planting guides for all major Indian crops.'
    
    if any(w in lower for w in ['fertilizer', 'manure', 'urea', 'dap', 'npk']):
        return '🧪 Always get a soil test before applying fertilizers. Contact your nearest Krishi Vigyan Kendra (KVK) for free soil testing. Balance NPK based on your crop needs.'
    
    if any(w in lower for w in ['sell', 'price', 'market', 'mandi', 'msp']):
        return '📊 Check real-time mandi prices on our Market Data page. Compare prices across different mandis in your state before selling. Also check if your crop has an MSP (Minimum Support Price).'
    
    if any(w in lower for w in ['scheme', 'subsidy', 'government', 'pm-kisan', 'pmfby', 'loan', 'kcc']):
        return '🏛️ Key schemes for farmers: PM-KISAN (₹6000/year), PMFBY (crop insurance), KCC (Kisan Credit Card for loans at 4%). Visit your nearest CSC or bank for registration.'
    
    if any(w in lower for w in ['machinery', 'tractor', 'equipment', 'rent', 'hire']):
        return '🚜 Browse our Machinery Rental section to find tractors, harvesters, and farm equipment from verified local providers at affordable rates.'
    
    if any(w in lower for w in ['hello', 'hi', 'namaste', 'hey']):
        return '🙏 Namaste! I\'m AgroBot, your AI farming assistant. I can help with crops, diseases, weather planning, market prices, and government schemes. What would you like to know?'
    
    return f'🌿 I can help with crops, diseases, weather, market prices, government schemes, and farming tips. Could you tell me more about what specific farming topic you need help with?'
