import os
import datetime
import logging
from functools import wraps
from random import choice, choices, randint
from flask import abort
from flask_restplus import Api, Resource, fields
from flask_caching import Cache
from .models import db, Item, Cashier

api = Api()
cache = Cache(config={"CACHE_TYPE": "redis"})


logger = logging.getLogger(__name__)


def troll_mode(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        if os.getenv("TROLL"):
            case = randint(1, 10)

            def hang(*args, **kwargs):
                import time

                logger.info("troll: hang mode")
                time.sleep(5)
                return f(*args, **kwargs)

            def kill(*args, **kwargs):
                logger.info("troll: server error mode")
                abort(choice([502, 504, 500, 501]))

            def noop(*args, **kwargs):
                logger.info("troll: noop mode")
                return {}

            response = {1: hang, 2: kill, 3: noop}

            method = response.get(case, f)
        else:
            method = f
        return method(*args, **kwargs)

    return decorated


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
    @troll_mode
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
    @troll_mode
    @cache.cached(timeout=60)
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
