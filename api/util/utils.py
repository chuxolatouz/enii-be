from datetime import datetime, timedelta
from jose import jwt
from bson import ObjectId, json_util
from io import StringIO, BytesIO
from flask import send_file
from util.generar_acta_inicio import generar_acta_inicio_pdf
from util.backblaze import BUCKET_ID, upload_file, auth_b2_account
import csv  # Para CSV
import json


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
    string_float = string_float.replace(".", ",")
    return string_float


def string_to_int(string_float):
    """
    Recibe un string que representa un número en formato de punto flotante.
    Devuelve un entero que representa el número multiplicado por 100.
    """
    # Reemplazamos la coma por un punto para poder convertirlo a flotante
    float_number = float(string_float.replace(",", "."))
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
        "role": "admin" if usuario.get("is_admin") else "usuario",
        "exp": int(thirty_days_later.timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def map_to_doc(document):
    document["amount"] = int_to_string(document["amount"])
    document["total_amount"] = int_to_string(document["total_amount"])
    return document


def actualizar_pasos(status, paso, proyecto=None):
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
    """
    Esta funcion actualiza el status de un proyecto dependiendo de la posicion en la que se encuentre.
    Si se alcanza el paso 6 (proyecto configurado) y no tiene acta de inicio, se genera y guarda.
    """
    new_status = status.copy()

    if paso > new_status["actual"]:
        new_status["actual"] = paso
    if paso == new_status["actual"]:
        new_status["actual"] = paso + 1

    if paso not in new_status["completado"]:
        new_status["completado"].append(paso)

    acta_inicio = None

    if new_status["actual"] >= 6 and proyecto and not proyecto.get("acta_inicio"):
        try:
            pdf_bytes = generar_acta_inicio_pdf(proyecto)
            api = auth_b2_account()
            filename = f"actas/acta_inicio_{str(proyecto['_id'])}.pdf"
            upload_result = upload_file(api, BUCKET_ID, BytesIO(pdf_bytes), filename)
            acta_inicio = {
                "fecha": datetime.utcnow(),
                "documento_url": upload_result.download_url,
            }
        except Exception as e:
            print(f"[ERROR] Falló la generación del acta de inicio: {e}")

    return new_status, acta_inicio



def generar_csv(movimientos):
    si = StringIO()  # Usar StringIO en lugar de BytesIO para texto
    cw = csv.writer(si)

    # Escribir la fila de encabezado
    cw.writerow([
        "Tipo",
        "Usuario",
        "Monto",
        "Monto Total",
        # ... Agrega aquí otros campos que desees incluir
    ])

    # Escribir los datos de los movimientos
    for mov in movimientos:
        cw.writerow([
            mov.get("type", ""),
            mov.get("user", ""),
            int_to_string(mov.get("amount", 0)),  # Formatear el monto
            int_to_string(mov.get("total_amount", 0)),  # Formatear el monto total
            # ... Agrega aquí otros campos que desees incluir
        ])

    output = si.getvalue()
    return send_file(
        BytesIO(output.encode()),  # Convertir a BytesIO
        mimetype="text/csv",
        as_attachment=True,
        download_name="movimientos_proyecto.csv"  # Nombre del archivo
    )

def generar_json(movimientos):
    # Convertir los ObjectId a cadenas y formatear los montos
    movimientos_serializables = []
    for mov in movimientos:
        mov_serializable = {}
        for key, value in mov.items():
            if isinstance(value, ObjectId):
                mov_serializable[key] = str(value)
            elif key in ("amount", "total_amount"):
                mov_serializable[key] = int_to_string(value)
            else:
                mov_serializable[key] = value
        movimientos_serializables.append(mov_serializable)

    json_output = json.dumps(movimientos_serializables, ensure_ascii=False, default=json_util.default)
    return send_file(
        BytesIO(json_output.encode('utf-8')),
        mimetype="application/json",
        as_attachment=True,
        download_name="movimientos_proyecto.json"
    )
