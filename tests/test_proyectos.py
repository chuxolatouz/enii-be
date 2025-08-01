# tests/test_projects.py
import unittest
from datetime import datetime, timezone
from api.index import app

class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        # Crear usuario y obtener token para endpoints protegidos
        self.user = {
            "nombre": "Admin",
            "apellido": "Test",
            "email": "admin@example.com",
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

    def test_01_crear_proyecto(self):
        proyecto = {
            "nombre": "Sistema de Gestión ENII",
            "descripcion": "Aplicación web para administrar proyectos.",
            "fecha_inicio": datetime.now(timezone.utc),
            "fecha_fin": datetime.now(timezone.utc)
        }
        res = self.client.post("/crear_proyecto", json=proyecto, headers=self.auth_headers)
        print("Response from creating project:", res.get_json())
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Proyecto creado con éxito")

    def test_02_listar_proyectos(self):
        res = self.client.get("/mostrar_proyectos", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn("request_list", data)
        self.assertIsInstance(data["request_list"], list)
        self.assertGreater(len(data["request_list"]), 0)

    def test_03_obtener_proyecto(self):
        # Asumimos que el primer proyecto es el que queremos obtener
        res = self.client.get("/mostrar_proyectos", headers=self.auth_headers)
        data = res.get_json()
        proyecto_id = data["request_list"][0]["_id"]["$oid"]
        res = self.client.get(f"/proyecto/{proyecto_id}", headers=self.auth_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("nombre", data)
        self.assertIn("descripcion", data)
        self.assertEqual(data["balance"], "0,00")

    def test_04_actualizar_proyecto(self):
        # Asumimos que el primer proyecto es el que queremos actualizar
        res = self.client.get("/mostrar_proyectos", headers=self.auth_headers)
        data = res.get_json()
        proyecto_id = data["request_list"][0]["_id"]["$oid"]
        
        proyecto_actualizado = {
            "nombre": "Sistema de Gestión ENII Actualizado",
            "descripcion": "Descripción actualizada del proyecto.",
        }
        
        res = self.client.put(f"/actualizar_proyecto/{proyecto_id}", json=proyecto_actualizado, headers=self.auth_headers)
        
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Proyecto actualizado con éxito")

    def test_05_agregar_balance(self):
        # Asumimos que el primer proyecto es el que queremos actualizar
        res = self.client.get("/mostrar_proyectos", headers=self.auth_headers)
        data = res.get_json()
        proyecto_id = data["request_list"][0]["_id"]["$oid"]
        
        balance = {
            "project_id": proyecto_id,
            "balance": "1000",
            "descripcion": "Aporte inicial al proyecto."
        }
        
        res = self.client.patch("/asignar_balance", json=balance, headers=self.auth_headers)
        print("Response from adding balance:", res.get_json())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Balance asignado con éxito")
    def tearDown(self):
        
        return super().tearDown()

if __name__ == '__main__':
    unittest.main()
