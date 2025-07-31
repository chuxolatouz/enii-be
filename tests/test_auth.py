# tests/test_auth.py
import unittest
from api.index import app  # o desde donde expongas `app`

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_registro_y_login_exitoso(self):
        # 1. Registro
        registro = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@example.com",
            "password": "123456"
        }
        response = self.app.post("/registrar", json=registro)

        self.assertEqual(response.status_code, 201)
        self.assertIn(b"Usuario registrado", response.data)

        # 2. Login correcto
        login = {
            "email": "juan@example.com",
            "password": "123456"
        }
        response = self.app.post("/login", json=login)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"token", response.data)

    def test_login_invalido(self):
        login = {
            "email": "noexiste@example.com",
            "password": "123456"
        }
        response = self.app.post("/login", json=login)
        self.assertEqual(response.status_code, 401)

        data = response.get_json()
        self.assertEqual(data["message"], "Credenciales inválidas")



if __name__ == '__main__':
    unittest.main()
