from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)

    def __str__(self):
        return self.name


class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)

    country_id = db.Column(
        db.Integer, db.ForeignKey("country.id"), nullable=False
    )
    country = db.relationship(
        "Country", backref=db.backref("regions", lazy="joined")
    )

    def __str__(self):
        return self.name


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)

    region_id = db.Column(
        db.Integer, db.ForeignKey("region.id"), nullable=False
    )
    region = db.relationship(
        "Region", backref=db.backref("cities", lazy="joined")
    )

    def __str__(self):
        return self.name


class Bakery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)

    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    city = db.relationship(
        "City", backref=db.backref("bakeries", lazy="joined")
    )

    def __str__(self):
        return self.name


class Cashier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)

    bakery_id = db.Column(
        db.Integer, db.ForeignKey("bakery.id"), nullable=False
    )
    bakery = db.relationship(
        "Bakery", backref=db.backref("cashiers", lazy="joined")
    )

    def __str__(self):
        return self.name


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)

    def __str__(self):
        return self.name
