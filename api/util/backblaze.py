
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from io import BytesIO

ACCOUNT_ID = "0054addcef284d30000000002"
APPLICATION_KEY = "K005xSlLQhiwP7QZsQOXxe7k2HH+WHk"
BUCKET_ID = "d4ea8d3dcc4e0ff288e40d13"
BASE_B2_URL = "https://f005.backblazeb2.com/file"
BUCKET_NAME="enii-ucv-1"

info = InMemoryAccountInfo()
b2_api = B2Api(account_info=info)

def auth_b2_account():
    b2_api.authorize_account("production", ACCOUNT_ID, APPLICATION_KEY)
    return b2_api

def upload_file(file_buffer: BytesIO, full_path: str):
    """Sube un archivo a Backblaze a una ruta completa (incluyendo carpeta y nombre)."""
    auth_b2_account()
    bucket = b2_api.get_bucket_by_id(BUCKET_ID)

    if not bucket:
        raise ValueError(f"Bucket with ID {BUCKET_ID} not found.")
    if not file_buffer or not isinstance(file_buffer, BytesIO):
        raise ValueError("Invalid file buffer.")
    if not full_path or not isinstance(full_path, str):
        raise ValueError("Invalid file path.")

    file_data = file_buffer.read()
    result = bucket.upload_bytes(file_data, file_name=full_path)

    public_url = f"{BASE_B2_URL}/{BUCKET_NAME}/{full_path}"
    return {
        "fileName": full_path,
        "download_url": public_url,
        "fileId": result.id_,
    }
