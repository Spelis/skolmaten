import os
import uuid

from dotenv import dotenv_values, load_dotenv
from flask import Flask


def create_app():
    load_dotenv()
    config = dotenv_values(".env")
    app = Flask(
        __name__,
        template_folder="../templates/",
        static_folder="../static/",
        static_url_path=os.environ.get("ROOT", "/") + "static",
    )
    app.config.from_mapping(DATABASE="database.db")
    app.secret_key = uuid.uuid4().hex
    app.json.sort_keys = False
    app.config["APPLICATION_ROOT"] = config.get("ROOT", "/")

    from . import db

    db.init_app()

    from . import app as main_routes

    app.register_blueprint(main_routes.app, url_prefix=app.config["APPLICATION_ROOT"])

    return app
