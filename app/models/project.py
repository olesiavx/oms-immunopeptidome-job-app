from datetime import datetime
from ..extensions import db

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False, index=True)

    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    partners_text = db.Column(db.Text, nullable=True)

    short_description = db.Column(db.Text, nullable=True)

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Project {self.id} {self.name}>"