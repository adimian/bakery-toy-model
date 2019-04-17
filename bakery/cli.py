from flask_script import Manager
from bakery.application import app_maker


app = app_maker()
manager = Manager(app)


# @manager.command
# def hello():
#     print "hello"

if __name__ == "__main__":
    manager.run()
