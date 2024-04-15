from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)  # Achtung: im echten Einsatz sollte das Passwort gehasht werden.
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

class Buchung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    zugnummer = db.Column(db.String(20), nullable=False)
    abfahrtsort = db.Column(db.String(100), nullable=False)
    zielort = db.Column(db.String(100), nullable=False)
    abfahrtszeit = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    preis = db.Column(db.Float, nullable=False)
    storniert = db.Column(db.Boolean, default=False, nullable=False)
    reiseklasse = db.Column(db.String(50), nullable=False)

    user = db.relationship('User', backref='buchungen')
