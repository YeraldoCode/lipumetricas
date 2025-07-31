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
    'semana_36': '1-septiembre a 7-septiembre',
    'semana_37': '8-septiembre a 14-septiembre',
    'semana_38': '15-septiembre a 21-septiembre',
    'semana_39': '22-septiembre a 28-septiembre',
    'semana_40': '29-septiembre a 5-octubre',
    'semana_41': '6-octubre a 12-octubre',
    'semana_42': '13-octubre a 19-octubre',
    'semana_43': '20-octubre a 26-octubre',
    'semana_44': '27-octubre a 2-noviembre',
    'semana_45': '3-noviembre a 9-noviembre',
    'semana_46': '10-noviembre a 16-noviembre',
    'semana_47': '17-noviembre a 23-noviembre',
    'semana_48': '24-noviembre a 30-noviembre',
    'semana_49': '1-diciembre a 7-diciembre',
    'semana_50': '8-diciembre a 14-diciembre',
    'semana_51': '15-diciembre a 21-diciembre',
    'semana_52': '22-diciembre a 28-diciembre',
    }

def cargar_datos(semana):
    excel_path = SEMANA_ARCHIVOS.get(semana)
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Archivo no encontrado para {semana}")
    
    # Leer la hoja 'Resumen'
    df = pd.read_excel(excel_path, sheet_name='Resumen')
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={'c': 'Cliente'})
    for col in ['N5_%', 'VOK_%', 'cr']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('%','').str.replace(',','.').astype(float)
            if df[col].max() > 1.5:
                df[col] = df[col] / 100
    # Asegurarse de que 'rutas' sea numérico
    if 'rutas' in df.columns:
        df['rutas'] = pd.to_numeric(df['rutas'], errors='coerce').fillna(0)
    return df



def cargar_detalle_generico(semana, metrica, cliente=None):
    excel_path = SEMANA_ARCHIVOS.get(semana)
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Archivo no encontrado para {semana}")

    # Determinar la hoja a leer según la métrica
    if metrica == 'ns':
        sheet_name = 'Detalle_NS'
    elif metrica == 'vok':
        sheet_name = 'Detalle_VOK'
    elif metrica == 'cal_ruta':
        sheet_name = 'Cal_Ruta'
    else:
        raise ValueError("Métrica no soportada")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        df.columns = [str(col).strip() for col in df.columns]

        if metrica == 'ns':
            required_columns = ['c', 'des', 'Suma de ns_val', 'Suma de ns_val_ok', 'Suma de ns_p', 'Suma de malos']
            try:
                df = df[required_columns]
            except KeyError:
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

        elif metrica == 'vok':
            required_columns = ['c', 'Des', 'vok_val', 'vok_val_ok', 'vok_p', 'malos']
            try:
                df = df[required_columns]
            except KeyError:
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

        elif metrica == 'cal_ruta':
            # Mapeo flexible para columnas de detalle de calidad de ruta
            column_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['c', 'cliente']:
                    column_mapping[col] = 'cliente'
                elif col_lower == 'rutas':
                    column_mapping[col] = 'rutas'
                elif col_lower == 'cr':
                    column_mapping[col] = 'cr'
            df = df.rename(columns=column_mapping)

            # Filtrar por cliente si aplica
            if cliente and 'cliente' in df.columns:
                df['cliente'] = df['cliente'].astype(str).str.strip()
                cliente = str(cliente).strip()
                df = df[df['cliente'] == cliente]

            # Solo dejar las columnas relevantes
            df = df[['cliente', 'rutas', 'cr']]

            # Asegurarse de que 'rutas' sea numérico
            df['rutas'] = pd.to_numeric(df['rutas'], errors='coerce').fillna(0)
            # Asegurarse de que 'cr' sea numérico y esté en porcentaje
            df['cr'] = df['cr'].astype(str).str.replace('%','').str.replace(',','.').astype(float)
            if df['cr'].max() > 1.5:
                df['cr'] = df['cr'] / 100
            df['cr'] = (df['cr'] * 100).map("{:.2f}%")

            # Filtrar por cliente si aplica
            if cliente and 'cliente' in df.columns:
                df['cliente'] = df['cliente'].astype(str).str.strip()
                cliente = str(cliente).strip()
                df = df[df['cliente'] == cliente]

            # Asegurarse de que 'cr' sea numérico y esté en proporción
            if 'cr' in df.columns:
                df['cr'] = df['cr'].astype(str).str.replace('%','').str.replace(',','.').astype(float)
                if df['cr'].max() > 1.5:
                    df['cr'] = df['cr'] / 100

        # Calcular porcentajes y filtrar según la métrica
        if metrica == 'ns':
            df['Suma de ns_p'] = (df['Suma de ns_val_ok'].astype(float) /
                                  df['Suma de ns_val'].astype(float) * 100).map("{:.2f}".format)
            df = df[df['Suma de malos'].astype(float) >= 1]
        elif metrica == 'vok':
            df['vok_p'] = (df['vok_val_ok'].astype(float) /
                           df['vok_val'].astype(float) * 100).map("{:.2f}".format)
            df = df[df['malos'].astype(float) >= 1]
        elif metrica == 'cal_ruta':
            # Puedes filtrar o calcular campos adicionales aquí si lo necesitas
            pass

        result = df.to_dict(orient='records')
        print(f"Registros encontrados: {len(result)}")
        if result:
            print("Primer registro:", result[0])
        return result

    except Exception as e:
        print(f"Error al procesar el archivo: {str(e)}")
        return []
    
def cargar_datos_calruta(semana, cliente=None):
    excel_path = SEMANA_ARCHIVOS.get(semana)
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Archivo no encontrado para {semana}")

    # Leer la hoja 'Carta_cr'
    df = pd.read_excel(excel_path, sheet_name='Carta_cr')
    df.columns = [c.strip() for c in df.columns]

    # Convertir 'cr' a decimal si está en porcentaje
    df['cr'] = df['cr'].astype(str).str.replace(',', '.').str.replace('%', '')  # Reemplazar comas y eliminar '%'
    df['cr'] = pd.to_numeric(df['cr'], errors='coerce')  # Convertir a número
    if df['cr'].max() > 1:  # Si los valores son mayores a 1, están en porcentaje
        df['cr'] = df['cr'] / 100

    # Filtrar por cliente si se especifica
    if cliente:
        df = df[df['cliente'] == cliente]

    # Calcular el total de rutas
    calruta_total = df['rutas'].sum()

    # Calcular el porcentaje general (promedio ponderado)
    if calruta_total > 0:
        calruta_promedio = (df['rutas'] * df['cr']).sum() / calruta_total
    else:
        calruta_promedio = 0  # Si no hay rutas, el promedio es 0

    return calruta_total, calruta_promedio

@app.route('/detalle_calruta')
def detalle_calruta():
    try:
        semana = request.args.get('semana')
        cliente = request.args.get('cliente')

        # Ruta del archivo según la semana
        excel_path = SEMANA_ARCHIVOS.get(semana)
        if not excel_path or not os.path.exists(excel_path):
            return render_template('detalle_calruta.html', data=[], cliente=cliente, semana=semana, titulo='Calidad de Ruta')

        # Leer la hoja 'Detalle_cr'
        import pandas as pd
        df_detalle = pd.read_excel(excel_path, sheet_name='Detalle_cr')
        # Renombrar columnas
        df_detalle = df_detalle.rename(columns={
            'cliente': 'Cliente',
            'id_ruta': 'ID Ruta',
            'total_paradas': 'Total Paradas',
            'total_paradas_enc': 'Paradas Encuestadas',
            'total_paradas_no_enc': 'Paradas No Encuestadas',
            'cr': 'Calidad de Ruta'
        })

        # Filtrar por cliente si aplica
        if cliente:
            df_detalle['Cliente'] = df_detalle['Cliente'].astype(str).str.strip()
            cliente = str(cliente).strip()
            df_detalle = df_detalle[df_detalle['Cliente'] == cliente]

        # Convertir y formatear 'Calidad de Ruta' a porcentaje
        df_detalle['Calidad de Ruta'] = (
            df_detalle['Calidad de Ruta']
            .astype(str)
            .str.replace(',', '.')
            .astype(float)
            .mul(100)
            .map("{:.2f}".format)
            .str.replace('.', ',') + '%'
        )

        data = df_detalle.to_dict(orient='records')
        return render_template(
            'detalle_calruta.html',
            data=data,
            cliente=cliente,
            semana=semana,
            titulo='Calidad de Ruta'
        )
    except Exception as e:
        print(f"Error al cargar detalle de calidad de ruta: {str(e)}")
        return render_template('detalle_calruta.html', data=[], cliente=cliente, semana=semana, titulo='Calidad de Ruta', error=str(e))

@app.route('/')
def index():
    try:
        semana = request.args.get('semana', 'semana_14')
        cliente = request.args.get('cliente', '')
        df = cargar_datos(semana)

        # Obtener la lista completa de clientes antes de filtrar
        clientes = df['Cliente'].dropna().unique()

        # Filtrar los datos por cliente si se selecciona uno
        if cliente:
            df = df[df['Cliente'] == cliente]

        # Convertir el DataFrame filtrado a un diccionario para mostrar en la tabla
        tabla_clientes = df.to_dict(orient='records')

        # Calcular totales y porcentajes para NS
        ns_total = round(df['N5_TOTAL'].sum()) if not df.empty else 'N/A'
        ns_buenos = round(df['N5_Buenos'].sum()) if not df.empty else 'N/A'
        ns_malos = round(df['n5_malos'].sum()) if not df.empty else 'N/A'
        ns_promedio = (df['N5_Buenos'].sum() / df['N5_TOTAL'].sum()) if not df.empty and df['N5_TOTAL'].sum() != 0 else 'N/A'

        # Calcular totales y porcentajes para VOK
        vok_total = round(df['VOK_Total'].sum()) if not df.empty else 'N/A'
        vok_buenos = round(df['VOK_Buenos'].sum()) if not df.empty else 'N/A'
        vok_malos = round(df['VOK_Malos'].sum()) if not df.empty else 'N/A'
        vok_promedio = (df['VOK_Buenos'].sum() / df['VOK_Total'].sum()) if not df.empty and df['VOK_Total'].sum() != 0 else 'N/A'

        # Calcular totales y porcentajes para CALRUTA
        calruta_total, calruta_promedio = cargar_datos_calruta(semana, cliente) if cliente else cargar_datos_calruta(semana)
        calruta_total = round(calruta_total) if calruta_total != 'N/A' else 'N/A'

        # Leer el porcentaje actualizado de calruta_percentage.json solo si no hay cliente seleccionado
        if not cliente:
            calruta_file = os.path.join(SEMANAS_FOLDER, 'calruta_percentage.json')
            if os.path.exists(calruta_file):
                with open(calruta_file, 'r') as f:
                    calruta_data = json.load(f)
                calruta_actualizado = calruta_data.get(semana, 'N/A')
            else:
                calruta_actualizado = 'N/A'
        else:
            calruta_actualizado = f"{calruta_promedio:.2%}" if calruta_promedio != 'N/A' else 'N/A'

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
                'total': calruta_total,
                'porcentaje': calruta_actualizado
            }
        }
        return render_template('index.html', data=data, clientes=clientes, request=request, semanas=SEMANA_ARCHIVOS, semana=semana, cliente=cliente, semana_fechas=SEMANA_FECHAS, tabla_clientes=tabla_clientes)
    except Exception as e:
        return f"<h3>Error al leer archivo: {str(e)}</h3>"

@app.route('/grafica')
def grafica():
    try:
        semana = request.args.get('semana', 'semana_14')
        df = cargar_datos(semana)
        cliente = request.args.get('cliente', '')
        if cliente:
            df = df[df['Cliente'] == cliente]
        if df.empty:
            return jsonify({'error': 'No hay datos para este cliente'}), 400
            
        metrica = request.args.get('metrica', 'N5_%')
        import plotly.graph_objects as go

        if metrica == 'N5_%':
            total = df['N5_TOTAL'].sum()
            buenos = df['N5_Buenos'].sum()
            malos = df['n5_malos'].sum()
            cumplimiento = buenos / total if total else 0
            valores = [buenos, malos]
            etiquetas = ['Buenos', 'Malos']
            titulo = f"NS - Cumplimiento: {cumplimiento:.2%}"
        elif metrica == 'VOK_%':
            total = df['VOK_Total'].sum()
            buenos = df['VOK_Buenos'].sum()
            malos = df['VOK_Malos'].sum()
            cumplimiento = buenos / total if total else 0
            valores = [buenos, malos]
            etiquetas = ['Buenos', 'Malos']
            titulo = f"VOK - Cumplimiento: {cumplimiento:.2%}"
        elif metrica == 'CAL_RUTA':
            if 'rutas' in df.columns and 'cr' in df.columns:
                total = df['rutas'].sum()
                buenas = (df['rutas'] * df['cr']).sum()
                malas = total - buenas
                cumplimiento = buenas / total if total else 0
                valores = [buenas, malas]
                etiquetas = ['Buenas', 'Con Problemas']
                titulo = f"Calidad de Ruta - Cumplimiento: {cumplimiento:.2%}"
            else:
                total = 0
                valores = [0]
                etiquetas = ['Total']
                titulo = "Calidad de Ruta"
        else:
            total = 0
            valores = [0]
            etiquetas = ['Total']
            titulo = "Métrica desconocida"

        fig = go.Figure(data=[go.Pie(
            labels=etiquetas,
            values=valores,
            hole=0.4,
            marker=dict(
                colors=['#198754', '#dc3545'] if len(valores) > 1 else ['#198754'],
                line=dict(color='white', width=2)
            ),
            textinfo='percent',
            textposition='outside',
            showlegend=False
        )])

        fig.update_layout(
            title_text=titulo,
            margin=dict(l=20, r=120, t=40, b=20),
            annotations=[
                dict(
                    text=f"<b>Total:</b> {sum(valores)}",
                    x=1.2, y=0.5,
                    xref="paper", yref="paper",
                    showarrow=False,
                    align="left",
                    font=dict(size=14)
                )
            ]
        )

        return jsonify(fig.to_json())
    except Exception as e:
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

        # Obtener logs de actividad
        logs = get_activity_logs()

        # Pasar las semanas disponibles al template
        return render_template('admin_dashboard.html', 
                               files=files,
                               logs=logs,
                               semanas=SEMANA_ARCHIVOS)
    except Exception as e:
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

@app.route('/update_calruta_percentage', methods=['POST'])
def update_calruta_percentage():
    try:
        semana = request.form.get('semana')
        calruta_percentage = request.form.get('calruta_percentage')
        if semana and calruta_percentage:
            try:
                calruta_percentage = float(calruta_percentage)
                if not (0 <= calruta_percentage <= 100):
                    raise ValueError("El porcentaje debe estar entre 0 y 100.")
            except ValueError:
                flash('Por favor, ingrese un porcentaje válido entre 0 y 100.', 'error')
                return redirect(url_for('admin_dashboard'))

            # Leer o crear el archivo JSON
            calruta_file = os.path.join(SEMANAS_FOLDER, 'calruta_percentage.json')
            if os.path.exists(calruta_file):
                with open(calruta_file, 'r') as f:
                    calruta_data = json.load(f)
            else:
                calruta_data = {}

            # Actualizar el porcentaje para la semana seleccionada
            calruta_data[semana] = calruta_percentage
            with open(calruta_file, 'w') as f:
                json.dump(calruta_data, f, indent=4)

            flash(f'Porcentaje de Calidad de Ruta para {semana} actualizado correctamente.', 'success')
        else:
            flash('Por favor, seleccione una semana y proporcione un porcentaje válido.', 'error')
    except Exception as e:
        flash(f'Error al actualizar el porcentaje: {str(e)}', 'error')
    return redirect(url_for('admin_dashboard'))

@app.route('/detalle_evidencia_vok')
def detalle_evidencia_vok():
    try:
        semana = request.args.get('semana')
        cliente = request.args.get('cliente')

        # Leer el archivo correspondiente a la semana
        excel_path = SEMANA_ARCHIVOS.get(semana)
        if not excel_path or not os.path.exists(excel_path):
            return render_template('evidencia_vok.html', data=[], semana=semana, cliente=cliente)

        # Leer la hoja 'Evidencia_vok'
        df = pd.read_excel(excel_path, sheet_name='Evidencia_vok')
        df.columns = [c.strip() for c in df.columns]

        # Filtrar por cliente si aplica
        if cliente and 'cliente' in df.columns:
            df['cliente'] = df['cliente'].astype(str).str.strip()
            cliente = str(cliente).strip()
            df = df[df['cliente'] == cliente]

        # Seleccionar columnas relevantes (ajustar según la estructura de la hoja)
        columnas_evidencia = ['PLANTA', 'RUTAS', 'V MALOS', 'PROBLEMA']
        columnas_disponibles = [col for col in columnas_evidencia if col in df.columns]
        df = df[columnas_disponibles]

        # Convertir los datos a un diccionario para enviarlos al template
        data = df.to_dict(orient='records')
        return render_template('evidencia_vok.html', data=data, semana=semana, cliente=cliente)
    except Exception as e:
        print(f"Error al cargar datos de Evidencia_vok: {str(e)}")
        return render_template('evidencia_vok.html', data=[], semana=semana, cliente=cliente, error=str(e))

@app.route('/detalle_evidencia_ns')
def detalle_evidencia_ns():
    try:
        semana = request.args.get('semana')
        cliente = request.args.get('cliente')

        # Leer el archivo correspondiente a la semana
        excel_path = SEMANA_ARCHIVOS.get(semana)
        if not excel_path or not os.path.exists(excel_path):
            return render_template('evidencia_ns.html', data=[], semana=semana, cliente=cliente)

        # Leer la hoja 'Evidencia_ns'
        df = pd.read_excel(excel_path, sheet_name='Evidencia_ns')
        df.columns = [c.strip() for c in df.columns]

        # Filtrar por cliente si aplica
        if cliente and 'PLANTA' in df.columns:
            df['PLANTA'] = df['PLANTA'].astype(str).str.strip()
            cliente = str(cliente).strip()
            df = df[df['PLANTA'] == cliente]

        # Seleccionar columnas relevantes (ajustar según la estructura de la hoja)
        columnas_evidencia = [
            "PLANTA",	"RUTAS",	"V MALOS",	"INI RUTA",	"FIN RUTA",	"Observacion",
        ]
        columnas_disponibles = [col for col in columnas_evidencia if col in df.columns]
        df = df[columnas_disponibles]

        # Convertir los datos a un diccionario para enviarlos al template
        data = df.to_dict(orient='records')
        return render_template('evidencia_ns.html', data=data, semana=semana, cliente=cliente)
    except Exception as e:
        print(f"Error al cargar datos de Evidencia_ns: {str(e)}")
        return render_template('evidencia_ns.html', data=[], semana=semana, cliente=cliente, error=str(e))

@app.route('/api/ultimo_archivo_subido')
def api_ultimo_archivo_subido():
    try:
        archivos = [f for f in os.listdir(SEMANAS_FOLDER) if f.startswith('semana_completa_') and f.endswith('.xlsx')]
        if not archivos:
            return jsonify({'archivo': None, 'semana': None})
        archivos.sort(key=lambda f: os.path.getmtime(os.path.join(SEMANAS_FOLDER, f)), reverse=True)
        ultimo_archivo = archivos[0]
        # Extraer la semana del nombre del archivo
        semana = ultimo_archivo.replace('semana_completa_', '').replace('.xlsx', '')
        return jsonify({'archivo': ultimo_archivo, 'semana': f'semana_{semana}'})
    except Exception as e:
        return jsonify({'archivo': None, 'semana': None})
if __name__ == '__main__':
    app.run(debug=True)


