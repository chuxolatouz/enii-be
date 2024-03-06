from datetime import datetime, timedelta
from jose import jwt


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


def generar_token(usuario, secret):
    now = datetime.now()
    thirty_days_later = now + timedelta(days=30)
    payload = {
        "sub": str(usuario["_id"]),
        "email": usuario["email"],
        "nombre": usuario["nombre"],
        "exp": int(thirty_days_later.timestamp())
    }
    token = jwt.encode(payload, secret, algorithm='HS256')
    print(token)
    return token


def map_to_doc(document):
    document['amount'] = int_to_string(document["amount"])
    document['total_amount'] = int_to_string(document["total_amount"])
    return document


def actualizar_pasos(status, paso):
    "Esta funcion actualiza el status de un proyecto dependiendo de la posicion en la que se encuentre"
    "Recibe el objecto status y el paso a actualizar"
    "El objeto status se representa como {'actual': 3, 'completado': [1, 2]}"
    "En este ejemplo el paso actual a continuar es Agregar Lider"
    "Segun ese orden ya se agregó un usuario y se agregó balance al proyecto"
    "-----------------------------"
    "Status 1: Agregar Balance"
    "Status 2: Agregar usuarios"
    "Status 3: Agregar Lider"
    "Status 4: Agregar Regla de Distribucion"
    "Status 5: Agregar Regla fija"
    "Status 6: Configurado"
    "-----------------------"
    new_status = status
    if paso > status["actual"]:
        new_status["actual"] = paso
    if paso == status["actual"]:
        new_status["actual"] = paso + 1

    if paso not in status["completado"]:
        new_status["completado"].append(paso)

    return new_status


def auth_account(b2_api):
    auth = b2_api.authorize_account("production", "0054addcef284d30000000002",
                                    "K005xSlLQhiwP7QZsQOXxe7k2HH+WHk")
    return auth
