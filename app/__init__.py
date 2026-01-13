import os
from flask import Flask
from .extensions import db, login_manager, migrate
from .forms import CSRFOnlyForm

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///oms_job_app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    @app.context_processor
    def inject_global_forms():
        return {
            "logout_form": CSRFOnlyForm(),
            "csrf_form": CSRFOnlyForm(),
        }

    from .main import main_bp
    from .auth import auth_bp
    from .jobs import jobs_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")

    return app