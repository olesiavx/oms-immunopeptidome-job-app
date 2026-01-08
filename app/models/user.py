
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from ..extensions import db, login_manager

class Role:
    ADMIN = "admin"
    ANALYST = "analyst"
    REQUESTER = "requester"

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)

    role = db.Column(db.String(32), nullable=False, default=Role.REQUESTER)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_analyst(self) -> bool:
        return self.role in (Role.ADMIN, Role.ANALYST)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"