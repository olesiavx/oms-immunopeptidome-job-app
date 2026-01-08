from flask import render_template
from flask_login import current_user
from . import main_bp
from flask import render_template, abort
from flask_login import login_required
from ..models import Project

@main_bp.get("/")
def index():
    return render_template("main/index.html", user=current_user)

@main_bp.get("/projects/<int:project_id>")
@login_required
def project_detail(project_id: int):
    project = Project.query.get(project_id)
    if not project:
        abort(404)

    from ..models import Job
    jobs = Job.query.filter_by(project_id=project.id).order_by(Job.created_at.desc()).all()

    return render_template("main/project_detail.html", project=project, jobs=jobs)