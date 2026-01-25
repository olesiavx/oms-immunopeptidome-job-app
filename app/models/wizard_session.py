from datetime import datetime
from app.extensions import db

class WizardSession(db.Model):
    __tablename__ = "wizard_sessions"

    id = db.Column(db.Integer, primary_key=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    path = db.Column(db.JSON, default=list, nullable=False)

    profile = db.Column(db.String(128), nullable=True)

    inputs = db.Column(db.JSON, default=dict, nullable=False)

    status = db.Column(db.String(32), default="draft", nullable=False)