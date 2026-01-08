# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import auth_bp
from .forms import RegisterForm, LoginForm
from ..extensions import db
from ..models import User, Role

@auth_bp.get("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    return render_template("auth/register.html", form=form)

@auth_bp.post("/register")
def register_post():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if not form.validate_on_submit():
        return render_template("auth/register.html", form=form), 400

    existing = User.query.filter_by(email=form.email.data.lower()).first()
    if existing:
        flash("Email already registered. Try logging in.", "warning")
        return redirect(url_for("auth.login"))

    user = User(
        name=form.name.data.strip(),
        email=form.email.data.lower().strip(),
        role=Role.REQUESTER,
    )
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.commit()

    flash("Account created. Please log in.", "success")
    return redirect(url_for("auth.login"))

@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    return render_template("auth/login.html", form=form)

@auth_bp.post("/login")
def login_post():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("auth/login.html", form=form), 400

    user = User.query.filter_by(email=form.email.data.lower().strip()).first()
    if not user or not user.check_password(form.password.data):
        flash("Invalid email or password.", "danger")
        return render_template("auth/login.html", form=form), 401

    if not user.is_active:
        flash("Account is disabled. Contact admin.", "danger")
        return render_template("auth/login.html", form=form), 403

    login_user(user)
    next_url = request.args.get("next")
    return redirect(next_url or url_for("main.index"))

@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.index"))