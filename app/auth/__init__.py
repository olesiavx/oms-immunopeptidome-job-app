from flask import Blueprint
from wtforms.validators import DataRequired, Email, Length, EqualTo

auth_bp = Blueprint("auth", __name__)

from . import routes 