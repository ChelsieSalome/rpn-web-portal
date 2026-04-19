from flask import Blueprint, render_template, session, redirect, url_for
from app.services.sheets import get_all_members, get_member_by_email, get_balance_status, format_currency
from functools import wraps

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        if not session.get("is_admin"):
            return redirect(url_for("auth.unauthorized"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@admin_required
def dashboard():
    members = get_all_members()

    in_deficit   = [m for m in members if m["balance"] < 0]
    total_owed   = sum(abs(m["balance"]) for m in in_deficit)
    on_probation = [m for m in members if m["status"] == "probation"]

    # Add balance_status and formatted balance to each member
    for m in members:
        m["balance_status"] = get_balance_status(m["balance"])
        m["balance_fmt"]    = format_currency(m["balance"])

    # Sort: most negative first
    members_sorted = sorted(members, key=lambda m: m["balance"])

    stats = {
        "total":      len(members),
        "in_deficit": len(in_deficit),
        "total_owed": f"${total_owed:.2f}",
        "probation":  len(on_probation),
    }

    return render_template(
        "admin/dashboard.html",
        members=members_sorted,
        stats=stats,
    )


@admin_bp.route("/members/<member_id>")
@admin_required
def member_detail(member_id):
    members = get_all_members()
    member  = next((m for m in members if m["id"] == member_id), None)

    if not member:
        return redirect(url_for("admin.dashboard"))

    member["balance_status"] = get_balance_status(member["balance"])
    member["balance_fmt"]    = format_currency(member["balance"])

    return render_template("admin/member_detail.html", member=member)


@admin_bp.route("/reminders")
@admin_required
def reminders():
    return render_template("admin/reminders.html")


@admin_bp.route("/settings")
@admin_required
def settings():
    return render_template("admin/settings.html")
