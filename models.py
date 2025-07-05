from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    password    = db.Column(db.String(200), nullable=False)
    role        = db.Column(db.String(20), nullable=False)  # Customer | Driver | Admin
    is_approved = db.Column(db.Boolean, default=True)       # ← Required for driver approval

    deliveries_created = db.relationship(
        "DeliveryRequest",
        backref="customer",
        lazy=True,
        foreign_keys="DeliveryRequest.customer_id"
    )

    deliveries_taken = db.relationship(
        "DeliveryRequest",
        backref="driver",
        lazy=True,
        foreign_keys="DeliveryRequest.driver_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.id} | {self.email} | {self.role} | approved={self.is_approved}>"

class DeliveryRequest(db.Model):
    __tablename__ = "delivery_request"

    id              = db.Column(db.Integer, primary_key=True)
    pickup_address  = db.Column(db.String(200), nullable=False)
    dropoff_address = db.Column(db.String(200), nullable=False)
    package_note    = db.Column(db.String(300))
    status          = db.Column(db.String(20), default="Pending")  # Pending → Accepted → In Transit → Delivered
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    driver_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    feedback = db.relationship(
        "Feedback",
        uselist=False,
        back_populates="delivery",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Delivery #{self.id} | {self.status}>"


class Feedback(db.Model):
    __tablename__ = "feedback"

    id          = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(
        db.Integer,
        db.ForeignKey("delivery_request.id"),
        unique=True,
        nullable=False
    )
    rating      = db.Column(db.Integer, nullable=False)  # 1–5
    comment     = db.Column(db.String(200))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    delivery = db.relationship("DeliveryRequest", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback delivery={self.delivery_id} rating={self.rating}>"
