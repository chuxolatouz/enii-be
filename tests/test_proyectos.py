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
            "rol": "admin"
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

if __name__ == '__main__':
    unittest.main()
