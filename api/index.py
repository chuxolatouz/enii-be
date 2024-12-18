from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
from bson import ObjectId, json_util
# from cloudinary import config, api, uploader
from b2sdk.v2 import (B2Api, InMemoryAccountInfo)
from util.decorators import validar_datos, allow_cors, token_required
from util.utils import string_to_int, int_to_string, generar_token, map_to_doc, actualizar_pasos, auth_account
import json
import random
import math
import string
import os
from io import BytesIO

app = Flask(__name__)
# app.config["MONGO_URI"] = "mongodb+srv://enii:e5YztEJeaJ9Z@cluster0.cnakns0.mongodb.net/enii"
app.config["MONGO_URI"] = "mongodb://localhost:27017/mi_db"
app.config["SECRET_KEY"] = "tu_clave_secreta"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app)

info = InMemoryAccountInfo()
b2_api = B2Api(account_info=info)

# config(
#     cloud_name="dnfl6l0xp",
#     api_key="734477293158223",
#     api_secret="Xh4crQOUXkMG2TaMC_OT4yBx5Wc",
#     secure=True
# )

db_usuarios = mongo.db.usuarios
db_proyectos = mongo.db.proyectos
db_roles = mongo.db.roles
db_acciones = mongo.db.acciones
db_categorias = mongo.db.categorias
db_documentos = mongo.db.documentos
db_solicitudes = mongo.db.solicitudes
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
            "id": str(usuario["_id"]),
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


@app.route("/eliminar_usuario", methods=["POST"])
@token_required
def eliminar_usuario(user):
    data = request.get_json()
    id_usuario = data["id_usuario"]
    result = db_usuarios.delete_one({"_id": ObjectId(id_usuario)})

    if result.deleted_count == 1:
        return jsonify({"message": "Usuario eliminado éxitosamente"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar el usuario"}), 400


@app.route("/crear_rol", methods=["POST"])
@token_required
def crear_rol():
    data = request.get_json()
    db_roles.insert_one(data)
    return jsonify({"message": "Rol creado con éxito"}), 201


@app.route('/mostrar_categorias', methods=["GET"])
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
    current_user = user["sub"]
    data = request.get_json()
    data["miembros"] = []
    data["balance"] = 000
    data["balance_inicial"] = 000
    data["status"] = {"actual": 1, "completado": []}
    data["show"] = {"status": False}
    data["owner"] = ObjectId(current_user)
    data["user"] = user
    project = db_proyectos.insert_one(data)
    message_log = 'Usuario %s ha creado el proyecto' % user["nombre"]
    agregar_log(project.inserted_id, message_log)
    return jsonify({"message": "Proyecto creado con éxito"}), 201


@app.route("/actualizar_proyecto/<project_id>", methods=["PUT"])
@token_required
@validar_datos({
    "nombre": str,
    "descripcion": str,
    "fecha_inicio": str,
    "fecha_fin": str
})
def actualizar_proyecto(user, project_id):
    current_user = user["sub"]
    data = request.get_json()

    # Check if project exists
    project = db_proyectos.find_one({"_id": ObjectId(project_id)})
    if not project:
        return jsonify({"message": "Proyecto no encontrado"}), 404

    # Ensure only the owner can update the project
    # if project["owner"] != ObjectId(current_user):
    #     return jsonify({"message": "No tienes permiso para actualizar este proyecto"}), 403

    # Update specified fields
    for key, value in data.items():
        project[key] = value

    # Save updated project
    db_proyectos.update_one({"_id": ObjectId(project_id)}, {"$set": project})

    message_log = 'Usuario %s ha actualizado el proyecto' % user["nombre"]
    agregar_log(project_id, message_log)

    return jsonify({"message": "Proyecto actualizado con éxito"}), 200


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

    new_status = {}
    query = {"$push": {"miembros": data}}
    # Agregar el usuario a la lista de miembros
    if 2 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 2)

    if data["role"]["value"] == "lider":
        new_status = actualizar_pasos(proyecto["status"], 3)

    if bool(new_status):
        query["$set"] = {"status": new_status}

    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, query)
    message_log = f'{usuario["nombre"]} fue asignado al proyecto por {user["nombre"]} con el rol {data["role"]["label"]}'
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
    usuario = None
    for miembro in miembros:
        if miembro["usuario"]["_id"]["$oid"] == usuario_id:
            usuario = miembro["usuario"]
            break
    if usuario is None:
        return jsonify({"message": "El usuario no es miembro del proyecto"}), 400

    # Eliminar el usuario de la lista de miembros
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$pull": {"miembros": {"usuario._id.$oid": usuario_id}}})
    message_log = f'{usuario["nombre"]} fue eliminado del proyecto por {user["nombre"]}'
    agregar_log(proyecto_id, message_log)
    return jsonify({"message": "Usuario eliminado del proyecto con éxito"}), 200


@app.route("/asignar_regla_distribucion", methods=["POST"])
@allow_cors
@token_required
def asignar_regla_distribucion(user):
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    regla_distribucion = data["regla_distribucion"]
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})

    if 4 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 4)
        db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                                "$set": {"status": new_status, "reglas": regla_distribucion}})

        message_log = f'{user["nombre"]} establecio las reglas de distribucion del proyecto'
        agregar_log(proyecto_id, message_log)
        return jsonify({"message": "Regla de distribución establecida con éxito"}), 200

    return jsonify({"message": "El proyecto ya cuenta con regla de distribución"}), 200


@app.route("/crear_solicitud_regla_fija", methods=["POST"])
@token_required
def crear_solicitud_regla_fija(user):
    data = request.get_json()
    solicitud_regla = {}
    items = data["items"]
    for item in items:
        item["monto"] = item["monto"] * 100

    solicitud_regla["nombre"] = data["name"]
    solicitud_regla["reglas"] = items
    solicitud_regla["status"] = "new"
    solicitud_regla["usuario"] = user
    db_solicitudes.insert_one(solicitud_regla)
    return jsonify({"message": "Solicitud de regla creada con éxito"}), 200

# TODO: Agregar el tema de los decorators con multiples ID


@app.route("/eliminar_solicitud_regla_fija/<string:id>", methods=["POST"])
@allow_cors
def eliminar_solicitud_regla_fija(id):
    query = {'_id': ObjectId(id)}
    result = db_solicitudes.delete_one(query)
    if result.deleted_count == 1:
        return jsonify({"message": "Solicitud de regla eliminada con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


@app.route("/completar_solicitud_regla_fija/<string:id>", methods=["POST"])
@allow_cors
def completar_solicitud_regla_fija(id):
    data = request.get_json()
    resolution = data["resolution"]
    query = {'_id': ObjectId(id)}
    result = db_solicitudes.update_one(
        query, {"$set": {"status": resolution}})
    if result.modified_count == 1:
        return jsonify({"message": "Solicitud de regla eliminada con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


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
        new_changes["balance_inicial"] = balance

    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": new_changes})
    data_acciones = {}
    data_acciones["project_id"] = ObjectId(proyecto_id)
    data_acciones['user'] = 'Prueba'
    data_acciones['type'] = 'Fondeo'
    data_acciones['amount'] = data_balance
    data_acciones['total_amount'] = balance
    db_acciones.insert_one(data_acciones)
    message_log = f'{user["nombre"]} agrego balance al proyecto por un monto de: ${int_to_string(data_balance)}'
    agregar_log(proyecto_id, message_log)

    return jsonify({"message": "Balance asignado con éxito"}), 200


@app.route("/roles", methods=["GET"])
@allow_cors
def roles():
    roles = db_roles.find({})
    list_cursor = list(roles)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
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
    list_users = db_usuarios.find().skip(skip * limit).limit(limit)
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
    proyecto['owner'] = str(proyecto['owner'])
    proyecto['balance_inicial'] = balance_inicial

    # Devolver el proyecto como una respuesta JSON
    if "regla_fija" in proyecto:
        proyecto["regla_fija"]["_id"] = str(proyecto["regla_fija"]["_id"])
    print(proyecto)
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


@app.route('/documento_crear', methods=['POST'])
@allow_cors
@token_required
def crear_presupuesto(user):
    # Get project ID and other details from request
    project_id = request.form.get('proyecto_id')
    descripcion = request.form.get('descripcion')
    monto = request.form.get('monto')

    # Validate required fields
    if not project_id or not descripcion or not monto:
        return jsonify({'error': 'Missing required fields'}), 400

    # Generate unique presupuesto ID
    presupuesto_id = str(ObjectId())

    # Create folders with project ID and presupuesto ID in Cloudinary
    folder_path = f"{project_id}/{presupuesto_id}"
    # try:
    #     print('Folder Path')
    #     print(folder_path)
    #     api.create_folder(path=folder_path)
    # except Exception as e:
    #     print(f"Error creating folder: {e}")
    #     return jsonify({'error': 'Error creating folders'}), 400

    # Create budget object
    presupuesto = {
        'project_id': ObjectId(project_id),
        'presupuesto_id': presupuesto_id,
        'descripcion': descripcion,
        # Replace with your string to int conversion function
        'monto': string_to_int(monto),
        'status': 'new',
        'archivos': []
    }

    # Get uploaded files from request
    archivos = request.files.getlist('files')

    # Track successfully uploaded files and error messages
    uploaded_files = []
    error_messages = []

    # Upload files to Cloudinary within presupuesto folder
    for archivo in archivos:
        # Generate unique public ID (optional)
        public_id = f"budgets/{folder_path}/{archivo.filename}"

        # Upload file to Cloudinary
        auth_account(b2_api)
        bucket = b2_api.get_bucket_by_id("d4ea8d3dcc4e0ff288e40d13")

        file_buffer = BytesIO(archivo.read())
        file_data = file_buffer.read()
        upload_result = bucket.upload_bytes(file_data, file_name=public_id)

        if upload_result is not None:
            uploaded_files.append(upload_result.id_)
            presupuesto['archivos'].append({
                'nombre': archivo.filename,
                'public_id': upload_result.id_
            })
        else:
            error_messages.append(
                f"Error uploading file {archivo.filename}: {upload_result['error']}")

    # Handle upload errors (if any)
    if error_messages:
        # Delete successfully uploaded files if any
        # for uploaded_file in uploaded_files:
        #     api.destroy(public_id=uploaded_file)

        # Return error response with messages
        return jsonify({'error': error_messages}), 400

    # Insert presupuesto object into database
    result = db_documentos.insert_one(presupuesto)

    # Handle database errors
    if not result.acknowledged:
        return jsonify({'error': 'Error saving presupuesto'}), 500

    # Log document creation
    message_log = f'{user["nombre"]} agrego el presupuesto {descripcion} con un monto de ${monto}'
    agregar_log(project_id, message_log)

    # Return success response
    return jsonify({'mensaje': 'Archivos subidos exitosamente'}), 201


@app.route('/documento_cerrar', methods=['POST'])
@allow_cors
@token_required
def cerrar_presupuesto(user):
    id = request.form.get("proyecto_id")
    doc_id = request.form.get("doc_id")
    data_balance = request.form.get("monto")
    data_descripcion = request.form.get("description")
    carpeta_proyecto = os.path.join('files', id)

    # Crear la carpeta del proyecto si no existe
    if not os.path.exists(carpeta_proyecto):
        os.makedirs(carpeta_proyecto)
    # Actualizas balance
    proyecto = db_proyectos.find_one({'_id': ObjectId(id)})
    data_balance = string_to_int(data_balance)
    proyecto_balance = int(proyecto["balance"])
    balance = proyecto_balance - data_balance
    db_proyectos.update_one({"_id": ObjectId(id)}, {
                            "$set": {"balance": balance}})

    # Agregas la accion a las actividades
    data_acciones = {}
    data_acciones["project_id"] = ObjectId(id)
    data_acciones['user'] = user["nombre"]
    data_acciones['type'] = f'Retiro {data_descripcion}'
    data_acciones['amount'] = data_balance * -1
    data_acciones['total_amount'] = balance
    db_acciones.insert_one(data_acciones)

    # Cierras el presupuesto

    archivos = request.files.getlist('files')
    archivos_guardados = []
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
        archivos_guardados.append({
            'nombre': nombre_archivo,
            'ruta': os.path.join(carpeta_presupuesto, nombre_archivo)
        })

    db_documentos.update_one({'_id': ObjectId(doc_id)}, {
                             "$set": {"status": "finished", "monto_aprobado": data_balance, "archivos_aprobado": archivos_guardados}})

    message_log = f'{user["nombre"]} cerro el presupuesto {data_descripcion} con un monto de ${int_to_string(data_balance)}'
    agregar_log(id, message_log)

    return jsonify({'mensaje': 'proyecto ajustado exitosamente'}), 201


@app.route("/documento_eliminar", methods=["POST"])
@allow_cors
@token_required
def eliminar_presupuesto(user):
    data = request.get_json()
    presupuesto_id = data["budget_id"]
    id = data["project_id"]
    documento = db_documentos.find_one({'_id': ObjectId(presupuesto_id)})
    if documento is None:
        return jsonify({"message": "Presupuesto no encontrado"}), 404

    descripcion = documento["descripcion"]
    monto = documento["monto"]
    if documento["status"] == "finished":
        return jsonify({'mensaje': 'Presupuesto esta finalizado, no se puede eliminar'}), 401

    result = db_documentos.delete_one({'_id': ObjectId(presupuesto_id)})
    if result.deleted_count == 1:
        message_log = f'{user["nombre"]} elimino el presupuesto {descripcion} con un monto de ${int_to_string(monto)}'
        agregar_log(id, message_log)

        return jsonify({"message": "Solicitud de regla eliminada con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


@app.route("/eliminar_proyecto", methods=["POST"])
@allow_cors
@token_required
def eliminar_proyecto(user):
    data = request.get_json()
    id = data["proyecto_id"]
    documento = db_proyectos.find_one({'_id': ObjectId(id)})
    if documento is None:
        return jsonify({"message": "Proyecto no encontrado"}), 404

    result = db_proyectos.delete_one({'_id': ObjectId(id)})
    if result.deleted_count == 1:
        return jsonify({"message": "Proyecto eliminado con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


@app.route("/finalizar_proyecto", methods=["POST"])
@allow_cors
@token_required
def finalizar_proyecto(user):

    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    if proyecto is None:
        return jsonify({"message": "Proyecto no encontrado"}), 404
    balance = proyecto["balance"]
    reglas = proyecto["reglas"]
    if len(dir(reglas)) == 0:
        return jsonify({"message": "No se han establecido reglas de distribución"}), 404

    if sum(reglas.values()) != 100:
        return jsonify({"message": "La suma de los porcentajes de reglas debe ser igual a 100"}), 401
    miembros = proyecto.get("miembros", [])
    if len(miembros) == 0:
        return jsonify({"message": "No hay miembros asignados al proyecto"}), 404
        # 1. Calculate the percentage distribution for each role:
    distribucion = {
        role: (percentage / 100) * balance for role, percentage in reglas.items()
    }

    # 2. Create an empty list to store the budget-assigned members:
    budgeted_members = []

    # 3. Iterate through each member and assign their budget:
    for member in miembros:  # Using "miembros" instead of "members"
        member_role = member.get("role")
        member_role_value = member_role.get("value")
        if member_role_value in distribucion:
            member_budget = distribucion[member_role_value]
            budgeted_members.append(
                {"role": member_role, "budget": member_budget})
        else:
            print(
                f"Warning: No rule found for role '{member_role_value}'. Budget not assigned.")
    new_status = actualizar_pasos(proyecto["status"], 6)
    new_status["finished"] = True
    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                            "$set": {"status": new_status, "distribucion_recursos": budgeted_members}})
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    message_log = f'{user["nombre"]} finalizó el proyecto'
    agregar_log(proyecto_id, message_log)

    return jsonify({"message": "Proyecto finalizado con éxito"}), 200


@app.route("/proyecto/<string:id>/logs", methods=["GET"])
@allow_cors
def obtener_logs(id):
    id = ObjectId(id)

    params = request.args
    skip = int(params.get('page')) if params.get('page') else 0
    limit = params.get('limit') if params.get('limit') else 10
    acciones = db_logs.find({'id_proyecto': id}).skip(
        skip * limit).limit(limit)
    quantity = db_logs.count_documents({'id_proyecto': id}) / 10
    quantity = math.ceil(quantity)

    list_cursor = list(acciones)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
        count=quantity
    )
    return list_json, 200
    # return jsonify(list_json), 200


@app.route("/mostrar_solicitudes", methods=["GET"])
@allow_cors
@token_required
def mostrar_solicitudes(user):
    # Obtener el número de página actual
    params = request.args
    skip = int(params.get('page')) if params.get('page') else 0
    limit = params.get('limit') if params.get('limit') else 10
    # query = {"_id": ObjectId(request_id)}
    list_verification_request = db_solicitudes.find(
        {}).skip(skip * limit).limit(limit)
    quantity = db_solicitudes.count_documents({})
    list_cursor = list(list_verification_request)
    list_dump = json_util.dumps(list_cursor)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
        count=quantity
    )
    return list_json


@app.route("/mostrar_reglas_fijas", methods=["GET"])
@allow_cors
@token_required
def mostrar_reglas_fijas(user):
    list_request = db_solicitudes.find({"status": "completed"})
    list_cursor = list(list_request)
    list_dump = json_util.dumps(list_cursor)
    list_json = json.loads(list_dump.replace('\\', ''))
    list_json = jsonify(
        request_list=list_json,
    )

    return list_json, 200


@app.route("/proyecto/<string:id>/fin", methods=["GET"])
@allow_cors
def mostrar_finalizacion(id):
    id = ObjectId(id)
    movs = db_acciones.find({'project_id': id})
    docs = db_documentos.find({'project_id': id})
    logs = db_logs.find({'id_proyecto': id})

    movs_cursor = list(movs)
    movs_dump = json_util.dumps(movs_cursor)
    movs_json = json.loads(movs_dump.replace('\\', ''))

    docs_cursor = list(docs)
    docs_dump = json_util.dumps(docs_cursor)
    docs_json = json.loads(docs_dump.replace('\\', ''))

    logs_cursor = list(logs)
    logs_dump = json_util.dumps(logs_cursor)
    list_json = json.loads(logs_dump.replace('\\', ''))
    data_response = jsonify(
        logs=list_json,
        documentos=docs_json,
        movimientos=movs_json
    )
    return data_response, 200


@app.route("/asignar_regla_fija/", methods=["POST"])
@allow_cors
@token_required
def asignar_regla_fija(user):
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    regla_id = data["regla_id"]

    # Encontrar Regla
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    if proyecto is None:
        return jsonify({"message": "Proyecto no encontrado"}), 404

    # Encontrara Proyecto
    regla = db_solicitudes.find_one({"_id": ObjectId(regla_id)})
    if regla is None:
        return jsonify({"message": "Regla fija no encontrada"}), 404

    # Verificar proyecto tiene balance inicial
    if proyecto["balance_inicial"] == 0:
        return jsonify({"message": "Antes de asignar regla tienes que asignar balance"}), 400

    # Descontar proyecto
    for x in regla["reglas"]:
        proyecto_balance = int(proyecto["balance"])
        balance = proyecto_balance - x["monto"]
        db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
                                "$set": {"balance": balance}})

        # Agregas la accion a las actividades

        data_acciones = {}
        data_acciones["project_id"] = ObjectId(proyecto_id)
        data_acciones['user'] = user["nombre"]
        data_acciones['type'] = x["nombre_regla"]
        data_acciones['amount'] = x["monto"] * -1
        data_acciones['total_amount'] = balance
        db_acciones.insert_one(data_acciones)

        message_log = f'{user["nombre"]} asigno la regla: {regla["nombre"]} con el item {x["nombre_regla"]} con un monto de ${int_to_string(x["monto"])}'
        agregar_log(proyecto_id, message_log)

    # Asignar la regla
    new_status = actualizar_pasos(proyecto["status"], 5)

    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {
        "$set": {"regla_fija": regla, "status": new_status}})

    # Dar respuesta que todo esta ok
    return jsonify({"message": "La regla se asigno correctamente"}), 200


@app.route("/", methods=["GET"])
@allow_cors
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
    print(e)
    return jsonify({"message": "No encontrado"}), 404


@app.errorhandler(500)
def error_500(e):
    print(e)
    return jsonify({"message": "Error interno del servidor"}), 500


if __name__ == "__main__":
    app.run()
