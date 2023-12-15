from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = '571ebf8e13ca209536c29be68d435c01'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_PERMANENT"] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, logger=True, engineio_logger=True)

app.app_context().push()

app.config.from_object('config')

from app import views
from app import models