# tests/test_users.py
import unittest
from api.index import app

class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True


    def test_01_listar_usuarios(self):
        res = self.client.get("/mostrar_usuarios")
        self.assertEqual(res.status_code, 200)
        self.assertIn("request_list", res.get_json())

    # def test_02_actualizar_usuario(self):
    #     nuevo = {
    #         "nombre": "Lucía",
    #         "apellido": "Mora",
    #         "email": "lucia@example.com",
    #         "password": "pass123",
    #         "rol": "user"
    #     }
    #     crear = self.client.post("/users", json=nuevo)
    #     user_id = crear.get_json().get("sub") or crear.get_json().get("_id")
    #     login_data = {
    #         "email": "juan@example.com",
    #         "password": "123456"
    #     }
    #     res = self.client.post("/login", json=login_data)
    #     token = res.get_json().get("token")  # o "access_token"
    #     print("Token:", token)
    #     update = {
    #         "nombre": "Lucía Actualizada"
    #     }
    #     headers = {
    #         "Authorization": f"Bearer {token}"
    #     }
    #     res = self.client.put(f"/editar_usuario/{user_id}", json=update, headers=headers)
    #     self.assertEqual(res.status_code, 200)
    #     self.assertIn("actualizado", res.get_data(as_text=True).lower())

    # def test_03_eliminar_usuario(self):
    #     nuevo = {
    #         "nombre": "Miguel",
    #         "apellido": "Rivas",
    #         "email": "miguel@example.com",
    #         "password": "clave456",
    #         "rol": "admin"
    #     }
    #     crear = self.client.post("/users", json=nuevo)
    #     user_id = crear.get_json().get("id") or crear.get_json().get("_id")

    #     res = self.client.delete(f"/eliminar/{user_id}")
    #     self.assertEqual(res.status_code, 200)
    #     self.assertIn("eliminado", res.get_data(as_text=True).lower())

if __name__ == '__main__':
    unittest.main()
