import unittest
from gpt4 import app

class TestApp(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_registrar(self):
        data = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "correo": "juan@example.com",
            "password": "password123"
        }
        response = self.app.post("/registrar", json=data)
        self.assertEqual(response.status_code, 201)
        self.assertIn(b"Usuario registrado con exito", response.data)

    def test_login(self):
        # Registrar un usuario de prueba
        data = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "correo": "juan@example.com",
            "password": "password123"
        }
        self.app.post("/registrar", json=data)

        # Iniciar sesión con credenciales válidas
        data = {"correo": "juan@example.com", "password": "password123"}
        response = self.app.post("/login", json=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"token", response.data)

        # Iniciar sesión con credenciales inválidas
        data = {"correo": "juan@example.com", "password": "password456"}
        response = self.app.post("/login", json=data)
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Credenciales invalidas", response.data)

if __name__ == "__main__":
    unittest.main()