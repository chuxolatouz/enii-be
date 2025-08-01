import unittest
from datetime import datetime, timezone
from api.index import app, db_proyectos, db_solicitudes
from bson import ObjectId

class ReglaFijaTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        db_proyectos.drop()
        db_solicitudes.drop()

        # Crear usuario admin y login
        self.user = {
            "nombre": "Admin",
            "apellido": "Reglas",
            "email": "admin_reglas@example.com",
            "password": "admin123",
            "is_admin": True
        }
        self.client.post("/registrar", json=self.user)

        res = self.client.post("/login", json={
            "email": self.user["email"],
            "password": self.user["password"]
        })
        self.token = res.get_json()["token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

        # Crear proyecto
        res = self.client.post("/crear_proyecto", json={
            "nombre": "Proyecto con Reglas Fijas",
            "descripcion": "Test de reglas fijas",
            "fecha_inicio": datetime.now(timezone.utc),
            "fecha_fin": datetime.now(timezone.utc)
        }, headers=self.auth_headers)

        self.proyecto_id = res.get_json().get("_id") or res.get_json().get("proyecto_id")

        # Asignar balance al proyecto
        self.client.post("/asignar_balance", json={
            "proyecto_id": self.proyecto_id,
            "balance": 10000
        }, headers=self.auth_headers)

    def test_01_crear_regla_fija(self):
        reglas = {
            "name": "Pagos mensuale",
            "items": [
                {
                    "nombre_regla": "Pago mensual de mantenimiento",
                    "monto": 100
                },
                {
                    "nombre_regla": "Pago mensual de servicios",
                    "monto": 200
                }
            ]
        }

        res = self.client.post("/crear_solicitud_regla_fija", json=reglas, headers=self.auth_headers)
        print("Crear regla fija:", res.get_json())
        self.assertEqual(res.status_code, 200)
        self.assertIn("message", res.get_json())

    def test_02_ver_reglas_fijas(self):
        # Crear primero
        self.test_01_crear_regla_fija()
        res = self.client.get("/mostrar_solicitudes", headers=self.auth_headers)
        print("Ver reglas fijas:", res.get_json())
        self.assertEqual(res.status_code, 200)
        reglas = res.get_json().get("request_list", [])
        self.assertIsInstance(reglas, list)
        self.assertGreaterEqual(len(reglas), 1)
        self.regla_id = reglas[0]["_id"]["$oid"]

    def test_03_actualizar_regla_fija(self):
        self.test_01_crear_regla_fija()
        res = self.client.get("/mostrar_solicitudes", headers=self.auth_headers)
        reglas = res.get_json().get("request_list", [])
        self.assertGreater(len(reglas), 0)
        regla_id = reglas[0]["_id"]["$oid"]

        update_data = {
            "resolution": "completed",
        }

        res = self.client.post(
            f"/completar_solicitud_regla_fija/{regla_id}",
            json=update_data,
            headers=self.auth_headers
        )

        print("Actualizar regla fija:", res.get_json())
        self.assertEqual(res.status_code, 200)
        self.assertIn("solicitud de regla eliminada con éxito", res.get_json().get("message", "").lower())


    def test_04_obtener_regla_fija(self):
        # Crear primero
        self.test_01_crear_regla_fija()
        res = self.client.get("/mostrar_solicitudes", headers=self.auth_headers)
        print("Obtener regla fija:", res.get_json())
        reglas = res.get_json().get("request_list", [])
        self.assertGreater(len(reglas), 0)
        self.assertEqual(res.status_code, 200)

    def test_05_eliminar_regla_fija(self):
        # Crear y obtener ID
        self.test_01_crear_regla_fija()
        res = self.client.get("/mostrar_solicitudes", headers=self.auth_headers)
        reglas = res.get_json().get("request_list", [])
        self.assertGreater(len(reglas), 0)
        regla_id = reglas[0]["_id"]["$oid"]

        # Eliminar
        res = self.client.post(f"/eliminar_solicitud_regla_fija/{regla_id}", headers=self.auth_headers)
        print('raw response:', res.data)
        print("Eliminar regla fija:", res.get_json())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json().get("message"), "Solicitud de regla eliminada con éxito")

if __name__ == '__main__':
    unittest.main()
