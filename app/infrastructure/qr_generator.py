import pyqrcode
import io
import base64

def generate_qr_code_base64(data: str) -> str:
    """Generates a QR code and returns it as a base64 string."""
    qr = pyqrcode.create(data)
    buffer = io.BytesIO()
    qr.png(buffer, scale=6)
    return base64.b64encode(buffer.getvalue()).decode()
