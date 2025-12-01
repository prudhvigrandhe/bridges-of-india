from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    states = db.relationship("State", backref="country", lazy=True)


class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey("country.id"), nullable=False)
    districts = db.relationship("District", backref="state", lazy=True)


class District(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    bridges = db.relationship("Bridge", backref="district", lazy=True)


class Bridge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    river_name = db.Column(db.String(100))
    year_built = db.Column(db.Integer)
    bridge_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))
    district_id = db.Column(db.Integer, db.ForeignKey("district.id"), nullable=False)
