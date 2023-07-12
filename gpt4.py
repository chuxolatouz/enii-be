from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
from bson import ObjectId, json_util
from utils import generar_token
import json
import random
import string

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/mi_db"
app.config["SECRET_KEY"] = "tu_clave_secreta"

mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app, origins=["http://localhost:3000"])

db_usuarios = mongo.db.usuarios
db_proyectos = mongo.db.proyectos
db_roles = mongo.db.roles
db_categorias = mongo.db.categorias

# Definir una función personalizada de serialización para manejar los objetos ObjectId


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


# Configurar el codificador JSON de Flask para utilizar la función personalizada
app.json_encoder = JSONEncoder

# Rutas de API para la aplicación


@app.route("/registrar", methods=["POST"])
def registrar():
    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data["password"])
    data["password"] = hashed_pw
    db_usuarios.insert_one(data)
    return jsonify({"message": "Usuario registrado con éxito"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    usuario = db_usuarios.find_one({"correo": data["correo"]})
    if usuario and bcrypt.check_password_hash(usuario["password"], data["password"]):
        token = generar_token(usuario["_id"], app.config["SECRET_KEY"])
        return jsonify({"token": token}), 200
    else:
        return jsonify({"message": "Credenciales inválidas"}), 401


@app.route("/crear_rol", methods=["POST"])
def crear_rol():
    data = request.get_json()
    db_roles.insert_one(data)
    return jsonify({"message": "Rol creado con éxito"}), 201


@app.route('/categorias', methods=["GET"])
def obtener_categorias():
    search_text = request.args.get('text')
    if search_text:
        cursor = db_categorias.find(
            {'nombre': {'$regex': search_text, '$options': 'i'}})
    else:
        cursor = db_categorias.find()
    list_cursor = list(cursor)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    return jsonify(list_json), 200


@app.route('/categorias', methods=["POST"])
def crear_categorias():
    data = request.get_json()
    nombre = data['nombre']
    color = ''.join(random.choices(string.hexdigits[:-6], k=6))
    categoria = {'nombre': nombre, 'color': color}
    categoria_insertada = db_categorias.insert_one(categoria)
    categoria["id"] = str(categoria_insertada.inserted_id)
    return jsonify(categoria), 201


@app.route("/asignar_rol", methods=["PATCH"])
def asignar_rol():
    data = request.get_json()
    user_id = data["user_id"]
    rol_id = data["rol_id"]
    db_usuarios.update_one({"_id": ObjectId(user_id)}, {
                           "$set": {"rol_id": ObjectId(rol_id)}})
    return jsonify({"message": "Rol asignado con éxito"}), 200


@app.route("/crear_proyecto", methods=["POST"])
def crear_proyecto():
    data = request.get_json()
    current_user_id = '644d550f0814bb028b458716'
    data["miembros"] = []
    data["balance"] = 0
    data["balance_inicial"] = 0
    data["status"] = "new"
    data["owner"] = ObjectId(current_user_id)
    db_proyectos.insert_one(data)
    return jsonify({"message": "Proyecto creado con éxito"}), 201


@app.route("/asignar_usuario_proyecto", methods=["PATCH"])
def asignar_usuario_proyecto():
    data = request.get_json()
    user_id = data["user_id"]
    proyecto_id = data["proyecto_id"]
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$push": {"miembros": ObjectId(user_id)}})
    return jsonify({"message": "Usuario asignado al proyecto con éxito"}), 200


@app.route("/establecer_reglas_distribucion", methods=["PATCH"])
def establecer_reglas_distribucion():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    reglas = data["reglas"]
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": {"reglas_distribucion": reglas}})
    return jsonify({"message": "Reglas de distribución establecidas con éxito"}), 200


@app.route("/asignar_balance_proyecto", methods=["PATCH"])
def asignar_balance_proyecto():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    balance = data["balance"]
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": {"balance": balance}})
    return jsonify({"message": "Balance asignado al proyecto con éxito"}), 200


@app.route("/mostrar_usuarios", methods=["GET"])
def mostrar_usuarios():
    usuarios = db_usuarios.find()
    list_cursor = list(usuarios)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    return jsonify(list_json), 200


@app.route("/mostrar_proyectos", methods=["GET"])
def mostrar_proyectos():
    proyectos = db_proyectos.find()
    list_cursor = list(proyectos)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    return jsonify(list_json), 200

# Manejo de errores


@app.errorhandler(400)
def error_400(e):
    return jsonify({"message": "Solicitud incorrecta"}), 400


@app.errorhandler(401)
def error_401(e):
    return jsonify({"message": "No autorizado"}), 401


@app.errorhandler(404)
def error_404(e):
    return jsonify({"message": "No encontrado"}), 404


@app.errorhandler(500)
def error_500(e):
    return jsonify({"message": "Error interno del servidor"}), 500


if __name__ == "__main__":
    app.run()
