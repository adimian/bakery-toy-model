from flask_script import Manager
from bakery.application import app_maker


app = app_maker()
manager = Manager(app)

from flask_script import Command, Option


class GunicornServer(Command):

    description = "Run the app within Gunicorn"

    def __init__(self, host="127.0.0.1", port=8000, workers=4):
        self.port = port
        self.host = host
        self.workers = workers

    def get_options(self):
        return (
            Option("-H", "--host", dest="host", default=self.host),
            Option("-p", "--port", dest="port", type=int, default=self.port),
            Option(
                "-w",
                "--workers",
                dest="workers",
                type=int,
                default=self.workers,
            ),
        )

    def __call__(self, app, host, port, workers):

        from gunicorn import version_info

        if version_info < (0, 9, 0):
            from gunicorn.arbiter import Arbiter
            from gunicorn.config import Config

            arbiter = Arbiter(
                Config(
                    {"bind": "%s:%d" % (host, int(port)), "workers": workers}
                ),
                app,
            )
            arbiter.run()
        else:
            from gunicorn.app.base import Application

            class FlaskApplication(Application):
                def init(self, parser, opts, args):
                    return {
                        "bind": "{0}:{1}".format(host, port),
                        "workers": workers,
                    }

                def load(self):
                    return app

            FlaskApplication().run()


manager.add_command("serve", GunicornServer())


def main():
    manager.run()


if __name__ == "__main__":
    main()
