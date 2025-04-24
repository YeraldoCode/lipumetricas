import os

#configuracion general 
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLPOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SEMANAS_FOLDER = os.path.join(BASE_DIR, 'semanas')
DETALLES_FOLDER = os.path.join(BASE_DIR, 'detalles')


# asegurar que los directorios existen
os.makedirs(SEMANAS_FOLDER, exist_ok=True)
os.makedirs(DETALLES_FOLDER, exist_ok=True) 