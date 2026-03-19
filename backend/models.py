from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    username      = db.Column(db.String(80),  nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    analyses = db.relationship(
        'Analysis', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    routines = db.relationship(
        'Routine', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id':         self.id,
            'email':      self.email,
            'username':   self.username,
            'created_at': self.created_at.isoformat(),
        }


class Analysis(db.Model):
    __tablename__ = 'analyses'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path      = db.Column(db.String(500), nullable=False)
    skin_type       = db.Column(db.String(50),  nullable=False)
    confidence      = db.Column(db.Float,       nullable=False)
    recommendations = db.Column(db.Text,        nullable=False)   # JSON string
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # ── Added in v2 ───────────────────────────────────────────────────────────
    normalized_image_b64      = db.Column(db.Text,  nullable=True)
    face_detection_confidence = db.Column(db.Float, nullable=True)

    # ── Added in v3 (concerns detection) ───────────────────────────────────────
    # JSON string: {"acne": 0.45, "dark_circles": 0.12, "redness": 0.78, ...}
    skin_concerns = db.Column(db.Text, nullable=True, default='{}')

    # Relationship
    concern_details = db.relationship(
        'SkinConcern', backref='analysis', lazy=True, cascade='all, delete-orphan'
    )

    def to_dict(self, include_image=True):
        data = {
            'id':                        self.id,
            'user_id':                   self.user_id,
            'image_path':                self.image_path,
            'skin_type':                 self.skin_type,
            'confidence':                self.confidence,
            'recommendations':           self.recommendations,
            'created_at':                self.created_at.isoformat(),
            'normalized_image_b64':      self.normalized_image_b64 if include_image else None,
            'face_detection_confidence': self.face_detection_confidence,
            'skin_concerns':             json.loads(self.skin_concerns) if self.skin_concerns else {},
        }
        return data


class SkinConcern(db.Model):
    """
    Detected skin concerns per analysis (acne, dark circles, redness, texture, hyperpigmentation).
    Each concern has a confidence score 0–1 and optional notes.
    """
    __tablename__ = 'skin_concerns'
    id              = db.Column(db.Integer, primary_key=True)
    analysis_id     = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=False)
    concern_type    = db.Column(db.String(50), nullable=False)  # 'acne', 'dark_circles', 'redness', 'texture', 'hyperpigmentation'
    confidence      = db.Column(db.Float, nullable=False)  # 0–1
    severity        = db.Column(db.String(20), nullable=True)  # 'mild', 'moderate', 'severe'
    notes               = db.Column(db.Text, nullable=True)
    annotated_image_b64 = db.Column(db.Text, default='')   # zone highlight image
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                   self.id,
            'analysis_id':          self.analysis_id,
            'concern_type':         self.concern_type,
            'confidence':           self.confidence,
            'severity':             self.severity,
            'notes':                self.notes,
            'annotated_image_b64':  self.annotated_image_b64 or '',
            'created_at':           self.created_at.isoformat(),
        }


class ProductRecommendation(db.Model):
    """
    Curated product database: skin type + concern combinations → product suggestions + ingredient lists.
    """
    __tablename__ = 'product_recommendations'
    id              = db.Column(db.Integer, primary_key=True)
    product_name    = db.Column(db.String(200), nullable=False)
    brand           = db.Column(db.String(100), nullable=False)
    skin_types      = db.Column(db.String(200), nullable=False)  # CSV: 'oily,combination,normal'
    concerns        = db.Column(db.String(300), nullable=False)  # CSV: 'acne,redness,texture'
    key_ingredients = db.Column(db.Text, nullable=False)  # CSV or JSON array
    description     = db.Column(db.Text, nullable=True)
    price_range     = db.Column(db.String(50), nullable=True)  # 'budget', 'mid', 'premium'
    url             = db.Column(db.String(500), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':               self.id,
            'product_name':     self.product_name,
            'brand':            self.brand,
            'skin_types':       [s.strip() for s in self.skin_types.split(',')],
            'concerns':         [c.strip() for c in self.concerns.split(',')],
            'key_ingredients':  [i.strip() for i in self.key_ingredients.split(',')],
            'description':      self.description,
            'price_range':      self.price_range,
            'url':              self.url,
            'created_at':       self.created_at.isoformat(),
        }


class Routine(db.Model):
    """
    Saved skincare routine: user's morning/night routine with steps, generated or edited.
    """
    __tablename__ = 'routines'
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    routine_type    = db.Column(db.String(20), nullable=False)  # 'morning' or 'night'
    name            = db.Column(db.String(200), nullable=False)  # e.g., "Summer Oily Skin Routine"
    based_on_scan   = db.Column(db.Integer, db.ForeignKey('analyses.id'), nullable=True)  # Which analysis prompted this
    description     = db.Column(db.Text, nullable=True)
    is_active       = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    steps = db.relationship(
        'RoutineStep', backref='routine', lazy=True, cascade='all, delete-orphan'
    )

    def to_dict(self, include_steps=True):
        data = {
            'id':             self.id,
            'user_id':        self.user_id,
            'routine_type':   self.routine_type,
            'name':           self.name,
            'based_on_scan':  self.based_on_scan,
            'description':    self.description,
            'is_active':      self.is_active,
            'created_at':     self.created_at.isoformat(),
            'updated_at':     self.updated_at.isoformat(),
        }
        if include_steps:
            data['steps'] = [step.to_dict() for step in self.steps]
        return data


class RoutineStep(db.Model):
    """
    Individual step in a routine: e.g., "Apply cleanser", "Wait 2 min", "Rinse with water".
    """
    __tablename__ = 'routine_steps'
    id              = db.Column(db.Integer, primary_key=True)
    routine_id      = db.Column(db.Integer, db.ForeignKey('routines.id'), nullable=False)
    order           = db.Column(db.Integer, nullable=False)  # 1, 2, 3, ...
    product_type    = db.Column(db.String(100), nullable=False)  # e.g., 'cleanser', 'toner', 'serum', 'moisturizer'
    instruction     = db.Column(db.Text, nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=True)  # e.g., 120 for "wait 2 minutes"
    key_ingredient  = db.Column(db.String(200), nullable=True)  # e.g., 'salicylic acid', 'retinol'
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                self.id,
            'routine_id':        self.routine_id,
            'order':             self.order,
            'product_type':      self.product_type,
            'instruction':       self.instruction,
            'duration_seconds':  self.duration_seconds,
            'key_ingredient':    self.key_ingredient,
            'created_at':        self.created_at.isoformat(),
        }