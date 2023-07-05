from flask import make_response, request, jsonify, current_app
import jwt
from functools import wraps

def allow_cors(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        resp = make_response(f(*args, **kwargs))
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    return decorated

def validar_datos(schema):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            for field, datatype in schema.items():
                if field not in data:
                    return jsonify({"message": f"El campo '{field}' es requerido"}), 400
                if not isinstance(data[field], datatype):
                    return jsonify({"message": f"El campo '{field}' debe ser de tipo {datatype.__name__}"}), 400
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Definir una función decoradora para proteger rutas que requieren autenticación
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token no proporcionado"}), 403

        try:            
            token = token.split()[1]
            data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=['HS256'])
            user_id = data["sub"]
        except:
            return jsonify({"message": "Token no es válido o ha expirado"}), 403

        return f(user_id, *args, **kwargs)

    return decorated
