# tests/test_categorias.py
import unittest
from api.index import app

class CategoriaTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

        self.user = {
            "nombre": "Admin",
            "apellido": "Test",
            "email": "admin_categorias@example.com",
            "password": "admin123",
            "is_admin": True
        }
        self.client.post("/registrar", json=self.user)

        login_data = {
            "email": self.user["email"],
            "password": self.user["password"]
        }
        res = self.client.post("/login", json=login_data)
        self.token = res.get_json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_01_crear_categoria(self):
        data = {
            "nombre": "Recursos Humanos",
            "descripcion": "Categoría relacionada al personal"
        }
        res = self.client.post("/categorias", json=data, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        self.assertIn("message", res.get_json())
        self.assertEqual(res.get_json()["message"], "Categoría creada con éxito")

    def test_02_listar_categorias(self):
        res = self.client.get("/mostrar_categorias", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)


if __name__ == '__main__':
    unittest.main()
