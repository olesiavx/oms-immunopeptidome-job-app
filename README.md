# OMS Immunopeptidome Job App

Flask-based web application for managing OMS immunopeptidomics job requests.

## Features
- User authentication (requester / analyst / admin)
- Job submission (quick + full wizard)
- Workflow status tracking
- Role-based access control
- JSON export for pipeline integration
- Audit logging
- Soft delete (archive)

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
python wsgi.py
flask run --port 5050 (for active updates)

### Creating an admin user

After registering a user normally, promote them to admin via Flask shell:

```bash
flask shell

```from app.models import User
u = User.query.filter_by(email="admin@example.com").first()
u.role = "admin"
db.session.commit()
