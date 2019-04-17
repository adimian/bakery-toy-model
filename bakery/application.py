from flask import Flask
from .models import db
from .endpoints import api
from .admin import admin
from flask_admin.contrib.sqla import ModelView


def app_maker():
    app = Flask("bakery")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bakery.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["DEBUG"] = True
    app.config["SECRET_KEY"] = "whatever"
    db.init_app(app)
    api.init_app(app)
    admin.init_app(app)

    from .models import Country, Region, City, Bakery, Cashier, Item

    for model in (Country, Region, City, Bakery, Cashier, Item):
        admin.add_view(ModelView(model, db.session))

    @app.before_first_request
    def create_db():
        db.create_all()

    return app
