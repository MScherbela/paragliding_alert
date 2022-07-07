from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_apscheduler import APScheduler
from flask_security import Security, SQLAlchemyUserDatastore
from flask_login import current_user
from flask_mail import Mail

class ProtectedModelView(ModelView):
    def is_accessible(self):
        return current_user.has_role('admin')

class ProtectedAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.has_role('admin')

def add_admin_views():
    # Add an admin view for every class in the db
    for mapper in db.Model.registry.mappers:
        admin.add_view(ProtectedModelView(mapper.class_, db.session))

db = SQLAlchemy()
scheduler = APScheduler()
security = Security()
mail = Mail()
admin = Admin(template_mode='bootstrap4', index_view=ProtectedAdminIndexView())

def init_extensions(app):
    from models import User, Role
    db.init_app(app)
    mail.init_app(app)
    security.init_app(app, SQLAlchemyUserDatastore(db, User, Role))
    admin.init_app(app)
    add_admin_views()
    scheduler.init_app(app)
    scheduler.start()




