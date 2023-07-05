from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
from bson import ObjectId, json_util
from decorators import validar_datos, allow_cors, token_required
from utils import string_to_int, int_to_string, generar_token, map_to_doc
import json
import random
import math
import string
import os

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/mi_db"
app.config["SECRET_KEY"] = "tu_clave_secreta"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app, origins=["http://localhost:3000"])

db_usuarios = mongo.db.usuarios
db_proyectos = mongo.db.proyectos
db_roles = mongo.db.roles
db_acciones = mongo.db.acciones
db_categorias = mongo.db.categorias
db_documentos = mongo.db.documentos

# Definir una función personalizada de serialización para manejar los objetos ObjectId


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


# Configurar el codificador JSON de Flask para utilizar la función personalizada
app.json_encoder = JSONEncoder


@app.route("/registrar", methods=["POST"])
@validar_datos({
    "nombre": str,
    "email": str,
    "password": str
})
def registrar():
    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data["password"])
    data["password"] = hashed_pw
    db_usuarios.insert_one(data)
    return jsonify({"message": "Usuario registrado con rxito"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    usuario = db_usuarios.find_one({"correo": data["correo"]})
    if usuario and bcrypt.check_password_hash(usuario["password"], data["password"]):
        token = generar_token(usuario["_id"], app.config["SECRET_KEY"])
        return jsonify({"token": token}), 200
    else:
        return jsonify({"message": "Credenciales inválidas"}), 401


@app.route("/olvido_contraseña", methods=["POST"])
def olvido_contraseña():
    data = request.get_json()
    usuario = db_usuarios.find_one({"correo": data["correo"]})
    if usuario:
        # Enviar correo electrónico con enlace para restablecer contraseña
        return jsonify({"message": "Se ha enviado un correo electrónico para restablecer la contraseña"}), 200
    else:
        return jsonify({"message": "El correo electrónico no está registrado"}), 404


@app.route("/editar_usuario/<id_usuario>", methods=["PUT"])
@token_required
def editar_usuario(id_usuario):
    data = request.get_json()
    db_usuarios.update_one({"_id": ObjectId(id_usuario)}, {"$set": data})
    return jsonify({"message": "Información de usuario actualizada con éxito"}), 200
# ... Agregar otros endpoints (iniciar sesión, olvido contraseña, editar información de usuario, etc.) ...


@app.route("/crear_rol", methods=["POST"])
@token_required
def crear_rol():
    data = request.get_json()
    db_roles.insert_one(data)
    return jsonify({"message": "Rol creado con éxito"}), 201


@app.route('/categorias', methods=["GET"])
@allow_cors
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
@allow_cors
@validar_datos({
    "nombre": str
})
def crear_categorias():
    data = request.get_json()
    nombre = data['nombre']
    color = ''.join(random.choices(string.hexdigits[:-6], k=6))
    categoria = {'nombre': nombre, 'color': color}
    categoria_insertada = db_categorias.insert_one(categoria)
    categoria["id"] = str(categoria_insertada.inserted_id)
    return jsonify(categoria), 201


@app.route("/asignar_rol", methods=["PATCH"])
@token_required
def asignar_rol():
    data = request.get_json()
    user_id = data["user_id"]
    rol_id = data["rol_id"]
    db_usuarios.update_one({"_id": ObjectId(user_id)}, {
                           "$set": {"rol_id": ObjectId(rol_id)}})
    return jsonify({"message": "Rol asignado con éxito"}), 200


@app.route("/crear_proyecto", methods=["POST"])
# @token_required
@validar_datos({
    "nombre": str,
    "descripcion": str,
    "fecha_inicio": str,
    "fecha_fin": str
})
def crear_proyecto():
    current_user = '644d550f0814bb028b458716'
    data = request.get_json()
    data["miembros"] = []
    data["balance"] = 000
    data["balance_inicial"] = 000
    data["status"] = "new"
    data["owner"] = ObjectId(current_user)
    db_proyectos.insert_one(data)
    return jsonify({"message": "Proyecto creado con éxito"}), 201


@app.route("/asignar_usuario_proyecto", methods=["PATCH"])
@allow_cors
def asignar_usuario_proyecto():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    usuario = data["usuario"]
    fecha_hora_actual = datetime.utcnow()
    data["fecha_ingreso"] = fecha_hora_actual.strftime("%d/%m/%Y %H:%M")
    # Verificar si el usuario ya está en la lista de miembros
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    miembros = proyecto["miembros"]
    if any(miembro["usuario"]["_id"]["$oid"] == data["usuario"]["_id"]["$oid"] for miembro in miembros):
        return jsonify({"message": "El usuario ya es miembro del proyecto"}), 400

    # Agregar el usuario a la lista de miembros
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$push": {"miembros": data}})
    return jsonify({"message": "Usuario asignado al proyecto con éxito"}), 200


@app.route("/eliminar_usuario_proyecto", methods=["PATCH"])
@allow_cors
def eliminar_usuario_proyecto():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    usuario_id = data["usuario_id"]

    # Verificar si el usuario ya está en la lista de miembros
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    miembros = proyecto["miembros"]
    if not any(miembro["usuario"]["_id"]["$oid"] == usuario_id for miembro in miembros):
        return jsonify({"message": "El usuario no es miembro del proyecto"}), 400

    # Eliminar el usuario de la lista de miembros
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$pull": {"miembros": {"usuario._id.$oid": usuario_id}}})
    return jsonify({"message": "Usuario eliminado del proyecto con éxito"}), 200


@app.route("/establecer_regla_distribucion", methods=["PATCH"])
@token_required
def establecer_regla_distribucion():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    regla_distribucion = data["regla_distribucion"]
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": {"regla_distribucion": regla_distribucion}})
    return jsonify({"message": "Regla de distribución establecida con éxito"}), 200


@app.route("/asignar_balance", methods=["PATCH"])
# @token_required
@allow_cors
def asignar_balance():
    data = request.get_json()
    proyecto_id = data["project_id"]
    proyecto = db_proyectos.find_one({'_id': ObjectId(proyecto_id)})
    data_balance = string_to_int(data["balance"])
    balance = data_balance + int(proyecto["balance"])
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": {"balance": balance}})
    data_acciones = {}
    data_acciones["project_id"] = ObjectId(proyecto_id)
    data_acciones['user'] = 'Prueba'
    data_acciones['type'] = 'Fondeo'
    data_acciones['amount'] = data_balance
    data_acciones['total_amount'] = balance
    db_acciones.insert_one(data_acciones)

    return jsonify({"message": "Balance asignado con éxito"}), 200


@app.route("/roles", methods=["GET"])
@allow_cors
def roles():
    roles = db_roles.find({})
    list_cursor = list(roles)
    list_dump = json_util.dumps(list_cursor)
    # Removezr las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(list_json)
    return list_json


@app.route("/mostrar_usuarios", methods=["GET"])
@allow_cors
def mostrar_usuarios():
    params = request.args
    skip = int(params.get('page')) if params.get('page') else 0
    limit = params.get('limit') if params.get('limit') else 10
    text = params.get('text')

    query = {}
    if text:
        query = {
            "$or": [
                {"nombre": {"$regex": text, "$options": "i"}},
                {"email": {"$regex": text, "$options": "i"}},
            ]
        }
    list_users = db_usuarios.find(query).skip(skip * limit).limit(limit)
    quantity = db_usuarios.count_documents(query)
    list_cursor = list(list_users)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
        count=quantity
    )
    return list_json


@app.route("/mostrar_proyectos", methods=["GET"])
# @token_required
@allow_cors
def mostrar_proyectos():
    # Obtener el número de página actual
    params = request.args
    skip = int(params.get('page')) if params.get('page') else 0
    limit = params.get('limit') if params.get('limit') else 10
    # query = {"_id": ObjectId(request_id)}
    list_verification_request = db_proyectos.find(
        {}).skip(skip * limit).limit(limit)
    quantity = db_proyectos.count_documents({})
    list_cursor = list(list_verification_request)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
        count=quantity
    )
    return list_json


@app.route('/proyecto/<string:id>/acciones', methods=['GET'])
@allow_cors
def acciones_proyecto(id):

    id = ObjectId(id)

    params = request.args
    skip = int(params.get('page')) if params.get('page') else 0
    limit = params.get('limit') if params.get('limit') else 10
    acciones = db_acciones.find({'project_id': id}).skip(
        skip * limit).limit(limit)
    acciones = map(map_to_doc, acciones)
    quantity = db_acciones.count_documents({'project_id': id}) / 10
    quantity = math.ceil(quantity)
    list_cursor = list(acciones)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
        count=quantity
    )
    return list_json


@app.route('/proyecto/<string:id>', methods=['GET'])
@allow_cors
def proyecto(id):
    # Convertir el ID a ObjectId
    id = ObjectId(id)

    # Buscar el producto por ID en la base de datos
    proyecto = db_proyectos.find_one({'_id': id})

    # Si el proyecto no existe, devolver un error 404
    if not proyecto:
        return jsonify({'error': 'proyecto no encontrado'}), 404

    # Convertir el ObjectId a una cadena de texto
    proyecto['_id'] = str(proyecto['_id'])
    balance = int_to_string(proyecto['balance'])
    balance_inicial = int_to_string(proyecto['balance_inicial'])
    proyecto['balance'] = balance
    proyecto['balance_inicial'] = balance_inicial

    # Devolver el proyecto como una respuesta JSON
    return jsonify(proyecto)


@app.route('/proyecto/<string:id>/documentos', methods=['GET'])
@allow_cors
def mostrar_documentos_proyecto(id):

    id = ObjectId(id)

    params = request.args
    skip = int(params.get('page')) if params.get('page') else 0
    limit = params.get('limit') if params.get('limit') else 10
    documentos = db_documentos.find({'project_id': id}).skip(
        skip * limit).limit(limit)
    # acciones = map(map_to_doc, acciones)
    quantity = db_documentos.count_documents({'project_id': id}) / 10
    quantity = math.ceil(quantity)
    list_cursor = list(documentos)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
        count=quantity
    )
    return list_json


@app.route('/proyecto/<string:id>/documentos', methods=['POST'])
@allow_cors
def crear_documentos_proyecto(id):
    # Obtener la ruta de la carpeta del proyecto
    carpeta_proyecto = os.path.join('files', id)

    # Crear la carpeta del proyecto si no existe
    if not os.path.exists(carpeta_proyecto):
        os.makedirs(carpeta_proyecto)

    # Obtener la descripción y el monto del presupuesto del formulario
    descripcion = request.form.get('descripcion')

    # Crear el documento del presupuesto
    presupuesto = {
        'project_id': ObjectId(id),
        'descripcion': descripcion,
        'status': 'new',
        'archivos': []
    }

    # Obtener los archivos del formulario
    archivos = request.files.getlist('files')

    # Guardar los archivos en las subcarpetas del proyecto
    for archivo in archivos:
        # Obtener el nombre del archivo
        nombre_archivo = archivo.filename

        # Crear la carpeta del presupuesto
        presupuesto_id = str(ObjectId())
        carpeta_presupuesto = os.path.join(carpeta_proyecto, presupuesto_id)
        os.makedirs(carpeta_presupuesto)

        # Guardar el archivo en la carpeta del presupuesto
        archivo.save(os.path.join(carpeta_presupuesto, nombre_archivo))

        # Agregar el archivo al arreglo de archivos del presupuesto
        presupuesto['archivos'].append({
            'nombre': nombre_archivo,
            'ruta': os.path.join(carpeta_presupuesto, nombre_archivo)
        })
    result = db_documentos.insert_one(presupuesto)

    if result.acknowledged:
        return jsonify({'mensaje': 'Archivos subidos exitosamente'}), 201
    else:
        return jsonify({'error': 'Error al subir archivos'}), 404


@app.route('/proyecto/<string:id>/documento/<string:doc_id>', methods=['POST'])
@allow_cors
def cerrar_presupuesto(id, doc_id):
    data = request.get_json()

    # Actualizas balance
    proyecto = db_proyectos.find_one({'_id': ObjectId(id)})
    data_balance = string_to_int(data["balance"])
    proyecto_balance = int(proyecto["balance"])
    balance = proyecto_balance - data_balance
    db_proyectos.update_one({"_id": ObjectId(id)}, {
                            "$set": {"balance": balance}})

    # Agregas la accion a las actividades

    data_acciones = {}
    data_acciones["project_id"] = ObjectId(id)
    data_acciones['user'] = 'Prueba'
    data_acciones['type'] = 'Retiro' + ' ' + data["description"]
    data_acciones['amount'] = data_balance * -1
    data_acciones['total_amount'] = balance
    db_acciones.insert_one(data_acciones)

    # Cierras el presupuesto

    db_documentos.update_one({'_id': ObjectId(doc_id)}, {
                             "$set": {"status": "finished"}})

    return jsonify({'mensaje': 'proyecto ajustado exitosamente'}), 201


if __name__ == "__main__":
    app.run(debug=True)