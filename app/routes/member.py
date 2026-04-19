import os
from flask import Blueprint, render_template, session, redirect, url_for
from app.services.sheets import get_member_by_email, get_balance_status, format_currency
from functools import wraps

member_bp = Blueprint("member", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@member_bp.route("/dashboard")
@login_required
def dashboard():
    email  = session["user"]["email"]
    member = get_member_by_email(email)

    if not member:
        return redirect(url_for("auth.unauthorized"))

    balance        = member["balance"]
    balance_status = get_balance_status(balance)
    balance_fmt    = format_currency(balance)
    payment_email  = os.getenv("PAYMENT_EMAIL", "")
    payment_deadline = os.getenv("PAYMENT_DEADLINE", "the 25th of this month")

    return render_template(
        "member/dashboard.html",
        member=member,
        balance_status=balance_status,
        balance_fmt=balance_fmt,
        payment_email=payment_email,
        payment_deadline=payment_deadline,
    )


@member_bp.route("/history")
@login_required
def history():
    return render_template("member/history.html", member=session["user"])


@member_bp.route("/coverage")
@login_required
def coverage():
    return render_template("member/coverage.html", member=session["user"])
