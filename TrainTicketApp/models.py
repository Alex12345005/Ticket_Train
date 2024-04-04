from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Buchung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    zugnummer = db.Column(db.String(20), nullable=False)
    abfahrtsort = db.Column(db.String(100), nullable=False)
    zielort = db.Column(db.String(100), nullable=False)
    abfahrtszeit = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    preis = db.Column(db.Float, nullable=False)
    storniert = db.Column(db.Boolean, default=False, nullable=False)
