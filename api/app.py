from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flasgger import Swagger
from bson import ObjectId
import json
from datetime import datetime
import os

app = Flask(__name__)
swagger_file = os.path.join(os.path.dirname(__file__), "swagger.yaml")
Swagger(app, template_file=swagger_file)

app.config["MONGO_URI"] = "mongodb+srv://enii:e5YztEJeaJ9Z@cluster0.cnakns0.mongodb.net/enii"
app.config["SECRET_KEY"] = "tu_clave_secreta"

mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:3000"}})


def agregar_log(id_proyecto, mensaje):
    data = {
        "id_proyecto": ObjectId(id_proyecto),
        "fecha_creacion": datetime.utcnow(),
        "mensaje": mensaje,
    }
    mongo.db.logs.insert_one(data)
    return "registro agregado"


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return JSONEncoder.default(self, o)


app.json_encoder = JSONEncoder
