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

def combine_excel_files(existing_file, new_file):
    if os.path.exists(existing_file):
        existing_df = pd.read_excel(existing_file)
        new_df = pd.read_excel(new_file)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_excel(existing_file, index=False)
        return existing_file
    else:
        new_df = pd.read_excel(new_file)
