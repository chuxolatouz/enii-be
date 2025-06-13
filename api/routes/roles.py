from flask import Blueprint, request, jsonify
from bson import ObjectId, json_util
from ..app import mongo
from util.decorators import token_required, allow_cors

bp = Blueprint('roles', __name__)

@bp.route('/crear_rol', methods=['POST'])
@token_required
def crear_rol():
    data = request.get_json()
    mongo.db.roles.insert_one(data)
    return jsonify({'message': 'Rol creado con éxito'}), 201


@bp.route('/asignar_rol', methods=['PATCH'])
@token_required
def asignar_rol():
    data = request.get_json()
    user_id = data['user_id']
    rol_id = data['rol_id']
    mongo.db.usuarios.update_one({'_id': ObjectId(user_id)}, {'$set': {'rol_id': ObjectId(rol_id)}})
    return jsonify({'message': 'Rol asignado con éxito'}), 200


@bp.route('/roles', methods=['GET'])
@allow_cors
@token_required
def roles(user):
    roles = mongo.db.roles.find({})
    list_cursor = list(roles)
    list_dump = json_util.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    list_json = json.loads(list_dump.replace('\\', ''))
    return jsonify(list_json)
