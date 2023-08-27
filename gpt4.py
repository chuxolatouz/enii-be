from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
from bson import ObjectId, json_util
from decorators import validar_datos, allow_cors, token_required
from utils import string_to_int, int_to_string, generar_token, map_to_doc, actualizar_pasos
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
CORS(app)

db_usuarios = mongo.db.usuarios
db_proyectos = mongo.db.proyectos
db_roles = mongo.db.roles
db_acciones = mongo.db.acciones
db_categorias = mongo.db.categorias
db_documentos = mongo.db.documentos
db_logs = mongo.db.logs

# Definir una función personalizada de serialización para manejar los objetos ObjectId


def agregar_log(id_proyecto, mensaje):

    data = {}
    data["id_proyecto"] = ObjectId(id_proyecto)
    data["fecha_creacion"] = datetime.utcnow()
    # data["usuario"] = user
    data["mensaje"] = mensaje

    db_logs.insert_one(data)

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
@validar_datos({
    "email": str,
    "password": str
})
def login():
    data = request.get_json()
    usuario = db_usuarios.find_one({"email": data["email"]})

    if usuario and bcrypt.check_password_hash(usuario["password"], data["password"]):
        token = generar_token(usuario, app.config["SECRET_KEY"])

        return jsonify({
            "token": token,
            "email": data["email"],
            "id": usuario["_id"],
            "role": "admin"
        }), 200
    else:
        return jsonify({"message": "Credenciales inválidas"}), 401


@app.route("/olvido_contraseña", methods=["POST"])
def olvido_contraseña():
    data = request.get_json()
    usuario = db_usuarios.find_one({"email": data["email"]})
    if usuario:
        # Enviar email electrónico con enlace para restablecer contraseña
        return jsonify({"message": "Se ha enviado un email electrónico para restablecer la contraseña"}), 200
    else:
        return jsonify({"message": "El email electrónico no está registrado"}), 404


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
@token_required
@validar_datos({
    "nombre": str,
    "descripcion": str,
    "fecha_inicio": str,
    "fecha_fin": str
})
def crear_proyecto(user):
    current_user = user._id
    data = request.get_json()
    data["miembros"] = []
    data["balance"] = 000
    data["balance_inicial"] = 000
    data["status"] = {"actual": 1, "completado": []}
    data["show"] = {"status": False}
    data["owner"] = ObjectId(current_user)
    db_proyectos.insert_one(data)
    return jsonify({"message": "Proyecto creado con éxito"}), 201


@app.route("/asignar_usuario_proyecto", methods=["PATCH"])
@allow_cors
@token_required
def asignar_usuario_proyecto(user):
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
    new_status = {}
    if 2 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 2)
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$push": {"miembros": data}, "$set": {"status": new_status}})
    message_log = 'usuario %s fue asignado al proyecto', usuario.nombre
    agregar_log(proyecto_id, message_log)
    return jsonify({"message": "Usuario asignado al proyecto con éxito"}), 200


@app.route("/eliminar_usuario_proyecto", methods=["PATCH"])
@allow_cors
@token_required
def eliminar_usuario_proyecto(user):
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
    message_log = 'usuario %s fue eliminado del proyecto', usuario_id
    agregar_log(proyecto_id, message_log)
    return jsonify({"message": "Usuario eliminado del proyecto con éxito"}), 200


@app.route("/establecer_regla_distribucion", methods=["PATCH"])
@token_required
def establecer_regla_distribucion():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    regla_distribucion = data["regla_distribucion"]

    new_changes = {"regla_distribucion": regla_distribucion}
    if 3 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 3)
        new_changes["status"] = new_status

    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": new_changes})

    message_log = 'usuario establecio las reglas de distribucion del proyecto'
    agregar_log(proyecto_id, message_log)
    return jsonify({"message": "Regla de distribución establecida con éxito"}), 200


@app.route("/asignar_balance", methods=["PATCH"])
@allow_cors
@token_required
def asignar_balance(user):
    data = request.get_json()
    proyecto_id = data["project_id"]
    proyecto = db_proyectos.find_one({'_id': ObjectId(proyecto_id)})
    data_balance = string_to_int(data["balance"])
    balance = data_balance + int(proyecto["balance"])
    new_changes = {"balance": balance}

    if 1 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 1)
        new_changes["status"] = new_status

    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": new_changes})
    data_acciones = {}
    data_acciones["project_id"] = ObjectId(proyecto_id)
    data_acciones['user'] = 'Prueba'
    data_acciones['type'] = 'Fondeo'
    data_acciones['amount'] = data_balance
    data_acciones['total_amount'] = balance
    db_acciones.insert_one(data_acciones)
    message_log = user["nombre"] + \
        'agrego balance al proyecto por un monto de: $' + \
        int_to_string(data_balance)
    agregar_log(proyecto_id, message_log)

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
@allow_cors
@token_required
def mostrar_proyectos(user):
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
    message_log = 'usuario agrego documento al proyecto'
    agregar_log(id, message_log)

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
    message_log = 'usuario cerro presupuesto'

    agregar_log(id, message_log)

    return jsonify({'mensaje': 'proyecto ajustado exitosamente'}), 201


@app.route("/finalizar_proyecto", methods=["PATCH"])
@allow_cors
def finalizar_proyecto():
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    if proyecto is None:
        return jsonify({"message": "Proyecto no encontrado"}), 404
    balance = proyecto["balance"]
    reglas = proyecto.get("reglas_distribucion", [])
    if len(reglas) == 0:
        return jsonify({"message": "No se han establecido reglas de distribución"}), 400
    total_porcentaje = sum([r["porcentaje"] for r in reglas])
    if total_porcentaje != 100:
        return jsonify({"message": "La suma de los porcentajes de reglas debe ser igual a 100"}), 400
    miembros = proyecto.get("miembros", [])
    if len(miembros) == 0:
        return jsonify({"message": "No hay miembros asignados al proyecto"}), 400
    distribucion = []
    for r in reglas:
        cantidad = math.floor(balance * r["porcentaje"] / 100)
        if r["tipo"] == "igual":
            cantidad_miembros = len(miembros)
            cantidad_por_miembro = math.floor(cantidad / cantidad_miembros)
            for m in miembros:
                distribucion.append(
                    {"miembro": m, "cantidad": cantidad_por_miembro})
        elif r["tipo"] == "proporcional":
            total_contribucion = sum([r.get(str(m), 0) for m in miembros])
            for m in miembros:
                contribucion = r.get(str(m), 0)
                if total_contribucion > 0:
                    cantidad_miembro = math.floor(
                        cantidad * contribucion / total_contribucion)
                else:
                    cantidad_miembro = 0
                distribucion.append(
                    {"miembro": m, "cantidad": cantidad_miembro})
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": {"status": "finished", "distribucion_recursos": distribucion}})
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    message_log = 'usuario finalizo el proyecto'
    agregar_log(proyecto_id, message_log)

    return jsonify({"message": "Proyecto finalizado con éxito", "proyecto": proyecto}), 200


@app.route("/proyectos/<id_proyecto>/logs", methods=["GET"])
@allow_cors
def obtener_logs(id_proyecto):
    proyecto = db_proyectos.find_one({"_id": ObjectId(id_proyecto)})
    if not proyecto:
        return jsonify({"message": "Proyecto no encontrado"}), 404

    logs = db_logs.find().sort("fecha_creacion", -1)
    list_logs = list(logs)
    list_dump = json_util.dumps(list_logs)
    list_json = json.loads(list_dump.replace('\\', ''))
    return jsonify(list_json), 200


@app.route("/", methods=["GET"])
def index():
    return 'pong'


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
