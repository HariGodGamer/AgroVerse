import os
from flask import Blueprint, request, jsonify, session, redirect, render_template
from app.config import Config
import app.utils.disease_model as disease_helper

disease_bp = Blueprint('disease', __name__)

@disease_bp.route('/disease')
def disease_page():
    if 'user_email' not in session:
        return redirect('/signin')
    return render_template('disease.html')

@disease_bp.route('/api/disease/predict', methods=['POST'])
def disease_predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    if disease_helper.DISEASE_CLASSES is None:
        return jsonify({'error': 'Disease detection model classes not loaded'}), 503
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    try:
        os.makedirs(Config.DISEASE_UPLOAD_DIR, exist_ok=True)
        img_path = os.path.join(Config.DISEASE_UPLOAD_DIR, file.filename)
        file.save(img_path)
        
        from PIL import Image
        img = Image.open(img_path).convert('RGB')
        img = disease_helper.remove_background(img)
        
        label, confidence = disease_helper.predict(img)
        is_healthy = 'healthy' in label.lower()
        
        return jsonify({
            'label': label,
            'confidence': confidence,
            'is_healthy': is_healthy,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'img_path' in locals() and os.path.exists(img_path):
            os.remove(img_path)
