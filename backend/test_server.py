#test_server.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
from services.ml_service import analyze_skin
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'test_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# In-memory storage (resets on restart)
analyses = []
analysis_id_counter = 1

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Test server running'}), 200

@app.route('/api/analysis/upload', methods=['POST', 'OPTIONS'])
def upload():
    if request.method == 'OPTIONS':
        return '', 200
    
    global analysis_id_counter
    
    try:
        print("\n" + "=" * 60)
        print("📤 IMAGE UPLOAD REQUEST")
        print("=" * 60)
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Save file
        filename = secure_filename(f"test_{analysis_id_counter}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        print(f"✓ File saved: {filepath}")
        
        # Run analysis
        print("🔍 Running ML analysis...")
        result = analyze_skin(filepath)

        # ── Face not detected — return early with warning ──────────
        if not result.get('face_found', True):
            return jsonify({
                'success': False,
                'face_found': False,
                'message': result['message'],
            }), 200

        print(f"✓ Analysis complete: {result['skin_type']} ({result['confidence']}%)")

        # Store result — ADD normalized_image_b64 and face_detection_confidence
        analysis = {
            'id': analysis_id_counter,
            'image_path': filename,
            'skin_type': result['skin_type'],
            'confidence': result['confidence'],
            'recommendations': json.dumps(result['recommendations']),
            'normalized_image_b64': result.get('normalized_image_b64'),
            'face_detection_confidence': result.get('face_detection_confidence', 0),
            'message': result.get('message', ''),
            'created_at': datetime.utcnow().isoformat()
        }
        analyses.append(analysis)
        analysis_id_counter += 1
        
        print("=" * 60 + "\n")
        
        return jsonify({
            'success': True,
            'message': 'Analysis completed',
            'analysis': analysis
        }), 201
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/history', methods=['GET'])
def history():
    return jsonify({'analyses': analyses}), 200

@app.route('/api/analysis/result/<int:analysis_id>', methods=['GET'])
def get_result(analysis_id):
    analysis = next((a for a in analyses if a['id'] == analysis_id), None)
    if not analysis:
        return jsonify({'error': 'Analysis not found'}), 404
    return jsonify({'analysis': analysis}), 200

@app.route('/api/analysis/uploads/<filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🧪 TEST SERVER - NO AUTHENTICATION")
    print("=" * 60)
    print("Upload endpoint: http://localhost:3001/api/analysis/upload")
    print("History endpoint: http://localhost:3001/api/analysis/history")
    print("Health check: http://localhost:3001/api/health")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=3001)