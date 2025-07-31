import unittest
from datetime import datetime, timezone
from io import BytesIO
from api.index import db_documentos
from api.index import app

class PresupuestoTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        # Crear usuario y obtener token
        self.user = {
            "nombre": "Admin",
            "apellido": "Test",
            "email": "admin_presupuesto@example.com",
            "password": "admin123",
            "is_admin": True
        }
        self.client.post("/registrar", json=self.user)

        login_data = {
            "email": self.user["email"],
            "password": self.user["password"]
        }
        res = self.client.post("/login", json=login_data)
        self.token = res.get_json().get("token")
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

        # Crear un proyecto para asociar al presupuesto
        proyecto = {
            "nombre": "Proyecto Presupuesto Test",
            "descripcion": "Proyecto usado para test de presupuesto.",
            "fecha_inicio": datetime.now(timezone.utc),
            "fecha_fin": datetime.now(timezone.utc)
        }
        res = self.client.post("/crear_proyecto", json=proyecto, headers=self.auth_headers)
        self.proyecto_id = res.get_json().get("proyecto_id") or res.get_json().get("_id")

        self.client.post("/asignar_balance", json={
            "proyecto_id": self.proyecto_id,
            "balance": 10000
        }, headers=self.auth_headers)

    def test_01_crear_presupuesto(self):
        presupuesto = {
            "proyecto_id": self.proyecto_id,
            "monto": 5000,
            "descripcion": "Presupuesto inicial de prueba"
        }
        file_data = {
            "files": (BytesIO(b"contenido de prueba"), "prueba.pdf")
        }
        form_data = {
            "proyecto_id": self.proyecto_id,
            "descripcion": "Presupuesto con archivo",
            "monto": "2000.00",

        }
        print("Presupuesto a crear:", presupuesto)
        res = self.client.post(
            "/documento_crear",
            data={**form_data, **file_data},
            headers=self.auth_headers,
            content_type='multipart/form-data'
        )
        print("Response from creating budget:", res.get_json())
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("mensaje", data)
        self.assertEqual(data["mensaje"], "Archivos subidos exitosamente")

    def test_02_cerrar_presupuesto(self):
        # Primero crear el documento
        crear_data = {
            "proyecto_id": self.proyecto_id,
            "descripcion": "Presupuesto para cerrar",
            "monto": "100",
            "objetivo_especifico": "Compra"
        }
        res = self.client.post(
            "/documento_crear",
            data=crear_data,
            headers=self.auth_headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 201)

        data = res.get_json()
        
        
        balance = {
            "project_id": self.proyecto_id,
            "balance": "1000",
            "descripcion": "Aporte inicial al proyecto."
        }
        
        res2 = self.client.patch("/asignar_balance", json=balance, headers=self.auth_headers)
        self.assertEqual(res2.status_code, 200)
        # Buscar el doc_id del presupuesto recién creado
        

        doc = db_documentos.find_one({"descripcion": "Presupuesto para cerrar"})
        self.assertIsNotNone(doc)
        doc_id = str(doc["_id"])

        cerrar_data = {
            "proyecto_id": self.proyecto_id,
            "doc_id": doc_id,
            "monto": "1",
            "description": "Cierre automático por test",
            "referencia": "REF12345",
            "monto_transferencia": "1",
            "banco": "TestBank",
            "cuenta_contable": "CC123456789"
        }

        file_data = {
            "files": (BytesIO(b"archivo cierre"), "cierre.pdf")
        }

        res = self.client.post(
            "/documento_cerrar",
            data={**cerrar_data, **file_data},
            headers=self.auth_headers,
            content_type='multipart/form-data'
        )
        print("Response from cerrar presupuesto:", res.get_json())
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("mensaje", data)
        self.assertEqual(data["mensaje"], "proyecto ajustado exitosamente")


    def test_03_cerrar_presupuesto_erroneo(self):
        # Primero crear el documento
        crear_data = {
            "proyecto_id": self.proyecto_id,
            "descripcion": "Presupuesto para cerrar",
            "monto": "1000.00",
            "objetivo_especifico": "Compra"
        }
        res = self.client.post(
            "/documento_crear",
            data=crear_data,
            headers=self.auth_headers,
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 201)

        # Buscar el doc_id del presupuesto recién creado
        

        doc = db_documentos.find_one({"descripcion": "Presupuesto para cerrar"})
        self.assertIsNotNone(doc)
        doc_id = str(doc["_id"])

        cerrar_data = {
            "proyecto_id": self.proyecto_id,
            "doc_id": doc_id,
            "monto": "500.00",
            "description": "Cierre automático por test",
            "referencia": "REF12345",
            "monto_transferencia": "500.00",
            "banco": "TestBank",
            "cuenta_contable": "CC123456789"
        }

        file_data = {
            "files": (BytesIO(b"archivo cierre"), "cierre.pdf")
        }

        res = self.client.post(
            "/documento_cerrar",
            data={**cerrar_data, **file_data},
            headers=self.auth_headers,
            content_type='multipart/form-data'
        )
        print("Response from cerrar presupuesto:", res.get_json())
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "El monto aprobado excede el saldo disponible del proyecto.")


if __name__ == '__main__':
    unittest.main()
