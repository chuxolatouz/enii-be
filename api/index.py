from flask import Flask, request, jsonify, send_file
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
from bson import ObjectId, json_util


from b2sdk.v2 import B2Api, InMemoryAccountInfo
from util.decorators import validar_datos, allow_cors, token_required
from util.utils import (
    string_to_int,
    int_to_string,
    generar_token,
    map_to_doc,
    actualizar_pasos,
    auth_account,
    generar_csv,
    generar_json
)
from flasgger import Swagger
import json
import random
import math
import string
import os
from io import BytesIO

### Swagger UI configuration ###f
SWAGGER_URL = '/swagger'   # URL for exposing Swagger UI (without trailing slash)
API_URL = '/swagger.json'  # Our API url route

app = Flask(__name__)
Swagger(app)

app.config["MONGO_URI"] = (
    "mongodb+srv://enii:e5YztEJeaJ9Z@cluster0.cnakns0.mongodb.net/enii"
)
# app.config["MONGO_URI"] = "mongodb://localhost:27017/mi_db"
app.config["SECRET_KEY"] = "tu_clave_secreta"
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
CORS(app, supports_credentials=True)

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
@validar_datos({"nombre": str, "email": str, "password": str})
def registrar():
    """
    Endpoint para registrar una persona en la plataforma.
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nombre:
              type: string
              example: "Juan"
            email:
              type: string
              example: "juan@example.com"
            password:
              type: string
              example: "password123"
    responses:
      201:
        description: Usuario registrado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Usuario registrado con éxito"
      400:
        description: Error en los datos enviados.
    """

    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data["password"])
    data["password"] = hashed_pw
    db_usuarios.insert_one(data)
    return jsonify({"message": "Usuario registrado con rxito"}), 201


@app.route("/login", methods=["POST"])
@validar_datos({"email": str, "password": str})
def login():   
    """
    Endpoint para iniciar sesión en la plataforma.
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "juan@example.com"
            password:
              type: string
              example: "password123"
    responses:
      200:
        description: Inicio de sesión exitoso.
        schema:
          type: object
          properties:
            token:
              type: string
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            email:
              type: string
              example: "juan@example.com"
            id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            nombre:
              type: string
              example: "Juan"
            role:
              type: string
              example: "usuario"
      401:
        description: Credenciales inválidas.
    """
    data = request.get_json()
    usuario = db_usuarios.find_one({"email": data["email"]})

    if usuario and bcrypt.check_password_hash(usuario["password"], data["password"]):
        token = generar_token(usuario, app.config["SECRET_KEY"])

        return jsonify(
            {
                "token": token,
                "email": data["email"],
                "id": str(usuario["_id"]),
                "nombre": usuario["nombre"],
                "role": "admin" if usuario.get("is_admin") else "usuario",
            }
        ), 200
    else:
        return jsonify({"message": "Credenciales inválidas"}), 401


@app.route("/olvido_contraseña", methods=["POST"])
def olvido_contraseña():
    """
    Endpoint para solicitar restablecimiento de contraseña.
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
              example: "juan@example.com"
    responses:
      200:
        description: Email enviado para restablecer la contraseña.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Se ha enviado un email electrónico para restablecer la contraseña"
      404:
        description: Email no registrado.
    """
    data = request.get_json()
    usuario = db_usuarios.find_one({"email": data["email"]})
    if usuario:
        # Enviar email electrónico con enlace para restablecer contraseña
        return jsonify(
            {
                "message": "Se ha enviado un email electrónico para restablecer la contraseña"
            }
        ), 200
    else:
        return jsonify({"message": "El email electrónico no está registrado"}), 404


@app.route("/editar_usuario/<id_usuario>", methods=["PUT"])
@token_required
def editar_usuario(id_usuario):
    """
    Endpoint para editar la información de un usuario.
    ---
    tags:
      - Usuarios
    parameters:
      - in: path
        name: id_usuario
        required: true
        description: ID del usuario a editar.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: body
        name: body
        required: true
        description: Datos a actualizar del usuario.
        schema:
          type: object
          properties:
            nombre:
              type: string
              example: "Juan Actualizado"
            email:
              type: string
              example: "juan_actualizado@example.com"
    responses:
      200:
        description: Información de usuario actualizada con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Información de usuario actualizada con éxito"
      404:
        description: Usuario no encontrado.
    """
    data = request.get_json()
    db_usuarios.update_one({"_id": ObjectId(id_usuario)}, {"$set": data})
    return jsonify({"message": "Información de usuario actualizada con éxito"}), 200


@app.route("/eliminar_usuario", methods=["POST"])
@token_required
def eliminar_usuario(user):
    """
    Endpoint para eliminar un usuario.
    ---
    tags:
      - Usuarios
    parameters:
      - in: body
        name: body
        required: true
        description: ID del usuario a eliminar.
        schema:
          type: object
          properties:
            id_usuario:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
    responses:
      200:
        description: Usuario eliminado exitosamente.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Usuario eliminado éxitosamente"
      400:
        description: No se pudo eliminar el usuario.
    """
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
    """
    Endpoint para crear un nuevo rol.
    ---
    tags:
      - Roles
    parameters:
      - in: body
        name: body
        required: true
        description: Datos del rol a crear.
        schema:
          type: object
          properties:
            nombre:
              type: string
              example: "Administrador"
            permisos:
              type: array
              items:
                type: string
              example: ["crear_usuario", "editar_usuario"]
    responses:
      201:
        description: Rol creado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Rol creado con éxito"
    """
    data = request.get_json()
    db_roles.insert_one(data)
    return jsonify({"message": "Rol creado con éxito"}), 201


@app.route("/mostrar_categorias", methods=["GET"])
@allow_cors
def obtener_categorias():
    """
    Endpoint para obtener una lista de categorías.
    ---
    tags:
      - Categorías
    parameters:
      - in: query
        name: text
        required: false
        description: Texto para filtrar las categorías por nombre.
        schema:
          type: string
          example: "educación"
    responses:
      200:
        description: Lista de categorías obtenida con éxito.
        schema:
          type: array
          items:
            type: object
            properties:
              _id:
                type: string
                example: "64b8f3e2c9d1a2b3c4d5e6f7"
              nombre:
                type: string
                example: "Educación"
              color:
                type: string
                example: "#FF5733"
    """
    search_text = request.args.get("text")
    if search_text:
        cursor = db_categorias.find(
            {"nombre": {"$regex": search_text, "$options": "i"}}
        )
    else:
        cursor = db_categorias.find()
    
    list_cursor = list(cursor)
    list_dump = json.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    print(list_dump)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    return jsonify(list_json), 200


@app.route("/categorias", methods=["POST"])
@allow_cors
@validar_datos({"nombre": str})
def crear_categorias():
    """
    Endpoint para crear una nueva categoría.
    ---
    tags:
      - Categorías
    parameters:
      - in: body
        name: body
        required: true
        description: Datos de la categoría a crear.
        schema:
          type: object
          properties:
            nombre:
              type: string
              example: "Educación"
    responses:
      201:
        description: Categoría creada con éxito.
        schema:
          type: object
          properties:
            id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            nombre:
              type: string
              example: "Educación"
            color:
              type: string
              example: "#FF5733"
    """
    data = request.get_json()
    nombre = data["nombre"]
    color = "".join(random.choices(string.hexdigits[:-6], k=6))
    categoria = {"nombre": nombre, "color": color}
    categoria_insertada = db_categorias.insert_one(categoria)
    categoria["id"] = str(categoria_insertada.inserted_id)
    return jsonify(categoria), 201


@app.route("/asignar_rol", methods=["PATCH"])
@token_required
def asignar_rol():
    """
    Endpoint para asignar un rol a un usuario.
    ---
    tags:
      - Roles
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para asignar el rol.
        schema:
          type: object
          properties:
            user_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            rol_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f8"
    responses:
      200:
        description: Rol asignado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Rol asignado con éxito"
    """
    data = request.get_json()
    user_id = data["user_id"]
    rol_id = data["rol_id"]
    db_usuarios.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"rol_id": ObjectId(rol_id)}}
    )
    return jsonify({"message": "Rol asignado con éxito"}), 200


@app.route("/crear_proyecto", methods=["POST"])
@token_required
@validar_datos(
    {"nombre": str, "descripcion": str, "fecha_inicio": str, "fecha_fin": str}
)
def crear_proyecto(user):
    """
    Endpoint para asignar un rol a un usuario.
    ---
    tags:
      - Roles
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para asignar el rol.
        schema:
          type: object
          properties:
            user_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            rol_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f8"
    responses:
      200:
        description: Rol asignado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Rol asignado con éxito"
    """
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
    message_log = "Usuario %s ha creado el proyecto" % user["nombre"]
    agregar_log(project.inserted_id, message_log)
    return jsonify({"message": "Proyecto creado con éxito"}), 201


@app.route("/actualizar_proyecto/<project_id>", methods=["PUT"])
@token_required
@validar_datos(
    {"nombre": str, "descripcion": str, "fecha_inicio": str, "fecha_fin": str}
)
def actualizar_proyecto(user, project_id):
    """
    Endpoint para actualizar un proyecto existente.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: project_id
        required: true
        description: ID del proyecto a actualizar.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: body
        name: body
        required: true
        description: Datos a actualizar del proyecto.
        schema:
          type: object
          properties:
            nombre:
              type: string
              example: "Proyecto A Actualizado"
            descripcion:
              type: string
              example: "Descripción actualizada del proyecto A"
            fecha_inicio:
              type: string
              example: "2025-05-01"
            fecha_fin:
              type: string
              example: "2025-12-31"
    responses:
      200:
        description: Proyecto actualizado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Proyecto actualizado con éxito"
      404:
        description: Proyecto no encontrado.
    """
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

    message_log = "Usuario %s ha actualizado el proyecto" % user["nombre"]
    agregar_log(project_id, message_log)

    return jsonify({"message": "Proyecto actualizado con éxito"}), 200


@app.route("/asignar_usuario_proyecto", methods=["PATCH"])
@allow_cors
@token_required
def asignar_usuario_proyecto(user):
    """
    Endpoint para asignar un usuario a un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para asignar un usuario al proyecto.
        schema:
          type: object
          properties:
            proyecto_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            usuario:
              type: object
              properties:
                _id:
                  type: string
                  example: "64b8f3e2c9d1a2b3c4d5e6f8"
                nombre:
                  type: string
                  example: "Juan"
                role:
                  type: object
                  properties:
                    value:
                      type: string
                      example: "lider"
                    label:
                      type: string
                      example: "Líder"
    responses:
      200:
        description: Usuario asignado al proyecto con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Usuario asignado al proyecto con éxito"
      400:
        description: El usuario ya es miembro del proyecto.
    """
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    usuario = data["usuario"]
    fecha_hora_actual = datetime.utcnow()
    data["fecha_ingreso"] = fecha_hora_actual.strftime("%d/%m/%Y %H:%M")
    # Verificar si el usuario ya está en la lista de miembros
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    miembros = proyecto["miembros"]

    if any(
        miembro["usuario"]["_id"]["$oid"] == data["usuario"]["_id"]["$oid"]
        for miembro in miembros
    ):
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
    """
    Endpoint para eliminar un usuario de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para eliminar un usuario del proyecto.
        schema:
          type: object
          properties:
            proyecto_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            usuario_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f8"
    responses:
      200:
        description: Usuario eliminado del proyecto con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Usuario eliminado del proyecto con éxito"
      400:
        description: El usuario no es miembro del proyecto.
    """
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
    db_proyectos.update_one(
        {"_id": ObjectId(proyecto_id)},
        {"$pull": {"miembros": {"usuario._id.$oid": usuario_id}}},
    )
    message_log = f'{usuario["nombre"]} fue eliminado del proyecto por {user["nombre"]}'
    agregar_log(proyecto_id, message_log)
    return jsonify({"message": "Usuario eliminado del proyecto con éxito"}), 200


@app.route("/asignar_regla_distribucion", methods=["POST"])
@allow_cors
@token_required
def asignar_regla_distribucion(user):
    """
    Endpoint para asignar una regla de distribución a un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para asignar la regla de distribución.
        schema:
          type: object
          properties:
            proyecto_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            regla_distribucion:
              type: object
              additionalProperties:
                type: number
              example:
                lider: 50
                miembro: 50
    responses:
      200:
        description: Regla de distribución asignada con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Regla de distribución establecida con éxito"
      400:
        description: El proyecto ya cuenta con una regla de distribución.
    """
    data = request.get_json()
    proyecto_id = data["proyecto_id"]
    regla_distribucion = data["regla_distribucion"]
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})

    if 4 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 4)
        db_proyectos.update_one(
            {"_id": ObjectId(proyecto_id)},
            {"$set": {"status": new_status, "reglas": regla_distribucion}},
        )

        message_log = (
            f'{user["nombre"]} establecio las reglas de distribucion del proyecto'
        )
        agregar_log(proyecto_id, message_log)
        return jsonify({"message": "Regla de distribución establecida con éxito"}), 200

    return jsonify({"message": "El proyecto ya cuenta con regla de distribución"}), 200


@app.route("/crear_solicitud_regla_fija", methods=["POST"])
@token_required
def crear_solicitud_regla_fija(user):
    """
    Endpoint para crear una solicitud de regla fija.
    ---
    tags:
      - Reglas fijas
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para crear la solicitud de regla fija.
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Regla Fija 1"
            items:
              type: array
              items:
                type: object
                properties:
                  nombre_regla:
                    type: string
                    example: "Regla 1"
                  monto:
                    type: number
                    example: 1000
    responses:
      200:
        description: Solicitud de regla fija creada con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Solicitud de regla creada con éxito"
    """
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
    """
    Endpoint para eliminar una solicitud de regla fija.
    ---
    tags:
      - Reglas fijas
    parameters:
      - in: path
        name: id
        required: true
        description: ID de la solicitud de regla fija a eliminar.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
    responses:
      200:
        description: Solicitud de regla fija eliminada con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Solicitud de regla eliminada con éxito"
      400:
        description: No se pudo eliminar la solicitud de regla fija.
    """
    query = {"_id": ObjectId(id)}
    result = db_solicitudes.delete_one(query)
    if result.deleted_count == 1:
        return jsonify({"message": "Solicitud de regla eliminada con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


@app.route("/completar_solicitud_regla_fija/<string:id>", methods=["POST"])
@allow_cors
def completar_solicitud_regla_fija(id):
    """
    Endpoint para completar una solicitud de regla fija.
    ---
    tags:
      - Reglas fijas
    parameters:
      - in: path
        name: id
        required: true
        description: ID de la solicitud de regla fija a completar.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: body
        name: body
        required: true
        description: Resolución de la solicitud.
        schema:
          type: object
          properties:
            resolution:
              type: string
              example: "completed"
    responses:
      200:
        description: Solicitud de regla fija completada con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Solicitud de regla eliminada con éxito"
      400:
        description: No se pudo completar la solicitud de regla fija.
    """
    data = request.get_json()
    resolution = data["resolution"]
    query = {"_id": ObjectId(id)}
    result = db_solicitudes.update_one(query, {"$set": {"status": resolution}})
    if result.modified_count == 1:
        return jsonify({"message": "Solicitud de regla eliminada con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


@app.route("/asignar_balance", methods=["PATCH"])
@allow_cors
@token_required
def asignar_balance(user):
    """
    Endpoint para asignar balance a un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para asignar balance al proyecto.
        schema:
          type: object
          properties:
            project_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            balance:
              type: string
              example: "1000.00"
    responses:
      200:
        description: Balance asignado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Balance asignado con éxito"
    """
    data = request.get_json()
    proyecto_id = data["project_id"]
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    data_balance = string_to_int(data["balance"])
    balance = data_balance + int(proyecto["balance"])
    new_changes = {"balance": balance}

    if 1 not in proyecto["status"]["completado"]:
        new_status = actualizar_pasos(proyecto["status"], 1)
        new_changes["status"] = new_status
        new_changes["balance_inicial"] = balance

    db_proyectos.update_one({"_id": ObjectId(proyecto_id)}, {"$set": new_changes})
    data_acciones = {}
    data_acciones["project_id"] = ObjectId(proyecto_id)
    data_acciones["user"] = "Prueba"
    data_acciones["type"] = "Fondeo"
    data_acciones["amount"] = data_balance
    data_acciones["total_amount"] = balance
    db_acciones.insert_one(data_acciones)
    message_log = f'{user["nombre"]} agrego balance al proyecto por un monto de: ${int_to_string(data_balance)}'
    agregar_log(proyecto_id, message_log)

    return jsonify({"message": "Balance asignado con éxito"}), 200


@app.route("/roles", methods=["GET"])
@allow_cors
def roles():
    """
    Endpoint para obtener la lista de roles.
    ---
    tags:
      - Roles
    responses:
      200:
        description: Lista de roles obtenida con éxito.
        schema:
          type: array
          items:
            type: object
            properties:
              _id:
                type: string
                example: "64b8f3e2c9d1a2b3c4d5e6f7"
              nombre:
                type: string
                example: "Administrador"
              permisos:
                type: array
                items:
                  type: string
                example: ["crear_usuario", "editar_usuario"]
    """
    roles = db_roles.find({})
    list_cursor = list(roles)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(list_json)
    return list_json


@app.route("/mostrar_usuarios", methods=["GET"])
@allow_cors
def mostrar_usuarios():
    """
    Endpoint para obtener la lista de usuarios.
    ---
    tags:
      - Usuarios
    parameters:
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de usuarios por página.
        schema:
          type: integer
          example: 10
      - in: query
        name: text
        required: false
        description: Texto para filtrar usuarios por nombre o email.
        schema:
          type: string
          example: "Juan"
    responses:
      200:
        description: Lista de usuarios obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "64b8f3e2c9d1a2b3c4d5e6f7"
                  nombre:
                    type: string
                    example: "Juan"
                  email:
                    type: string
                    example: "juan@example.com"
            count:
              type: integer
              example: 100
    """
    params = request.args
    skip = int(params.get("page")) if params.get("page") else 0
    limit = params.get("limit") if params.get("limit") else 10
    text = params.get("text")

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
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(request_list=list_json, count=quantity)
    return list_json


@app.route("/mostrar_proyectos", methods=["GET"])
@allow_cors
@token_required
def mostrar_proyectos(user):
    """
    Endpoint para obtener la lista de proyectos.
    ---
    tags:
      - Proyectos
    parameters:
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de proyectos por página.
        schema:
          type: integer
          example: 10
    responses:
      200:
        description: Lista de proyectos obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "64b8f3e2c9d1a2b3c4d5e6f7"
                  nombre:
                    type: string
                    example: "Proyecto A"
                  descripcion:
                    type: string
                    example: "Descripción del proyecto A"
                  balance:
                    type: string
                    example: "1000.00"
            count:
              type: integer
              example: 50
    """
    # Obtener el número de página actual
    params = request.args
    skip = int(params.get("page")) if params.get("page") else 0
    limit = params.get("limit") if params.get("limit") else 10
    query = {
        "$or": [
            {"owner": user["sub"]},  # Check for project owner
            {
                "miembros": {
                    "$elemMatch": {  # Check for membership in any project
                        "usuario._id.$oid": user["sub"]  # Match user ID
                    }
                }
            },
        ]
    }
    dir(user)
    if user["role"] == "admin":
        query = {}

    # Optional: Projection to exclude password field
    projection = {"miembros.usuario.password": 0}  # Exclude password

    list_verification_request = (
        db_proyectos.find(query, projection=projection).skip(skip).limit(limit)
    )

    quantity = db_proyectos.count_documents(query)
    list_cursor = list(list_verification_request)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(request_list=list_json, count=quantity)
    return list_json


@app.route("/proyecto/<string:id>/acciones", methods=["GET"])
@allow_cors
def acciones_proyecto(id):
    """
    Endpoint para obtener las acciones de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: id
        required: true
        description: ID del proyecto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de acciones por página.
        schema:
          type: integer
          example: 10
    responses:
      200:
        description: Lista de acciones obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  type:
                    type: string
                    example: "Fondeo"
                  amount:
                    type: number
                    example: 1000
                  total_amount:
                    type: number
                    example: 5000
            count:
              type: integer
              example: 5
    """
    id = ObjectId(id)

    params = request.args
    skip = int(params.get("page")) if params.get("page") else 0
    limit = params.get("limit") if params.get("limit") else 10
    acciones = db_acciones.find({"project_id": id}).skip(skip * limit).limit(limit)
    acciones = map(map_to_doc, acciones)
    quantity = db_acciones.count_documents({"project_id": id}) / 10
    quantity = math.ceil(quantity)
    list_cursor = list(acciones)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(request_list=list_json, count=quantity)
    return list_json


@app.route("/proyecto/<string:id>", methods=["GET"])
@allow_cors
def proyecto(id):
    """
    Endpoint para obtener las acciones de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: id
        required: true
        description: ID del proyecto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de acciones por página.
        schema:
          type: integer
          example: 10
    responses:
      200:
        description: Lista de acciones obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  type:
                    type: string
                    example: "Fondeo"
                  amount:
                    type: number
                    example: 1000
                  total_amount:
                    type: number
                    example: 5000
            count:
              type: integer
              example: 5
    """
    # Convertir el ID a ObjectId
    id = ObjectId(id)

    # Buscar el producto por ID en la base de datos
    proyecto = db_proyectos.find_one({"_id": id})

    # Si el proyecto no existe, devolver un error 404
    if not proyecto:
        return jsonify({"error": "proyecto no encontrado"}), 404

    # Convertir el ObjectId a una cadena de texto
    proyecto["_id"] = str(proyecto["_id"])
    balance = int_to_string(proyecto["balance"])
    balance_inicial = int_to_string(proyecto["balance_inicial"])
    proyecto["balance"] = balance
    proyecto["owner"] = str(proyecto["owner"])
    proyecto["balance_inicial"] = balance_inicial

    # Devolver el proyecto como una respuesta JSON
    if "regla_fija" in proyecto:
        proyecto["regla_fija"]["_id"] = str(proyecto["regla_fija"]["_id"])
    print(proyecto)
    return jsonify(proyecto)


@app.route("/proyecto/<string:id>/documentos", methods=["GET"])
@allow_cors
def mostrar_documentos_proyecto(id):
    """
    Endpoint para obtener los documentos de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: id
        required: true
        description: ID del proyecto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de documentos por página.
        schema:
          type: integer
          example: 10
    responses:
      200:
        description: Lista de documentos obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "64b8f3e2c9d1a2b3c4d5e6f7"
                  descripcion:
                    type: string
                    example: "Presupuesto inicial"
                  monto:
                    type: string
                    example: "1000.00"
            count:
              type: integer
              example: 5
    """
    id = ObjectId(id)

    params = request.args
    skip = int(params.get("page")) if params.get("page") else 0
    limit = params.get("limit") if params.get("limit") else 10
    documentos = db_documentos.find({"project_id": id}).skip(skip * limit).limit(limit)
    # acciones = map(map_to_doc, acciones)
    quantity = db_documentos.count_documents({"project_id": id}) / 10
    quantity = math.ceil(quantity)
    list_cursor = list(documentos)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(request_list=list_json, count=quantity)
    return list_json


@app.route("/documento_crear", methods=["POST"])
@allow_cors
@token_required
def crear_presupuesto(user):
    """
    Endpoint para crear un presupuesto en un proyecto.
    ---
    tags:
      - Presupuestos
    parameters:
      - in: formData
        name: proyecto_id
        required: true
        description: ID del proyecto al que pertenece el presupuesto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: formData
        name: descripcion
        required: true
        description: Descripción del presupuesto.
        schema:
          type: string
          example: "Presupuesto inicial"
      - in: formData
        name: monto
        required: true
        description: Monto del presupuesto.
        schema:
          type: string
          example: "1000.00"
      - in: formData
        name: files
        required: false
        description: Archivos relacionados con el presupuesto.
        schema:
          type: array
          items:
            type: file
    responses:
      201:
        description: Presupuesto creado con éxito.
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "Archivos subidos exitosamente"
      400:
        description: Error en los datos enviados.
    """
    # Get project ID and other details from request
    project_id = request.form.get("proyecto_id")
    descripcion = request.form.get("descripcion")
    monto = request.form.get("monto")

    # Validate required fields
    if not project_id or not descripcion or not monto:
        return jsonify({"error": "Missing required fields"}), 400

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
        "project_id": ObjectId(project_id),
        "presupuesto_id": presupuesto_id,
        "descripcion": descripcion,
        # Replace with your string to int conversion function
        "monto": string_to_int(monto),
        "status": "new",
        "archivos": [],
    }

    # Get uploaded files from request
    archivos = request.files.getlist("files")

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
            presupuesto["archivos"].append(
                {"nombre": archivo.filename, "public_id": upload_result.id_}
            )
        else:
            error_messages.append(
                f"Error uploading file {archivo.filename}: {upload_result['error']}"
            )

    # Handle upload errors (if any)
    if error_messages:
        # Delete successfully uploaded files if any
        # for uploaded_file in uploaded_files:
        #     api.destroy(public_id=uploaded_file)

        # Return error response with messages
        return jsonify({"error": error_messages}), 400

    # Insert presupuesto object into database
    result = db_documentos.insert_one(presupuesto)

    # Handle database errors
    if not result.acknowledged:
        return jsonify({"error": "Error saving presupuesto"}), 500

    # Log document creation
    message_log = (
        f'{user["nombre"]} agrego el presupuesto {descripcion} con un monto de ${monto}'
    )
    agregar_log(project_id, message_log)

    # Return success response
    return jsonify({"mensaje": "Archivos subidos exitosamente"}), 201


@app.route("/documento_cerrar", methods=["POST"])
@allow_cors
@token_required
def cerrar_presupuesto(user):
    """
    Endpoint para cerrar un presupuesto en un proyecto.
    ---
    tags:
      - Presupuestos
    parameters:
      - in: formData
        name: proyecto_id
        required: true
        description: ID del proyecto al que pertenece el presupuesto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: formData
        name: doc_id
        required: true
        description: ID del documento del presupuesto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f8"
      - in: formData
        name: monto
        required: true
        description: Monto aprobado del presupuesto.
        schema:
          type: string
          example: "500.00"
      - in: formData
        name: description
        required: true
        description: Descripción del cierre del presupuesto.
        schema:
          type: string
          example: "Cierre del presupuesto inicial"
      - in: formData
        name: files
        required: false
        description: Archivos relacionados con el cierre del presupuesto.
        schema:
          type: array
          items:
            type: file
    responses:
      201:
        description: Presupuesto cerrado con éxito.
        schema:
          type: object
          properties:
            mensaje:
              type: string
              example: "proyecto ajustado exitosamente"
      400:
        description: Error en los datos enviados.
    """

    id = request.form.get("proyecto_id")
    doc_id = request.form.get("doc_id")
    data_balance = request.form.get("monto")
    data_descripcion = request.form.get("description")
    carpeta_proyecto = os.path.join("files", id)

    # Crear la carpeta del proyecto si no existe
    if not os.path.exists(carpeta_proyecto):
        os.makedirs(carpeta_proyecto)
    # Actualizas balance
    proyecto = db_proyectos.find_one({"_id": ObjectId(id)})
    data_balance = string_to_int(data_balance)
    proyecto_balance = int(proyecto["balance"])
    balance = proyecto_balance - data_balance
    db_proyectos.update_one({"_id": ObjectId(id)}, {"$set": {"balance": balance}})

    # Agregas la accion a las actividades
    data_acciones = {}
    data_acciones["project_id"] = ObjectId(id)
    data_acciones["user"] = user["nombre"]
    data_acciones["type"] = f"Retiro {data_descripcion}"
    data_acciones["amount"] = data_balance * -1
    data_acciones["total_amount"] = balance
    db_acciones.insert_one(data_acciones)

    # Cierras el presupuesto

    archivos = request.files.getlist("files")
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
        archivos_guardados.append(
            {
                "nombre": nombre_archivo,
                "ruta": os.path.join(carpeta_presupuesto, nombre_archivo),
            }
        )

    db_documentos.update_one(
        {"_id": ObjectId(doc_id)},
        {
            "$set": {
                "status": "finished",
                "monto_aprobado": data_balance,
                "archivos_aprobado": archivos_guardados,
            }
        },
    )

    message_log = f'{user["nombre"]} cerro el presupuesto {data_descripcion} con un monto de ${int_to_string(data_balance)}'
    agregar_log(id, message_log)

    return jsonify({"mensaje": "proyecto ajustado exitosamente"}), 201


@app.route("/documento_eliminar", methods=["POST"])
@allow_cors
@token_required
def eliminar_presupuesto(user):
    """
    Endpoint para eliminar un presupuesto de un proyecto.
    ---
    tags:
      - Presupuestos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para eliminar el presupuesto.
        schema:
          type: object
          properties:
            budget_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f8"
            project_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
    responses:
      200:
        description: Presupuesto eliminado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Solicitud de regla eliminada con éxito"
      401:
        description: El presupuesto está finalizado y no se puede eliminar.
      404:
        description: Presupuesto no encontrado.
      400:
        description: No se pudo eliminar el presupuesto.
    """
    data = request.get_json()
    presupuesto_id = data["budget_id"]
    id = data["project_id"]
    documento = db_documentos.find_one({"_id": ObjectId(presupuesto_id)})
    if documento is None:
        return jsonify({"message": "Presupuesto no encontrado"}), 404

    descripcion = documento["descripcion"]
    monto = documento["monto"]
    if documento["status"] == "finished":
        return jsonify(
            {"mensaje": "Presupuesto esta finalizado, no se puede eliminar"}
        ), 401

    result = db_documentos.delete_one({"_id": ObjectId(presupuesto_id)})
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
    """
    Endpoint para eliminar un presupuesto de un proyecto.
    ---
    tags:
      - Presupuestos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para eliminar el presupuesto.
        schema:
          type: object
          properties:
            budget_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f8"
            project_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
    responses:
      200:
        description: Presupuesto eliminado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Solicitud de regla eliminada con éxito"
      401:
        description: El presupuesto está finalizado y no se puede eliminar.
      404:
        description: Presupuesto no encontrado.
      400:
        description: No se pudo eliminar el presupuesto.
    """
    data = request.get_json()
    id = data["proyecto_id"]
    documento = db_proyectos.find_one({"_id": ObjectId(id)})
    if documento is None:
        return jsonify({"message": "Proyecto no encontrado"}), 404

    result = db_proyectos.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 1:
        return jsonify({"message": "Proyecto eliminado con éxito"}), 200
    else:
        return jsonify({"message": "No se pudo eliminar la regla"}), 400


@app.route("/finalizar_proyecto", methods=["POST"])
@allow_cors
@token_required
def finalizar_proyecto(user):
    """
    Endpoint para finalizar un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para finalizar el proyecto.
        schema:
          type: object
          properties:
            proyecto_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
    responses:
      200:
        description: Proyecto finalizado con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Proyecto finalizado con éxito"
      404:
        description: Proyecto no encontrado.
      400:
        description: Error en los datos enviados.
    """
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
        return jsonify(
            {"message": "La suma de los porcentajes de reglas debe ser igual a 100"}
        ), 401
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
            budgeted_members.append({"role": member_role, "budget": member_budget})
        else:
            print(
                f"Warning: No rule found for role '{member_role_value}'. Budget not assigned."
            )
    new_status = actualizar_pasos(proyecto["status"], 6)
    new_status["finished"] = True
    db_proyectos.update_one(
        {"_id": ObjectId(proyecto_id)},
        {"$set": {"status": new_status, "distribucion_recursos": budgeted_members}},
    )
    proyecto = db_proyectos.find_one({"_id": ObjectId(proyecto_id)})
    message_log = f'{user["nombre"]} finalizó el proyecto'
    agregar_log(proyecto_id, message_log)

    return jsonify({"message": "Proyecto finalizado con éxito"}), 200


@app.route("/proyecto/<string:id>/logs", methods=["GET"])
@allow_cors
def obtener_logs(id):
    """
    Endpoint para obtener los logs de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: id
        required: true
        description: ID del proyecto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de logs por página.
        schema:
          type: integer
          example: 10
    responses:
      200:
        description: Lista de logs obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  id_proyecto:
                    type: string
                    example: "64b8f3e2c9d1a2b3c4d5e6f7"
                  mensaje:
                    type: string
                    example: "Usuario X realizó una acción"
                  fecha_creacion:
                    type: string
                    example: "2025-04-22T12:00:00Z"
            count:
              type: integer
              example: 5
    """
    id = ObjectId(id)

    params = request.args
    skip = int(params.get("page")) if params.get("page") else 0
    limit = params.get("limit") if params.get("limit") else 10
    acciones = db_logs.find({"id_proyecto": id}).skip(skip * limit).limit(limit)
    quantity = db_logs.count_documents({"id_proyecto": id}) / 10
    quantity = math.ceil(quantity)

    list_cursor = list(acciones)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(request_list=list_json, count=quantity)
    return list_json, 200
    # return jsonify(list_json), 200


@app.route("/mostrar_solicitudes", methods=["GET"])
@allow_cors
@token_required
def mostrar_solicitudes(user):
    """
    Endpoint para obtener la lista de solicitudes.
    ---
    tags:
      - Solicitudes
    parameters:
      - in: query
        name: page
        required: false
        description: Número de página para la paginación.
        schema:
          type: integer
          example: 1
      - in: query
        name: limit
        required: false
        description: Límite de solicitudes por página.
        schema:
          type: integer
          example: 10
    responses:
      200:
        description: Lista de solicitudes obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "64b8f3e2c9d1a2b3c4d5e6f7"
                  nombre:
                    type: string
                    example: "Solicitud 1"
                  status:
                    type: string
                    example: "new"
            count:
              type: integer
              example: 50
    """
    # Obtener el número de página actual
    params = request.args
    skip = int(params.get("page")) if params.get("page") else 0
    limit = params.get("limit") if params.get("limit") else 10
    # query = {"_id": ObjectId(request_id)}
    list_verification_request = db_solicitudes.find({}).skip(skip * limit).limit(limit)
    quantity = db_solicitudes.count_documents({})
    list_cursor = list(list_verification_request)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    # Remover las barras invertidas
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(request_list=list_json, count=quantity)
    return list_json


@app.route("/mostrar_reglas_fijas", methods=["GET"])
@allow_cors
@token_required
def mostrar_reglas_fijas(user):
    """
    Endpoint para obtener la lista de reglas fijas completadas.
    ---
    tags:
      - Reglas fijas
    responses:
      200:
        description: Lista de reglas fijas obtenida con éxito.
        schema:
          type: object
          properties:
            request_list:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "64b8f3e2c9d1a2b3c4d5e6f7"
                  nombre:
                    type: string
                    example: "Regla Fija 1"
                  status:
                    type: string
                    example: "completed"
    """
    list_request = db_solicitudes.find({"status": "completed"})
    list_cursor = list(list_request)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    list_json = json.loads(list_dump.replace("\\", ""))
    list_json = jsonify(
        request_list=list_json,
    )

    return list_json, 200


@app.route("/proyecto/<string:id>/movimientos/descargar", methods=["GET"])
@allow_cors
def descargar_movimientos(id):
    """
    Endpoint para descargar los movimientos de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: id
        required: true
        description: ID del proyecto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
      - in: query
        name: formato
        required: false
        description: Formato de descarga (csv o json).
        schema:
          type: string
          example: "csv"
    responses:
      200:
        description: Archivo descargado con éxito.
        content:
          application/json:
            schema:
              type: string
              example: "Archivo descargado con éxito"
      400:
        description: Formato no válido.
    """
    id_proyecto = ObjectId(id)

    # 1. Recuperar los movimientos del proyecto desde la base de datos
    movimientos = db_acciones.find({"project_id": id_proyecto})
    movimientos_lista = list(movimientos)

    # 2. Determinar el formato de descarga (CSV o JSON)
    formato = request.args.get("formato", "csv").lower()  # Por defecto a CSV

    if formato == "csv":
        return generar_csv(movimientos_lista)
    elif formato == "json":
        return generar_json(movimientos_lista)
    else:
        return jsonify({"error": "Formato no válido. Use 'csv' o 'json'."}), 400

@app.route("/proyecto/<string:id>/fin", methods=["GET"])
@allow_cors
def mostrar_finalizacion(id):
    """
    Endpoint para obtener los datos finales de un proyecto.
    ---
    tags:
      - Proyectos
    parameters:
      - in: path
        name: id
        required: true
        description: ID del proyecto.
        schema:
          type: string
          example: "64b8f3e2c9d1a2b3c4d5e6f7"
    responses:
      200:
        description: Datos finales del proyecto obtenidos con éxito.
        schema:
          type: object
          properties:
            logs:
              type: array
              items:
                type: object
                properties:
                  mensaje:
                    type: string
                    example: "Usuario X realizó una acción"
                  fecha_creacion:
                    type: string
                    example: "2025-04-22T12:00:00Z"
            documentos:
              type: array
              items:
                type: object
                properties:
                  descripcion:
                    type: string
                    example: "Presupuesto inicial"
                  monto:
                    type: string
                    example: "1000.00"
            movimientos:
              type: array
              items:
                type: object
                properties:
                  type:
                    type: string
                    example: "Fondeo"
                  amount:
                    type: number
                    example: 1000
    """
    id = ObjectId(id)
    movs = db_acciones.find({"project_id": id})
    docs = db_documentos.find({"project_id": id})
    logs = db_logs.find({"id_proyecto": id})

    movs_cursor = list(movs)
    movs_dump = json_util.dumps(movs_cursor)
    movs_json = json.loads(movs_dump.replace("\\", ""))

    docs_cursor = list(docs)
    docs_dump = json_util.dumps(docs_cursor)
    docs_json = json.loads(docs_dump.replace("\\", ""))

    logs_cursor = list(logs)
    logs_dump = json_util.dumps(logs_cursor)
    list_json = json.loads(logs_dump.replace("\\", ""))
    data_response = jsonify(logs=list_json, documentos=docs_json, movimientos=movs_json)
    return data_response, 200


@app.route("/asignar_regla_fija/", methods=["POST"])
@allow_cors
@token_required
def asignar_regla_fija(user):
    """
    Endpoint para asignar una regla fija a un proyecto.
    ---
    tags:
      - Reglas fijas
    parameters:
      - in: body
        name: body
        required: true
        description: Datos para asignar la regla fija.
        schema:
          type: object
          properties:
            proyecto_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f7"
            regla_id:
              type: string
              example: "64b8f3e2c9d1a2b3c4d5e6f8"
    responses:
      200:
        description: Regla fija asignada con éxito.
        schema:
          type: object
          properties:
            message:
              type: string
              example: "La regla se asignó correctamente"
      404:
        description: Proyecto o regla fija no encontrada.
      400:
        description: Error en los datos enviados.
    """
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
        return jsonify(
            {"message": "Antes de asignar regla tienes que asignar balance"}
        ), 400

    # Descontar proyecto
    for x in regla["reglas"]:
        proyecto_balance = int(proyecto["balance"])
        balance = proyecto_balance - x["monto"]
        db_proyectos.update_one(
            {"_id": ObjectId(proyecto_id)}, {"$set": {"balance": balance}}
        )

        # Agregas la accion a las actividades

        data_acciones = {}
        data_acciones["project_id"] = ObjectId(proyecto_id)
        data_acciones["user"] = user["nombre"]
        data_acciones["type"] = x["nombre_regla"]
        data_acciones["amount"] = x["monto"] * -1
        data_acciones["total_amount"] = balance
        db_acciones.insert_one(data_acciones)

        message_log = f'{user["nombre"]} asigno la regla: {regla["nombre"]} con el item {x["nombre_regla"]} con un monto de ${int_to_string(x["monto"])}'
        agregar_log(proyecto_id, message_log)

    # Asignar la regla
    new_status = actualizar_pasos(proyecto["status"], 5)

    db_proyectos.update_one(
        {"_id": ObjectId(proyecto_id)},
        {"$set": {"regla_fija": regla, "status": new_status}},
    )

    # Dar respuesta que todo esta ok
    return jsonify({"message": "La regla se asigno correctamente"}), 200


@app.route("/", methods=["GET"])
@allow_cors
def index():
    """
    Endpoint para saber si el servidor está aceptando requests.
    ---
    responses:
      200:
        description: retorna un string llamado pong porque le estás haciendo ping
        schema:
            type: string
            example: "pong"
    """
    return "pong"


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
