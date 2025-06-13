from flask import Blueprint, request, jsonify
from datetime import datetime
from bson import ObjectId
from ..app import mongo, agregar_log
from util.decorators import token_required, validar_datos, allow_cors
from util.utils import actualizar_pasos

bp = Blueprint('projects', __name__)

@bp.route('/crear_proyecto', methods=['POST'])
@token_required
@validar_datos({'nombre': str, 'descripcion': str, 'fecha_inicio': str, 'fecha_fin': str})
def crear_proyecto(user):
    current_user = user['sub']
    data = request.get_json()
    data['miembros'] = []
    data['balance'] = 0
    data['balance_inicial'] = 0
    data['status'] = {'actual': 1, 'completado': []}
    data['show'] = {'status': False}
    data['owner'] = ObjectId(current_user)
    data['user'] = user
    project = mongo.db.proyectos.insert_one(data)
    message_log = 'Usuario %s ha creado el proyecto' % user['nombre']
    agregar_log(project.inserted_id, message_log)
    return jsonify({'message': 'Proyecto creado con éxito'}), 201


@bp.route('/actualizar_proyecto/<project_id>', methods=['PUT'])
@token_required
@validar_datos({'nombre': str, 'descripcion': str, 'fecha_inicio': str, 'fecha_fin': str})
def actualizar_proyecto(user, project_id):
    data = request.get_json()
    project = mongo.db.proyectos.find_one({'_id': ObjectId(project_id)})
    if not project:
        return jsonify({'message': 'Proyecto no encontrado'}), 404
    for key, value in data.items():
        project[key] = value
    mongo.db.proyectos.update_one({'_id': ObjectId(project_id)}, {'$set': project})
    message_log = 'Usuario %s ha actualizado el proyecto' % user['nombre']
    agregar_log(project_id, message_log)
    return jsonify({'message': 'Proyecto actualizado con éxito'}), 200


@bp.route('/asignar_usuario_proyecto', methods=['PATCH'])
@allow_cors
@token_required
def asignar_usuario_proyecto(user):
    data = request.get_json()
    proyecto_id = data['proyecto_id']
    usuario = data['usuario']
    fecha_hora_actual = datetime.utcnow()
    data['fecha_ingreso'] = fecha_hora_actual.strftime('%d/%m/%Y %H:%M')
    proyecto = mongo.db.proyectos.find_one({'_id': ObjectId(proyecto_id)})
    miembros = proyecto['miembros']
    if any(miembro['usuario']['_id']['$oid'] == data['usuario']['_id']['$oid'] for miembro in miembros):
        return jsonify({'message': 'El usuario ya es miembro del proyecto'}), 400
    new_status = {}
    query = {'$push': {'miembros': data}}
    if 2 not in proyecto['status']['completado']:
        new_status = actualizar_pasos(proyecto['status'], 2)
    if data['role']['value'] == 'lider':
        new_status = actualizar_pasos(proyecto['status'], 3)
    if new_status:
        query['$set'] = {'status': new_status}
    mongo.db.proyectos.update_one({'_id': ObjectId(proyecto_id)}, query)
    message_log = f"{usuario['nombre']} fue asignado al proyecto por {user['nombre']} con el rol {data['role']['label']}"
    agregar_log(proyecto_id, message_log)
    return jsonify({'message': 'Usuario asignado al proyecto con éxito'}), 200
