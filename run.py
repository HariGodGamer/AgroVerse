import os
import sys

# Ensure the project root directory is in the sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, load_disease_model

app = create_app()

if __name__ == '__main__':
    # Load model and run the development server
    load_disease_model()
    print("AgroVerse running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
# Reloader trigger to reload india_data.json v2
