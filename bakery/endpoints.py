from flask_restplus import Api, Resource, fields
from .models import db, Item, Cashier
from random import choice, choices, randint
import datetime


api = Api()


item_model = api.model(
    "Item",
    {"item": fields.String, "price": fields.Float, "qty": fields.Integer},
)

sale_model = api.model(
    "Sale",
    {
        "locationName": fields.String,
        "locationCity": fields.String,
        "locationRegion": fields.String,
        "puchaseDate": fields.DateTime(dt_format="rfc822"),
        "purchaseBasket": fields.List(fields.Nested(item_model)),
        "cashierName": fields.String,
    },
)


@api.route("/cashregister")
class CashRegister(Resource):
    @api.marshal_with(sale_model, envelope="resource")
    def get(self):

        session = db.session

        cashier = choice(session.query(Cashier).all())
        bakery = cashier.bakery
        all_items = session.query(Item).all()
        number_of_items = randint(1, len(all_items))
        items = choices(all_items, k=number_of_items)

        purchased = [
            {"item": item.name, "qty": randint(1, 5), "price": item.price}
            for item in items
        ]

        return {
            "locationName": bakery.name,
            "locationCity": bakery.city.name,
            "locationRegion": bakery.city.region.name,
            "puchaseDate": datetime.datetime.utcnow(),
            "purchaseBasket": purchased,
            "cashierName": cashier.name,
        }
