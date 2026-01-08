from datetime import datetime
from ..extensions import db

class JobStatus:
    SUBMITTED = "SUBMITTED"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_ON_DATA = "WAITING_ON_DATA"
    QC = "QC"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

    ALL = [
        SUBMITTED, TRIAGED, IN_PROGRESS, WAITING_ON_DATA, QC, COMPLETED, ARCHIVED
    ]

class JobPriority:
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

    ALL = [LOW, NORMAL, HIGH, URGENT]

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    submitted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    assigned_primary_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    status = db.Column(db.String(32), nullable=False, default=JobStatus.SUBMITTED)
    priority = db.Column(db.String(16), nullable=False, default=JobPriority.NORMAL)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = db.relationship("Project", backref=db.backref("jobs", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<Job {self.id} status={self.status}>"

class JobAssignment(db.Model):
    __tablename__ = "job_assignments"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    role = db.Column(db.String(32), nullable=False, default="primary")  
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    job = db.relationship("Job", backref=db.backref("assignments", lazy="dynamic"))

class JobEvent(db.Model):
    __tablename__ = "job_events"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    event_type = db.Column(db.String(64), nullable=False) 
    payload_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    job = db.relationship("Job", backref=db.backref("events", lazy="dynamic"))