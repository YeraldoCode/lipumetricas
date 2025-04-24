import os 
import pandas as pd
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def save_file(file, folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(folder, filename)
        file.save(filepath)
        return filepath
    return None

def read_excel(filepath):
    return pd.read_excel(filepath)