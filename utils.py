from datetime import datetime
import jwt


def int_to_string(int_number):
    """
    Recibe un entero que representa un número multiplicado por 100.
    Devuelve una cadena de caracteres que representa el número en formato de punto flotante con dos decimales.
    """
    # Dividimos el número por 100 y lo convertimos a un número de punto flotante
    float_number = float(int_number) / 100
    # Formateamos el número como una cadena de caracteres con dos decimales
    string_float = "{:.2f}".format(float_number)
    # Reemplazamos el punto por una coma para el formato deseado
    string_float = string_float.replace('.', ',')
    return string_float


def string_to_int(string_float):
    """
    Recibe un string que representa un número en formato de punto flotante.
    Devuelve un entero que representa el número multiplicado por 100.
    """
    # Reemplazamos la coma por un punto para poder convertirlo a flotante
    float_number = float(string_float.replace(',', '.'))
    # Multiplicamos el número por 100 y lo convertimos a entero
    int_number = int(float_number * 100)
    return int_number


def generar_token(id_usuario, secret):
    payload = {
        "sub": str(id_usuario),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def map_to_doc(document):
    document['amount'] = int_to_string(document["amount"])
    document['total_amount'] = int_to_string(document["total_amount"])
    return document


def actualizar_pasos(status, paso):
    new_status = status
    if paso > status["actual"]:
        new_status["actual"] = paso
    if paso == status["actual"]:
        new_status["actual"] = paso + 1

    import pdb
    pdb.set_trace()
    if paso not in status["completado"]:
        new_status["completado"].append(paso)

    return new_status
