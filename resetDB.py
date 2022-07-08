from app import db, app
import os
from flask_security.utils import hash_password
import datetime
from models import ConditionFilter, Location

if os.path.isfile('/data/paragliding.db'):
    os.remove('/data/paragliding.db')

with app.app_context():
    user_datastore = app.extensions['security'].datastore
    db.create_all()
    user_datastore.create_role(name='admin')
    db.session.commit()

    user = user_datastore.create_user(email="michael.scherbela@gmail.com",
                               password=hash_password("password"),
                               roles=['admin'],
                               confirmed_at=datetime.datetime.now())
    db.session.commit()
    db.session.add(ConditionFilter(user_id=user.id))
    db.session.commit()
    db.session.add(Location(name="Sonnwendstein", lat=47.6293939,lon=15.8616387, user_id=user.id))
    db.session.commit()






