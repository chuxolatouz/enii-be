from flask import Blueprint, request, jsonify
from bson import json_util
import json
import random
import string
from ..app import mongo
from util.decorators import allow_cors, validar_datos, token_required

bp = Blueprint('categorias', __name__)

@bp.route('/mostrar_categorias', methods=['GET'])
@allow_cors
@token_required
def obtener_categorias(user):
    search_text = request.args.get('text')
    if search_text:
        cursor = mongo.db.categorias.find({'nombre': {'$regex': search_text, '$options': 'i'}})
    else:
        cursor = mongo.db.categorias.find()
    list_cursor = list(cursor)
    list_dump = json.dumps(list_cursor, default=json_util.default, ensure_ascii=False)
    list_json = json.loads(list_dump.replace('\\', ''))
    return jsonify(list_json), 200


@bp.route('/categorias', methods=['POST'])
@allow_cors
@validar_datos({'nombre': str})
@token_required
def crear_categorias(user):
    data = request.get_json()
    nombre = data['nombre']
    color = ''.join(random.choices(string.hexdigits[:-6], k=6))
    categoria = {'nombre': nombre, 'color': color}
    categoria_insertada = mongo.db.categorias.insert_one(categoria)
    categoria['id'] = str(categoria_insertada.inserted_id)
    return jsonify(categoria), 201
