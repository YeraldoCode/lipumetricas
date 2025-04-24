import os

# Configuración general
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SEMANAS_FOLDER = os.path.join(BASE_DIR, 'semana')
DETALLES_FOLDER = os.path.join(BASE_DIR, 'detalles')

# Asegurar que los directorios existen
os.makedirs(SEMANAS_FOLDER, exist_ok=True)
os.makedirs(DETALLES_FOLDER, exist_ok=True)

# Clave secreta para la aplicación Flask
SECRET_KEY = os.environ.get('llave_secreta') or os.urandom(24)
