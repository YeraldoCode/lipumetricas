from flask import Flask, flash, redirect, render_template, request, jsonify, url_for, session, abort
import pandas as pd
import secrets
from dotenv import load_dotenv
import os
from utils.file_handler import allowed_file, combine_excel_files, save_file, read_excel
from config import SEMANAS_FOLDER, DETALLES_FOLDER, SECRET_KEY
from datetime import datetime
import json
from werkzeug.utils import secure_filename
from functools import wraps
import logging

#cargar variables de entorno
load_dotenv()

#Creacion de la aplicacion
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = SEMANAS_FOLDER
app.secret_key = SECRET_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Inicialmente cargamos las semanas disponibles
def cargar_semanas_disponibles():
    semanas = {}
    for filename in os.listdir(SEMANAS_FOLDER):
        if filename.startswith('semana_completa_') and filename.endswith('.xlsx'):
            semana_key = filename.replace('semana_completa_', '').replace('.xlsx', '')
            semanas[f'semana_{semana_key}'] = os.path.join(SEMANAS_FOLDER, filename)
    # Ordenar las semanas de manera ascendente
    semanas_ordenadas = dict(sorted(semanas.items(), key=lambda x: int(x[0].split('_')[1])))
    return semanas_ordenadas

SEMANA_ARCHIVOS = cargar_semanas_disponibles()

SEMANA_FECHAS = {
    'semana_14': '31-marzo a 6-abril',
    'semana_15': '7-abril a 13-abril',
    'semana_16': '14-abril a 20-abril',
    'semana_17': '21-abril a 27-abril',
    'semana_18': '28-abril a 4-mayo',
    'semana_19': '5-mayo a 11-mayo',
    'semana_20': '12-mayo a 18-mayo',
    'semana_21': '19-mayo a 25-mayo',
    'semana_22': '26-mayo a 1-junio',
    'semana_23': '2-junio a 8-junio',
    'semana_24': '9-junio a 15-junio',
    'semana_25': '16-junio a 22-junio',
    'semana_26': '23-junio a 29-junio',
    'semana_27': '30-junio a 6-julio',
    'semana_28': '7-julio a 13-julio',
    'semana_29': '14-julio a 20-julio',
    'semana_30': '21-julio a 27-julio',
    'semana_31': '28-julio a 3-agosto',
    'semana_32': '4-agosto a 10-agosto',
    'semana_33': '11-agosto a 17-agosto',
    'semana_34': '18-agosto a 24-agosto',
    'semana_35': '25-agosto a 31-agosto',
    }

def cargar_datos(semana):
    excel_path = SEMANA_ARCHIVOS.get(semana)
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Archivo no encontrado para {semana}")
    
    # Leer la hoja 'Resumen'
    df = pd.read_excel(excel_path, sheet_name='Resumen')
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={'c': 'Cliente'})
    for col in ['N5_%', 'VOK_%']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('%','').str.replace(',','.').astype(float)
            if df[col].max() > 1.5:
                df[col] = df[col] / 100
    return df

def cargar_detalle_generico(semana, metrica, cliente=None):
    excel_path = SEMANA_ARCHIVOS.get(semana)
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Archivo no encontrado para {semana}")
    
    # Determinar la hoja a leer
    sheet_name = 'Detalle_NS' if metrica == 'ns' else 'Detalle_VOK'
    
    try:
        # Leer la hoja correspondiente - ahora sin skiprows ya que los encabezados están en A1
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        # Limpiar nombres de columnas
        df.columns = [str(col).strip() for col in df.columns]
        
        # Seleccionar columnas según la métrica
        if metrica == 'ns':
            required_columns = ['c', 'des', 'Suma de ns_val', 'Suma de ns_val_ok', 'Suma de ns_p', 'Suma de malos']
            try:
                df = df[required_columns]
            except KeyError:
                # Si no encuentra las columnas exactas, intentar encontrar coincidencias
                column_mapping = {}
                for col in df.columns:
                    col_lower = str(col).lower()
                    if 'cliente' in col_lower or col_lower == 'c':
                        column_mapping[col] = 'c'
                    elif 'desc' in col_lower or col_lower == 'des':
                        column_mapping[col] = 'des'
                    elif 'suma de ns_val' in col_lower and 'ok' not in col_lower:
                        column_mapping[col] = 'Suma de ns_val'
                    elif 'suma de ns_val_ok' in col_lower:
                        column_mapping[col] = 'Suma de ns_val_ok'
                    elif 'suma de ns_p' in col_lower:
                        column_mapping[col] = 'Suma de ns_p'
                    elif 'suma de malo' in col_lower:
                        column_mapping[col] = 'Suma de malos'
                
                df = df.rename(columns=column_mapping)
                df = df[required_columns]
            
        else:  # metrica == 'vok'
            required_columns = ['c', 'Des', 'vok_val', 'vok_val_ok', 'vok_p', 'malos']
            try:
                df = df[required_columns]
            except KeyError:
                # Si no encuentra las columnas exactas, intentar encontrar coincidencias
                column_mapping = {}
                for col in df.columns:
                    col_lower = str(col).lower()
                    if 'cliente' in col_lower or col_lower == 'c':
                        column_mapping[col] = 'c'
                    elif 'desc' in col_lower:
                        column_mapping[col] = 'Des'
                    elif 'vok_val' in col_lower and 'ok' not in col_lower:
                        column_mapping[col] = 'vok_val'
                    elif 'vok_val_ok' in col_lower:
                        column_mapping[col] = 'vok_val_ok'
                    elif 'vok_p' in col_lower:
                        column_mapping[col] = 'vok_p'
                    elif 'malo' in col_lower:
                        column_mapping[col] = 'malos'
                
                df = df.rename(columns=column_mapping)
                df = df[required_columns]

        # Filtrar por cliente si se especifica
        if cliente:
            df['c'] = df['c'].astype(str).str.strip()
            cliente = str(cliente).strip()
            df = df[df['c'] == cliente]
        
        # Calcular porcentajes
        if metrica == 'ns':
            df['Suma de ns_p'] = (df['Suma de ns_val_ok'].astype(float) / 
                         df['Suma de ns_val'].astype(float) * 100).map("{:.2f}".format)
            df = df[df['Suma de malos'].astype(float) >= 1]
        else:
            df['vok_p'] = (df['vok_val_ok'].astype(float) / 
                          df['vok_val'].astype(float) * 100).map("{:.2f}".format)
            df = df[df['malos'].astype(float) >= 1]
        
        result = df.to_dict(orient='records')
        print(f"Registros encontrados: {len(result)}")
        
        if result:
            print("Primer registro:", result[0])
        
        return result
        
    except Exception as e:
        print(f"Error al procesar el archivo: {str(e)}")
        return []

@app.route('/')
def index():
    try:
        semana = request.args.get('semana', 'semana_14')
        df = cargar_datos(semana)
        clientes = df['Cliente'].dropna().unique()
        cliente = request.args.get('cliente', '')
        if cliente:
            df = df[df['Cliente'] == cliente]
        
        # Calcular totales y porcentajes para NS
        ns_total = df['N5_TOTAL'].sum() if not df.empty else 'N/A'
        ns_buenos = df['N5_Buenos'].sum() if not df.empty else 'N/A'
        ns_malos = df['n5_malos'].sum() if not df.empty else 'N/A'
        ns_promedio = (ns_buenos / ns_total) if ns_total != 'N/A' and ns_total != 0 else 'N/A'
        
        # Calcular totales y porcentajes para VOK de la misma manera que NS
        vok_total = df['VOK_Total'].sum() if not df.empty else 'N/A'
        vok_buenos = df['VOK_Buenos'].sum() if not df.empty else 'N/A'
        vok_malos = df['VOK_Malos'].sum() if not df.empty else 'N/A'
        vok_promedio = (vok_buenos / vok_total) if vok_total != 'N/A' and vok_total != 0 else 'N/A'
        
        # Obtener primera fila para cal_ruta
        row = df.iloc[0] if not df.empty else {}
        
        data = {
            'cliente': cliente or 'Todos',
            'semana': semana,
            'ns': {
                'total': ns_total,
                'buenos': ns_buenos,
                'malos': ns_malos,
                'porcentaje': f"{ns_promedio:.2%}" if ns_promedio != 'N/A' else 'N/A'
            },
            'vok': {
                'total': vok_total,
                'buenos': vok_buenos,
                'malos': vok_malos,
                'porcentaje': f"{vok_promedio:.2%}" if vok_promedio != 'N/A' else 'N/A'
            },
            'cal_ruta': {
                'total': row.get('CalRuta_Total', 'N/A'),
                'buenos': 'N/A',
                'malos': 'N/A',
                'porcentaje': 'N/A'
            }
        }
        return render_template('index.html', data=data, clientes=clientes, request=request, semanas=SEMANA_ARCHIVOS, semana=semana, cliente=cliente, semana_fechas=SEMANA_FECHAS)
    except Exception as e:
        return f"<h3>Error al leer archivo: {str(e)}</h3>"

@app.route('/grafica')
def grafica():
    try:
        # Obtiene el parámetro 'semana' de la URL, por defecto 'semana_14'
        semana = request.args.get('semana', 'semana_14')
        # Carga los datos del archivo Excel correspondiente a la semana
        df = cargar_datos(semana)
        # Obtiene el parámetro 'cliente' de la URL
        cliente = request.args.get('cliente', '')
        
        # Filtra el DataFrame si se especificó un cliente
        if cliente:
            df = df[df['Cliente'] == cliente]
        # Verifica si hay datos después del filtrado
        if df.empty:
            return jsonify({'error': 'No hay datos para este cliente'}), 400
            
        # Obtiene el tipo de métrica a mostrar, por defecto 'N5_%'
        metrica = request.args.get('metrica', 'N5_%')
        import plotly.graph_objects as go

        # Configuración para métrica de Nivel de Servicio (NS)
        if metrica == 'N5_%':
            total = df['N5_TOTAL'].sum()
            buenos = df['N5_Buenos'].sum()
            malos = df['n5_malos'].sum()
            # Calcula el porcentaje de cumplimiento
            cumplimiento = buenos / total if total else 0
            valores = [buenos, malos]
            etiquetas = ['Buenos', 'Malos']
            titulo = f"NS - Cumplimiento: {cumplimiento:.2%}"
        
        # Configuración para métrica de Viajes OK (VOK)
        elif metrica == 'VOK_%':
            total = df['VOK_Total'].sum()
            buenos = df['VOK_Buenos'].sum()
            malos = df['VOK_Malos'].sum()
            cumplimiento = buenos / total if total else 0
            valores = [buenos, malos]
            etiquetas = ['Buenos', 'Malos']
            titulo = f"VOK - Cumplimiento: {cumplimiento:.2%}"
        
        # Configuración para métrica de Calidad de Ruta
        else:
            total = df['CalRuta_Total'].sum() if 'CalRuta_Total' in df.columns else 0
            valores = [total]
            etiquetas = ['Total']
            titulo = f"Calidad de Ruta"

        # Crear la gráfica de dona usando Plotly
        fig = go.Figure(data=[go.Pie(
            labels=etiquetas,
            values=valores,
            hole=0.4,  # Tamaño del agujero central (0.4 = 40%)
            # Nuevos colores: Verde para buenos, Rojo para malos
            marker=dict(
                colors=['#198754', '#dc3545'] if len(valores) > 1 else ['#198754'],  
                line=dict(color='white', width=2)
            ),
            textinfo='percent',  # Mostrar porcentajes
            textposition='outside',  # Texto fuera de la dona
            showlegend=False  # Ocultar leyenda
        )])

        # Configurar el diseño de la gráfica
        fig.update_layout(
            title_text=titulo,  # Título de la gráfica
            # Márgenes: izquierda=20, derecha=120, arriba=40, abajo=20
            margin=dict(l=20, r=120, t=40, b=20),
            # Agregar anotación con el total
            annotations=[
                dict(
                    text=f"<b>Total:</b> {sum(valores)}",
                    x=1.2, y=0.5,  # Posición de la anotación
                    xref="paper", yref="paper",
                    showarrow=False,  # Sin flecha
                    align="left",
                    font=dict(size=14)  # Tamaño de fuente
                )
            ]
        )

        # Convertir la figura a JSON y retornar
        return jsonify(fig.to_json())
    except Exception as e:
        # Manejar cualquier error y retornar código 400
        return jsonify({'error': str(e)}), 400


    
@app.route('/detalle/<metrica>')
def detalle_metrica(metrica):
    try:
        semana = request.args.get('semana', 'semana_14')
        cliente = request.args.get('cliente')
        print(f"Procesando detalle: metrica={metrica}, semana={semana}, cliente={cliente}")
        
        data = cargar_detalle_generico(semana, metrica, cliente)
        print(f"Datos cargados: {len(data)} registros")
        
        return render_template(
            f"detalle_{metrica}.html",
            data=data,
            semana=semana,
            cliente=cliente,
            titulo=metrica.upper()
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"<h3>Error al cargar detalle: {str(e)}</h3>"
    

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if not any(request.files.get(key) for key in ['semanaFile', 'detalleNsFile', 'detalleVokFile', 'detalleCalidadRutaFile']):
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        semana_file = request.files.get('semanaFile')
        detalle_ns_file = request.files.get('detalleNsFile')
        detalle_vok_file = request.files.get('detalleVokFile')
        detalle_calidad_ruta_file = request.files.get('detalleCalidadRutaFile')
        
        if semana_file and allowed_file(semana_file.filename):
            semana_filepath = os.path.join(SEMANAS_FOLDER, semana_file.filename)
            semana_file.save(semana_filepath)
            flash(f'Archivo {semana_file.filename} subido exitosamente', 'success')
            # Actualizar la lista de semanas disponibles
            global SEMANA_ARCHIVOS
            SEMANA_ARCHIVOS = cargar_semanas_disponibles()
        
        if detalle_ns_file and allowed_file(detalle_ns_file.filename):
            detalle_ns_filepath = os.path.join(DETALLES_FOLDER, detalle_ns_file.filename)
            detalle_ns_file.save(detalle_ns_filepath)
            flash(f'Archivo {detalle_ns_file.filename} subido exitosamente', 'success')
        
        if detalle_vok_file and allowed_file(detalle_vok_file.filename):
            detalle_vok_filepath = os.path.join(DETALLES_FOLDER, detalle_vok_file.filename)
            detalle_vok_file.save(detalle_vok_filepath)
            flash(f'Archivo {detalle_vok_file.filename} subido exitosamente', 'success')
        
        if detalle_calidad_ruta_file and allowed_file(detalle_calidad_ruta_file.filename):
            detalle_calidad_ruta_filepath = os.path.join(DETALLES_FOLDER, detalle_calidad_ruta_file.filename)
            detalle_calidad_ruta_file.save(detalle_calidad_ruta_filepath)
            flash(f'Archivo {detalle_calidad_ruta_file.filename} subido exitosamente', 'success')
        
        return redirect(url_for('index'))
    
    return render_template('admin_upload.html')

# decorador para proteger ruta de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not os.path.exists(SEMANAS_FOLDER):
            try:
                os.makedirs(SEMANAS_FOLDER)
            except Exception as e:
                logger.error(f"Error al crear el directorio {SEMANAS_FOLDER}: {str(e)}")
                abort(500)
            return f(*args, **kwargs)
    return decorated_function



# Panel de Administración
@app.route('/admin-panel')
def admin_dashboard():
    print("Intentando acceder al panel de administración")  # Debug print
    try:
        # Obtener lista de archivos con su información
        files = []
        for filename in os.listdir(SEMANAS_FOLDER):
            if filename.startswith('semana_completa_') and filename.endswith('.xlsx'):
                file_path = os.path.join(SEMANAS_FOLDER, filename)
                files.append({
                    'name': filename,
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        print(f"Archivos encontrados: {len(files)}")  # Debug print
        
        # Obtener logs de actividad
        logs = get_activity_logs()
        
        print("Intentando renderizar template")  # Debug print
        return render_template('admin_dashboard.html', 
                            files=files,
                            logs=logs)
    except Exception as e:
        print(f"Error en el panel de administración: {str(e)}")  # Debug print
        # En lugar de redireccionar, mostramos el error
        return f"<h1>Error al cargar el panel</h1><p>{str(e)}</p>"



#cargar archivos 
@app.route('/admin-upload', methods=['POST'])
def admin_upload():
    try:
        if 'file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('admin_dashboard'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('admin_dashboard'))
        
        if file and allowed_file(file.filename):
            # Guardar el archivo
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Registrar la actividad
            log_activity('upload', filename, 'Archivo subido exitosamente')
            
            # Actualizar la lista de semanas disponibles
            global SEMANA_ARCHIVOS
            SEMANA_ARCHIVOS = cargar_semanas_disponibles()
            
            flash('Archivo subido exitosamente', 'success')
        else:
            flash('Tipo de archivo no permitido', 'error')
            
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error al subir el archivo: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))
    

#modificar archivos
@app.route('/admin-modify', methods=['POST'])
def admin_modify():
    try:
        filename = request.form.get('filename')
        if 'new_file' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(url_for('admin_dashboard'))
        
        new_file = request.files['new_file']
        details = request.form.get('details', '')
        
        if new_file and allowed_file(new_file.filename):
            # Guardar el nuevo archivo
            new_filename = secure_filename(new_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            new_file.save(file_path)
            
            # Registrar la actividad
            log_activity('modify', filename, details)
            
            # Actualizar la lista de semanas disponibles
            global SEMANA_ARCHIVOS
            SEMANA_ARCHIVOS = cargar_semanas_disponibles()
            
            flash('Archivo modificado exitosamente', 'success')
        else:
            flash('Tipo de archivo no permitido', 'error')
            
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error al modificar el archivo: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))


#eliminar archivo 
@app.route('/admin-delete/<filename>')
def admin_delete(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            log_activity('delete', filename, 'Archivo eliminado')
            
            # Actualizar la lista de semanas disponibles
            global SEMANA_ARCHIVOS
            SEMANA_ARCHIVOS = cargar_semanas_disponibles()
            
            flash('Archivo eliminado exitosamente', 'success')
        else:
            flash('Archivo no encontrado', 'error')
            
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f'Error al eliminar el archivo: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

# Funciones auxiliares para el registro de actividad
def log_activity(action, filename, details):
    """
    Registra una actividad en el log
    """
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': action,
        'filename': filename,
        'details': details
    }
    
    # Guardar en un archivo JSON
    log_file = os.path.join(SEMANAS_FOLDER, 'activity_log.json')
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"Error al registrar actividad: {str(e)}")

def get_activity_logs():
    """
    Obtiene el registro de actividades
    """
    log_file = os.path.join(SEMANAS_FOLDER, 'activity_log.json')
    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error al leer logs: {str(e)}")
        return []





if __name__ == '__main__':
    app.run(debug=True)


