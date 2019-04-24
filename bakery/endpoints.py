import os
import datetime
import logging
from functools import wraps
from random import choice, choices, randint

import sqlalchemy
from flask import abort
from flask_restplus import Api, Namespace, Resource, fields, reqparse, inputs
from flask_caching import Cache
from .models import (
    db,
    Item,
    Cashier,
    Country,
    Region,
    Bakery,
    City,
    Serie,
    FactoryOrder,
)

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
        "puchaseDate": fields.DateTime(dt_format="iso8601"),
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


sales = Namespace("sales", description="real-time sales feed")
api.add_namespace(sales)


@sales.route("/cashregister")
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
    {"deliveryDate": fields.DateTime(dt_format="iso8601")},
)


order_bill_model = api.model(
    "OrderBill",
    {
        "orderDate": fields.DateTime(dt_format="iso8601"),
        "orders": fields.List(fields.Nested(order_model, skip_none=True)),
    },
)

orders = Namespace("orders", description="snapshot view on orders")
api.add_namespace(orders)


@orders.route("/orders")
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


point_model = api.model(
    "Point",
    {"date": fields.DateTime(dt_format="iso8601"), "value": fields.Float},
)


serie_model = api.model(
    "Serie", {"data": fields.List(fields.Nested(point_model))}
)

point_parser = reqparse.RequestParser()
point_parser.add_argument("id", type=int)
point_parser.add_argument("type", type=str)
point_parser.add_argument("value", type=float)
point_parser.add_argument("date", type=inputs.datetime_from_iso8601)


serie_parser = reqparse.RequestParser()
serie_parser.add_argument("id", type=int)
serie_parser.add_argument("type", type=str)


timeseries = Namespace("timeseries", description="timeseries read/write")
api.add_namespace(timeseries)

for klass in (Cashier, Country, Region, Bakery, City):
    tablename = klass.__tablename__

    @timeseries.route("/{}/timeseries".format(tablename))
    class TimeSeries(Resource):
        @troll_mode
        @api.expect(point_parser)
        def post(self, target=tablename):
            args = point_parser.parse_args()

            ins = Serie.insert().values(
                reference=target,
                reference_id=args["id"],
                serie=args["type"],
                date=args["date"],
                value=args["value"],
            )

            upd = (
                Serie.update()
                .where(Serie.c.reference == target)
                .where(Serie.c.reference_id == args["id"])
                .where(Serie.c.serie == args["type"])
                .where(Serie.c.date == args["date"])
                .values(value=args["value"])
            )

            try:
                db.engine.connect().execute(ins)
            except sqlalchemy.exc.IntegrityError:
                db.engine.connect().execute(upd)

            return {"target": target, "id": args["id"], "message": "success"}

        @troll_mode
        @api.expect(serie_parser)
        @api.marshal_with(serie_model)
        def get(self, target=tablename):
            args = serie_parser.parse_args()
            sel = (
                sqlalchemy.sql.select([Serie.c.date, Serie.c.value])
                .where(Serie.c.reference == target)
                .where(Serie.c.reference_id == args["id"])
                .where(Serie.c.serie == args["type"])
            )

            result = db.engine.connect().execute(sel)

            return {"data": [{"date": d, "value": v} for d, v in result]}


factory = Namespace("factory", description="interface with the factory")
api.add_namespace(factory)


order_parser = reqparse.RequestParser()
order_parser.add_argument("bakery", type=str)
order_parser.add_argument("product", type=str)
order_parser.add_argument("quantity", type=int)
order_parser.add_argument("date", type=inputs.date_from_iso8601)

receipt_parser = reqparse.RequestParser()
receipt_parser.add_argument("date", type=inputs.date_from_iso8601)

next_day_item_model = api.model(
    "NextDayItem", {"item": fields.String, "qty": fields.Integer}
)


next_day_order_model = api.model(
    "NextDayOrder",
    {
        "locationName": fields.String,
        "orderBasket": fields.List(fields.Nested(next_day_item_model)),
    },
)

next_day_order_statement = api.model(
    "NextDayOrderStatement",
    {
        "date": fields.DateTime(dt_format="iso8601"),
        "orders": fields.List(fields.Nested(next_day_order_model)),
    },
)


@factory.route("/next-day-order".format(tablename))
class NextDayOrder(Resource):
    @troll_mode
    @api.expect(receipt_parser)
    @api.marshal_with(next_day_order_statement)
    def get(self):
        args = receipt_parser.parse_args()
        session = db.session

        booked = session.query(FactoryOrder).filter_by(date=args["date"])

        order_per_bakery = {}
        for order in booked.all():
            order_per_bakery.setdefault(order.bakery_name, []).append(
                {"item": order.item_name, "qty": order.quantity}
            )

        return {
            "date": args["date"],
            "orders": [
                {"locationName": k, "orderBasket": v}
                for k, v in order_per_bakery.items()
            ],
        }

    @troll_mode
    @api.expect(order_parser)
    def post(self):
        args = order_parser.parse_args()

        session = db.session
        today = datetime.date.today()

        if args["date"] < today:
            abort(400, "cannot set orders in the past")

        new_order = FactoryOrder(
            bakery_name=args["bakery"],
            item_name=args["product"],
            quantity=args["quantity"],
            date=args["date"],
        )

        try:
            session.add(new_order)
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            logger.info(
                (
                    "refused order {} because another "
                    "order for that day already exists"
                ).format(new_order)
            )

        return {"message": "ok"}


references = Namespace("references", description="details about references")
api.add_namespace(references)

resource_parser = reqparse.RequestParser()
resource_parser.add_argument("name", type=str)

for klass in (Cashier, Country, Region, Bakery, City):
    tablename = klass.__tablename__

    @references.route("/{}/resource".format(tablename))
    class References(Resource):
        @troll_mode
        @api.expect(resource_parser)
        def post(self, tablename=tablename, klass=klass):
            args = resource_parser.parse_args()

            session = db.session

            ref = (
                session.query(klass).filter_by(name=args["name"]).one_or_none()
            )

            if ref is None:
                abort(400, "unknown {}".format(tablename))

            return {"id": ref.id}
