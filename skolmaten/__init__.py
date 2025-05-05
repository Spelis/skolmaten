import os
import uuid

from dotenv import load_dotenv
from flask import Flask


def create_app():
    load_dotenv()
    app = Flask(__name__, template_folder="../templates/", static_folder="../static/")
    app.config.from_mapping(DATABASE="database.db")
    app.secret_key = uuid.uuid4().hex
    app.json.sort_keys = False
    app.config["APPLICATION_ROOT"] = os.environ.get("ROOT", "/")

    from . import db

    db.init_app()

    from . import app as main_routes

    app.register_blueprint(main_routes.app)

    return app
