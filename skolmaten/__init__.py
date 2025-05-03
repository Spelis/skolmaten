import uuid

from flask import Flask


def create_app():
    app = Flask(__name__, template_folder="../templates/", static_folder="../static/")
    app.config.from_mapping(DATABASE="database.db")
    app.secret_key = uuid.uuid4().hex
    app.json.sort_keys = False

    from . import db

    db.init_app()

    from . import app as main_routes

    app.register_blueprint(main_routes.app)

    return app
