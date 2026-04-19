import os
from flask import Blueprint, redirect, url_for, session, render_template, request
from app.services.oauth import oauth, init_oauth
from app.services.sheets import get_member_by_email
from flask import current_app

auth_bp = Blueprint("auth", __name__)


@auth_bp.record_once
def on_load(state):
    init_oauth(state.app)


@auth_bp.route("/")
def login():
    """Login page — redirect to dashboard if already logged in."""
    if session.get("user"):
        if session.get("is_admin"):
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("member.dashboard"))
    return render_template("auth/login.html")


@auth_bp.route("/login/google")
def login_google():
    """Kick off the Google OAuth flow."""
    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/callback")
def callback():
    """Handle Google OAuth callback."""
    token = oauth.google.authorize_access_token()
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        return redirect(url_for("auth.unauthorized"))

    email = user_info["email"]
    admin_email = os.getenv("ADMIN_EMAIL", "")

    # Check admin
    if email == admin_email:
        session["user"]     = {"email": email, "name": user_info.get("name", "Admin")}
        session["is_admin"] = True
        return redirect(url_for("admin.dashboard"))

    # Check member
    member = get_member_by_email(email)
    if not member:
        return redirect(url_for("auth.unauthorized"))
    if member["status"] == "deactivated":
        return redirect(url_for("auth.unauthorized"))

    session["user"]     = {"email": email, "name": user_info.get("name", member["name"])}
    session["is_admin"] = False
    return redirect(url_for("member.dashboard"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/unauthorized")
def unauthorized():
    return render_template("auth/unauthorized.html"), 403
