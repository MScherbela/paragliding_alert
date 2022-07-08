from extensions import db
import datetime
from flask_security import UserMixin, RoleMixin

# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean)
    confirmed_at = db.Column(db.DateTime)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    condition_filter = db.relationship("ConditionFilter", uselist=False, backref="user")

    def on_model_change(self):
        pass

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    launch_directions = db.Column(db.String, default="0-360")
    active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class ConditionFilter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    max_wind = db.Column(db.Float, default=15)
    max_gust = db.Column(db.Float, default=25)
    max_prec = db.Column(db.Float, default=0.5)
    start_time_weekday = db.Column(db.Time, default=datetime.time(hour=16))
    start_time_friday = db.Column(db.Time, default=datetime.time(hour=14))
    start_time_weekend = db.Column(db.Time, default=datetime.time(hour=7))
    end_time = db.Column(db.Time, default=datetime.time(hour=21))
    alert_level_weekday = db.Column(db.Integer, default=3)
    alert_level_friday = db.Column(db.Integer, default=2)
    alert_level_weekend = db.Column(db.Integer, default=1)
    min_window = db.Column(db.Integer, default=3) # in hours


