from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from ..app import mongo, bcrypt
from util.decorators import validar_datos, token_required, allow_cors
from util.utils import generar_token

bp = Blueprint('users', __name__)

@bp.route('/registrar', methods=['POST'])
@validar_datos({'nombre': str, 'email': str, 'password': str})
@token_required
def registrar(user):
    data = request.get_json()
    hashed_pw = bcrypt.generate_password_hash(data['password'])
    data['password'] = hashed_pw
    mongo.db.usuarios.insert_one(data)
    return jsonify({'message': 'Usuario registrado con rxito'}), 201


@bp.route('/login', methods=['POST'])
@validar_datos({'email': str, 'password': str})
def login():
    data = request.get_json()
    usuario = mongo.db.usuarios.find_one({'email': data['email']})
    if usuario and bcrypt.check_password_hash(usuario['password'], data['password']):
        token = generar_token(usuario, current_app.config['SECRET_KEY'])
        return jsonify({
            'token': token,
            'email': data['email'],
            'id': str(usuario['_id']),
            'nombre': usuario['nombre'],
            'role': 'admin' if usuario.get('is_admin') else 'usuario'
        }), 200
    return jsonify({'message': 'Credenciales inválidas'}), 401


@bp.route('/olvido_contraseña', methods=['POST'])
@token_required
def olvido_contraseña(user):
    data = request.get_json()
    usuario = mongo.db.usuarios.find_one({'email': data['email']})
    if usuario:
        return jsonify({'message': 'Se ha enviado un email electrónico para restablecer la contraseña'}), 200
    return jsonify({'message': 'El email electrónico no está registrado'}), 404


@bp.route('/editar_usuario/<id_usuario>', methods=['PUT'])
@token_required
def editar_usuario(id_usuario):
    data = request.get_json()
    mongo.db.usuarios.update_one({'_id': ObjectId(id_usuario)}, {'$set': data})
    return jsonify({'message': 'Información de usuario actualizada con éxito'}), 200


@bp.route('/eliminar_usuario', methods=['POST'])
@token_required
def eliminar_usuario(user):
    data = request.get_json()
    id_usuario = data['id_usuario']
    result = mongo.db.usuarios.delete_one({'_id': ObjectId(id_usuario)})
    if result.deleted_count == 1:
        return jsonify({'message': 'Usuario eliminado éxitosamente'}), 200
    return jsonify({'message': 'No se pudo eliminar el usuario'}), 400


@bp.route('/cambiar_rol_usuario', methods=['POST'])
@allow_cors
@validar_datos({'id': str, 'nuevo_rol': bool})
@token_required
def cambiar_rol_usuario(user):
    data = request.get_json()
    usuario_id = data.get('id')
    nuevo_rol = data.get('nuevo_rol')
    usuario = mongo.db.usuarios.find_one({'_id': ObjectId(usuario_id)})
    if not usuario:
        return jsonify({'message': 'Usuario no encontrado'}), 404
    mongo.db.usuarios.update_one({'_id': ObjectId(usuario_id)}, {'$set': {'is_admin': nuevo_rol}})
    return jsonify({'message': 'Rol actualizado correctamente'}), 200
