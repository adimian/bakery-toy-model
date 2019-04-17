from flask_restplus import Api, Resource, fields
from .models import db, Item, Cashier
from random import choice, choices, randint
import datetime


api = Api()


item_model = api.model(
    "Item",
    {"item": fields.String, "price": fields.Float, "qty": fields.Integer},
)


base_sale_model = api.model(
    "BaseSale",
    {
        "locationName": fields.String,
        "locationCity": fields.String,
        "locationRegion": fields.String,
        "purchaseBasket": fields.List(fields.Nested(item_model)),
    },
)


sale_model = api.inherit(
    "Sale",
    base_sale_model,
    {
        "puchaseDate": fields.DateTime(dt_format="rfc822"),
        "cashierName": fields.String,
    },
)


def generate_sale(session):
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


@api.route("/cashregister")
class CashRegister(Resource):
    @api.marshal_with(sale_model)
    def get(self):
        session = db.session
        sale = generate_sale(session)
        return sale


order_model = api.inherit(
    "Order",
    base_sale_model,
    {"deliveryDate": fields.DateTime(dt_format="rfc822")},
)


order_bill_model = api.model(
    "OrderBill",
    {
        "orderDate": fields.DateTime(dt_format="rfc822"),
        "orders": fields.List(fields.Nested(order_model, skip_none=True)),
    },
)


@api.route("/orders")
class Orders(Resource):
    @api.marshal_with(order_bill_model)
    def get(self):
        session = db.session
        order_date = datetime.datetime.utcnow()
        orders = []
        bill = {"orderDate": order_date, "orders": orders}
        for _ in range(randint(1, 5)):
            sale = generate_sale(session)
            del sale["cashierName"]
            sale["deliveryDate"] = sale["puchaseDate"]
            del sale["puchaseDate"]

            orders.append(sale)

        return bill
