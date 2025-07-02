# QuickDeliver Lite – Week 6 (driver approval + OTP + admin panel)

import os, random, string
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

from models import db, User, DeliveryRequest, Feedback
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")

# SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quickdeliver.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Mail
app.config["MAIL_SERVER"]   = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"]     = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"]  = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

with app.app_context():
    db.create_all()

STATUS_FLOW   = {"Accepted": "In Transit", "In Transit": "Delivered"}
ALLOWED_ROLES = ["Customer", "Driver"]

# ───────────────────────────────
# Helpers & decorators
# ───────────────────────────────
def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

def role_required(role):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u or u.role != role:
                return redirect(url_for("home"))
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

def gen_otp(n=6):
    return "".join(random.choices(string.digits, k=n))

def send_otp(address, otp):
    msg = Message(
        subject="QuickDeliver – verify your e-mail",
        sender  = app.config["MAIL_USERNAME"],
        recipients=[address],
        body=(
            f"Hello!\n\nYour QuickDeliver one-time code is {otp}. "
            "It is valid for 10 minutes.\n\n"
            "If you did not try to register, please ignore this message."
        )
    )
    mail.send(msg)

# ───────────────────────────────
# Auth routes
# ───────────────────────────────
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            if user.role == "Driver" and not user.is_approved:
                flash("Your driver account is awaiting admin approval.", "error")
                return redirect(url_for("home"))

            session.update(
                user_id=user.id,
                email=user.email,
                name=user.name,
                role=user.role
            )
            return redirect(url_for({
                "Customer": "customer_dashboard",
                "Driver":   "driver_dashboard",
                "Admin":    "admin_dashboard"
            }[user.role]))
        flash("Invalid e-mail or password", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form["email"]).first():
            flash("E-mail already registered.", "error")
            return redirect(url_for("register"))

        role = request.form["role"]
        if role not in ALLOWED_ROLES:
            flash("Invalid role selected.", "error")
            return redirect(url_for("register"))

        otp = gen_otp()
        session.update(
            otp_code    = otp,
            otp_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
            temp_user   = {
                "name":     request.form["name"],
                "email":    request.form["email"],
                "password": request.form["password"],
                "role":     role
            }
        )
        try:
            send_otp(request.form["email"], otp)
            flash("OTP sent – check your inbox.")
        except Exception as exc:
            flash(f"E-mail send error: {exc}", "error")
            return redirect(url_for("register"))

        return redirect(url_for("verify_otp"))

    return render_template("register.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    temp = session.get("temp_user")
    if not temp or "otp_expires" not in session:
        flash("Session expired – please register again.", "error")
        return redirect(url_for("register"))

    if request.method == "POST":
        if (request.form["otp"].strip() == session.get("otp_code") and
                datetime.utcnow() <= datetime.fromisoformat(session["otp_expires"])):
            
            if User.query.filter_by(email=temp["email"]).first():
                flash("Email already registered. Please login.", "error")
                return redirect(url_for("home"))

            try:
                db.session.add(User(
                    name     = temp["name"],
                    email    = temp["email"],
                    password = generate_password_hash(temp["password"]),
                    role     = temp["role"],
                    is_approved = (temp["role"] != "Driver")
                ))
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Email already exists. Try logging in.", "error")
                return redirect(url_for("home"))

            session.pop("otp_code", None)
            session.pop("otp_expires", None)
            session.pop("temp_user", None)
            flash("Verified! You can now log in.")
            return redirect(url_for("home"))

        flash("Invalid or expired OTP.", "error")

    return render_template("verify_otp.html", email=temp["email"])

@app.route("/resend_otp", methods=["POST"])
def resend_otp():
    temp = session.get("temp_user")
    if not temp:
        flash("Session expired – please register again.", "error")
        return redirect(url_for("register"))

    otp = gen_otp()
    session["otp_code"]    = otp
    session["otp_expires"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    try:
        send_otp(temp["email"], otp)
        flash("A new OTP has been sent.")
    except Exception as exc:
        flash(f"Failed to resend OTP: {exc}", "error")

    return redirect(url_for("verify_otp"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ───────────────────────────────
# Admin
# ───────────────────────────────
@app.route("/admin")
@role_required("Admin")
def admin_dashboard():
    unapproved = User.query.filter_by(role="Driver", is_approved=False).all()
    return render_template("admin_dashboard.html",
                           users      = User.query.all(),
                           deliveries = DeliveryRequest.query.all(),
                           feedbacks  = Feedback.query.all(),
                           pending_drivers = unapproved)

@app.route("/admin/approve_driver/<int:user_id>", methods=["POST"])
@role_required("Admin")
def approve_driver(user_id):
    u = User.query.get_or_404(user_id)
    if u.role == "Driver" and not u.is_approved:
        u.is_approved = True
        db.session.commit()
        flash(f"{u.name} has been approved as a driver.")
    return redirect(url_for("admin_dashboard"))

# ───────────────────────────────
# Customer routes
# ───────────────────────────────
@app.route("/customer")
@role_required("Customer")
def customer_dashboard():
    u = current_user()
    deliveries = DeliveryRequest.query.filter_by(customer_id=u.id).all()
    return render_template("customer_dashboard.html",
                           user=u, deliveries=deliveries, STATUS_FLOW=STATUS_FLOW)

@app.route("/request/create", methods=["GET", "POST"])
@role_required("Customer")
def create_request():
    if request.method == "POST":
        db.session.add(DeliveryRequest(
            pickup_address  = request.form["pickup"],
            dropoff_address = request.form["dropoff"],
            package_note    = request.form["note"],
            customer_id     = session["user_id"],
            status          = "Pending"
        ))
        db.session.commit()
        flash("Delivery request created.")
        return redirect(url_for("customer_dashboard"))
    return render_template("create_request.html")

# ───────────────────────────────
# Driver routes
# ───────────────────────────────
@app.route("/driver")
@role_required("Driver")
def driver_dashboard():
    return render_template("driver_dashboard.html", name=session["name"])

@app.route("/driver/requests")
@role_required("Driver")
def driver_requests():
    pending = DeliveryRequest.query.filter_by(status="Pending", driver_id=None).all()
    return render_template("driver_requests.html", deliveries=pending)

@app.route("/driver/accept/<int:delivery_id>", methods=["POST"])
@role_required("Driver")
def accept_delivery(delivery_id):
    d = DeliveryRequest.query.get_or_404(delivery_id)
    if d.status == "Pending" and d.driver_id is None:
        d.status, d.driver_id = "Accepted", session["user_id"]
        db.session.commit()
        flash(f"Delivery #{d.id} accepted.")
    else:
        flash("This delivery is no longer available.", "error")
    return redirect(url_for("driver_requests"))

@app.route("/driver/update_status/<int:delivery_id>", methods=["POST"])
@role_required("Driver")
def update_delivery_status(delivery_id):
    d = DeliveryRequest.query.get_or_404(delivery_id)
    if d.driver_id != session["user_id"]:
        abort(403)
    nxt = STATUS_FLOW.get(d.status)
    if not nxt:
        flash("Status cannot be advanced further.", "error")
    else:
        d.status = nxt
        db.session.commit()
        flash(f"Status updated to {nxt}.")
    return redirect(url_for("my_deliveries"))

@app.route("/driver/my_deliveries")
@role_required("Driver")
def my_deliveries():
    deliveries = DeliveryRequest.query.filter_by(driver_id=session["user_id"]).all()
    return render_template("my_deliveries.html",
                           deliveries=deliveries, STATUS_FLOW=STATUS_FLOW)

# ───────────────────────────────
# Feedback & profile
# ───────────────────────────────
@app.route("/feedback/<int:delivery_id>", methods=["GET", "POST"])
@role_required("Customer")
def leave_feedback(delivery_id):
    d = DeliveryRequest.query.get_or_404(delivery_id)
    if d.customer_id != session["user_id"] or d.status != "Delivered":
        abort(403)
    if Feedback.query.filter_by(delivery_id=delivery_id).first():
        flash("Feedback already provided.", "error")
        return redirect(url_for("profile"))

    if request.method == "POST":
        try:
            rating = int(request.form["rating"]); assert 1 <= rating <= 5
        except (ValueError, AssertionError):
            flash("Rating must be 1-5.", "error")
            return redirect(request.url)

        db.session.add(Feedback(
            delivery_id = delivery_id,
            rating      = rating,
            comment     = request.form["comment"][:200]
        ))
        db.session.commit()
        flash("Thank you for your feedback!")
        return redirect(url_for("profile"))

    return render_template("feedback_form.html", delivery=d)

@app.route("/profile")
def profile():
    u = current_user()
    if not u:
        return redirect(url_for("home"))

    if u.role == "Customer":
        deliveries = DeliveryRequest.query.filter_by(customer_id=u.id).all()
        fb_map = {fb.delivery_id: fb for fb in
                  Feedback.query.join(DeliveryRequest)
                  .filter(DeliveryRequest.customer_id == u.id)}
        return render_template("profile_customer.html",
                               user=u, deliveries=deliveries, feedback_map=fb_map)

    if u.role == "Driver":
        deliveries = DeliveryRequest.query.filter_by(
            driver_id=u.id, status="Delivered").all()
        feedbacks = (Feedback.query.join(DeliveryRequest)
                     .filter(DeliveryRequest.driver_id == u.id).all())
        return render_template("profile_driver.html",
                               user=u, deliveries=deliveries, feedbacks=feedbacks)

    return redirect(url_for("admin_dashboard"))

# ───────────────────────────────
# Main
# ───────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
 