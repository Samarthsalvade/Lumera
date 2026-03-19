from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from models import db, Analysis, User, SkinConcern
from services.ml_service import analyze_skin, get_analyzer
from utils.helpers import allowed_file
import os, json, time, cloudinary, cloudinary.uploader
from flask import current_app

analysis_bp = Blueprint('analysis', __name__)


def _init_cloudinary():
    cloudinary.config(
        cloud_name = current_app.config['CLOUDINARY_CLOUD_NAME'],
        api_key    = current_app.config['CLOUDINARY_API_KEY'],
        api_secret = current_app.config['CLOUDINARY_API_SECRET'],
        secure     = True,
    )


@analysis_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_image():
    try:
        print("=" * 50)
        print("UPLOAD REQUEST RECEIVED")

        user_id = int(get_jwt_identity())
        user    = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # ── Save temporarily for ML processing ───────────────────────────────
        filename      = secure_filename(f"{user_id}_{int(time.time())}_{file.filename}")
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # ── Run ML analysis FIRST (needs local file) ─────────────────────────
        result = analyze_skin(filepath)

        # ── Upload to Cloudinary ──────────────────────────────────────────────
        _init_cloudinary()
        cloudinary_response = cloudinary.uploader.upload(
            filepath,
            folder        = 'lumera/uploads',
            public_id     = filename.rsplit('.', 1)[0],
            resource_type = 'image',
        )
        image_url = cloudinary_response['secure_url']
        print(f"Uploaded to Cloudinary: {image_url}")

        # ── Clean up local temp file ──────────────────────────────────────────
        try:
            os.remove(filepath)
        except Exception:
            pass

        if not result.get('face_found', True):
            return jsonify({'success': False, 'face_found': False,
                            'message': result.get('message', 'No face detected.')}), 200

        # ── Detect skin concerns ──────────────────────────────────────────────
        detector            = None
        concerns_dict       = {}
        ai_recs             = {}
        concern_annotations = {}

        if result.get('analysis_image') is not None:
            try:
                from skin_concern_detector import (
                    SkinConcernDetector,
                    get_ai_recommendations,
                    generate_all_concern_annotations,
                )
                detector      = SkinConcernDetector()
                concerns_dict = detector.detect_concerns(result['analysis_image'])
                ai_recs       = get_ai_recommendations(
                    skin_type=result['skin_type'],
                    concerns=concerns_dict,
                )
                concern_annotations = generate_all_concern_annotations(
                    result['analysis_image'],
                    concerns_dict,
                    detector,
                    output_size=300,
                )
                print(f"Annotations generated for: {list(concern_annotations.keys())}")
            except Exception as e:
                print(f"Concern detection failed: {e}")
                import traceback; traceback.print_exc()

        # ── Regenerate recommendations with concern context ───────────────────
        if concerns_dict:
            try:
                final_recs = get_analyzer()._get_recommendations(
                    skin_type  = result['skin_type'],
                    confidence = result['confidence'],
                    concerns   = concerns_dict,
                )
            except Exception:
                final_recs = result['recommendations']
        else:
            final_recs = result['recommendations']

        # ── Save analysis — store Cloudinary URL as image_path ────────────────
        analysis = Analysis(
            user_id                   = user_id,
            image_path                = image_url,
            skin_type                 = result['skin_type'],
            confidence                = result['confidence'],
            recommendations           = json.dumps(final_recs),
            normalized_image_b64      = result.get('normalized_image_b64'),
            face_detection_confidence = result.get('face_detection_confidence'),
            skin_concerns             = json.dumps(concerns_dict),
        )
        db.session.add(analysis)
        db.session.flush()

        # ── Save concern rows ─────────────────────────────────────────────────
        concern_rows = []
        if concerns_dict and detector is not None:
            try:
                for ctype, conf in concerns_dict.items():
                    if conf > 0.10:
                        sev   = detector.classify_severity(ctype, conf)
                        notes = ai_recs.get(ctype) or \
                                detector.get_recommendation_for_concern(ctype, sev)
                        sc = SkinConcern(
                            analysis_id         = analysis.id,
                            concern_type        = ctype,
                            confidence          = conf,
                            severity            = sev,
                            notes               = notes,
                            annotated_image_b64 = concern_annotations.get(ctype, ''),
                        )
                        db.session.add(sc)
                        concern_rows.append(sc)
            except Exception as e:
                print(f"Saving concerns failed: {e}")
                import traceback; traceback.print_exc()

        db.session.commit()
        print(f"Analysis saved — {result['skin_type']} ({result['confidence']}%)")

        return jsonify({
            'success':  True,
            'message':  'Analysis completed successfully',
            'analysis': analysis.to_dict(),
            'concerns': [c.to_dict() for c in concern_rows],
            'products': [],
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Upload error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/history', methods=['GET'])
@jwt_required()
def get_analysis_history():
    try:
        user_id  = int(get_jwt_identity())
        analyses = (Analysis.query.filter_by(user_id=user_id)
                    .order_by(Analysis.created_at.desc()).all())
        return jsonify({
            'analyses': [
                {k: v for k, v in a.to_dict().items() if k != 'normalized_image_b64'}
                for a in analyses
            ]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/result/<int:analysis_id>', methods=['GET'])
@jwt_required()
def get_analysis_result(analysis_id):
    try:
        user_id  = int(get_jwt_identity())
        analysis = Analysis.query.filter_by(id=analysis_id, user_id=user_id).first()
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404

        concerns = SkinConcern.query.filter_by(analysis_id=analysis_id).all()

        return jsonify({
            'analysis': analysis.to_dict(),
            'concerns': [c.to_dict() for c in concerns],
            'products': [],
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analysis_bp.route('/uploads/<path:filename>', methods=['GET'])
@jwt_required()
def get_uploaded_image(filename):
    # Images are now on Cloudinary — this endpoint is kept for
    # backwards compatibility but just returns a 404 with a helpful message
    return jsonify({
        'error': 'Images are now served directly from Cloudinary. Use the image_path URL from the analysis object.'
    }), 404
