import os
import secrets
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración general
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SEMANAS_FOLDER = os.path.join(BASE_DIR, 'semana')
DETALLES_FOLDER = os.path.join(BASE_DIR, 'detalles')

# Asegurar que los directorios existen
os.makedirs(SEMANAS_FOLDER, exist_ok=True)
os.makedirs(DETALLES_FOLDER, exist_ok=True)

# Configuración de seguridad
SECRET_KEY = os.environ.get('llave_secreta') or os.urandom(24)
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN') or secrets.token_urlsafe(32)

# Configuración de auditoría
AUDIT_FOLDER = os.path.join(BASE_DIR, 'audit')
os.makedirs(AUDIT_FOLDER, exist_ok=True)
AUDIT_LOG_FILE = os.path.join(AUDIT_FOLDER, 'audit_log.json')

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# Configuración adicional
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit

