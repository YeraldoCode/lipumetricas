from flask import Flask, flash, redirect, render_template, request, jsonify, url_for
import pandas as pd
import os
from utils.file_handler import allowed_file, combine_excel_files, save_file, read_excel
from config import SEMANAS_FOLDER, DETALLES_FOLDER, SECRET_KEY

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = SEMANAS_FOLDER
app.secret_key = SECRET_KEY

SEMANA_ARCHIVOS = {
    'semana_14': 'semana/datos-semana-14.xlsx',
    'semana_15': 'semana/datos-semana-15.xlsx',
    'semana_16': 'semana/datos-semana-16.xlsx'
}

SEMANA_FECHAS = {
    'semana_14': '31-marzo a 6-abril',
    'semana_15': '7-abril a 13-abril',
    'semana_16': '14-abril a 20-abril'
}


def cargar_detalle_generico(semana, metrica, cliente=None):
    partes = semana.split('_')
    if len(partes) != 2:
        raise ValueError(f"Formato de semana inválido: {semana}")
    
    archivo = f"detalles/detalle-semana-{partes[1]}-{metrica}.xlsx"
    print(f"Intentando abrir archivo: {archivo}")  # Debug
    
    if not os.path.exists(archivo):
        raise FileNotFoundError(f"Archivo no encontrado: {archivo}")
    
    # Leer el archivo desde la celda A2
    df = pd.read_excel(archivo, skiprows=1)
    
    # Mantener los valores originales sin convertir
    df = df.astype(str)
    
    try:
        if metrica == 'ns':
            # Intenta seleccionar las columnas por nombre para NS
            df = df[['c', 'des', 'Suma de ns_val', 'Suma de ns_val_ok', 'Suma de ns_p', 'Suma de malos']]
        elif metrica == 'vok':
            # Intenta seleccionar las columnas por nombre para VOK
            df = df[['c', 'Des', 'vok_val', 'vok_val_ok', 'vok_p', 'malos']]
    except KeyError as e:
        print(f"Error al seleccionar columnas: {e}")
        # Si falla, intenta con nombres alternativos o muestra todas las columnas
        
        # Mapeo de posibles nombres de columnas
        column_mapping = {}
        for i, col in enumerate(df.columns):
            col_lower = str(col).lower()
            if 'cliente' in col_lower or 'c' == col_lower:
                column_mapping[col] = 'c'
            elif 'desc' in col_lower or 'des' in col_lower:
                column_mapping[col] = 'des' if metrica == 'ns' else 'Des'
            elif 'ns_val' in col_lower and 'ok' not in col_lower:
                column_mapping[col] = 'Suma de ns_val'
            elif 'ns_val_ok' in col_lower or 'val_ok' in col_lower:
                column_mapping[col] = 'Suma de ns_val_ok'
            elif 'ns_p' in col_lower or 'ns_%' in col_lower:
                column_mapping[col] = 'Suma de ns_p'
            elif 'vok_val' in col_lower and 'ok' not in col_lower:
                column_mapping[col] = 'vok_val'
            elif 'vok_val_ok' in col_lower or 'val_ok' in col_lower:
                column_mapping[col] = 'vok_val_ok'
            elif 'vok_p' in col_lower or 'vok_%' in col_lower:
                column_mapping[col] = 'vok_p'
            elif 'malo' in col_lower:
                column_mapping[col] = 'malos'
        
        # Renombrar columnas
        df = df.rename(columns=column_mapping)
    
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip()
    
    if cliente:
        df['c'] = df['c'].astype(str).str.strip()
        cliente = cliente.strip()
        df = df[df['c'] == cliente]
    
    # Calcular el porcentaje y formatearlo como cadena con dos decimales
    if metrica == 'ns':
        df['Suma de ns_p'] = (df['Suma de ns_val_ok'].astype(float) / df['Suma de ns_val'].astype(float) * 100).map("{:.2f}".format)
        # Filtrar filas donde 'Suma de malos' es mayor o igual a 1
        df = df[df['Suma de malos'].astype(float) >= 1]
    elif metrica == 'vok':
        df['vok_p'] = (df['vok_val_ok'].astype(float) / df['vok_val'].astype(float) * 100).map("{:.2f}".format)
        # Filtrar filas donde 'malos' es mayor o igual a 1
        df = df[df['malos'].astype(float) >= 1]
    
    # Convertir a diccionario manteniendo los valores originales
    result = df.to_dict(orient='records')
    print(f"Registros encontrados: {len(result)}")  # Debug
    
    if result:
        print("Primer registro:", result[0])
    
    return result

def cargar_datos(semana):
    excel_path = SEMANA_ARCHIVOS.get(semana)
    if not excel_path or not os.path.exists(excel_path):
        raise FileNotFoundError(f"Archivo no encontrado para {semana}")
    df = pd.read_excel(excel_path)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={'c': 'Cliente'})
    for col in ['N5_%', 'VOK_%']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('%','').str.replace(',','.').astype(float)
            if df[col].max() > 1.5:
                df[col] = df[col] / 100
    return df


@app.route('/')
def index():
    try:
        semana = request.args.get('semana', 'semana_14')
        df = cargar_datos(semana)
        clientes = df['Cliente'].dropna().unique()
        cliente = request.args.get('cliente', '')
        if cliente:
            df = df[df['Cliente'] == cliente]
        row = df.iloc[0] if not df.empty else {}
        data = {
            'cliente': cliente or 'Todos',
            'semana': semana,
            'ns': {
                'total': row.get('N5_TOTAL', 'N/A'),
                'buenos': row.get('N5_Buenos', 'N/A'),
                'malos': row.get('n5_malos', 'N/A'),
                'porcentaje': f"{row.get('N5_%', 'N/A'):.2%}" if row.get('N5_%', None) not in [None, 'N/A'] else 'N/A'
            },
            'vok': {
                'total': row.get('VOK_Total', 'N/A'),
                'buenos': row.get('VOK_Buenos', 'N/A'),
                'malos': row.get('VOK_Malos', 'N/A'),
                'porcentaje': f"{row.get('VOK_%', 'N/A'):.2%}" if row.get('VOK_%', None) not in [None, 'N/A'] else 'N/A'
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

@app.route('/detalle/<metrica>')
def detalle_metrica(metrica):
    try:
        semana = request.args.get('semana', 'semana_14')
        cliente = request.args.get('cliente')
        print(f"Procesando detalle: metrica={metrica}, semana={semana}, cliente={cliente}")  # Debug
        
        data = cargar_detalle_generico(semana, metrica, cliente)
        print(f"Datos cargados: {len(data)} registros")  # Debug
        
        return render_template(
            f"detalle_{metrica}.html",
            data=data,
            semana=semana,
            cliente=cliente,
            titulo=metrica.upper()
        )
    except Exception as e:
        print(f"Error: {str(e)}")  # Debug
        return f"<h3>Error al cargar detalle: {str(e)}</h3>"

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
        row = df.iloc[0]
        metrica = request.args.get('metrica', 'N5_%')
        import plotly.graph_objects as go

        if metrica == 'N5_%':
            total = row.get('N5_TOTAL', 0)
            buenos = row.get('N5_Buenos', 0)
            malos = row.get('n5_malos', 0)
            cumplimiento = buenos / total if total else 0
            valores = [buenos, malos]
            etiquetas = ['Buenos', 'Malos']
            titulo = f"NS - Cumplimiento: {cumplimiento:.2%}"
        elif metrica == 'VOK_%':
            total = row.get('VOK_Total', 0)
            buenos = row.get('VOK_Buenos', 0)
            malos = row.get('VOK_Malos', 0)
            cumplimiento = buenos / total if total else 0
            valores = [buenos, malos]
            etiquetas = ['Buenos', 'Malos']
            titulo = f"VOK - Cumplimiento: {cumplimiento:.2%}"
        else:
            total = row.get('CalRuta_Total', 0)
            valores = [total]
            etiquetas = ['Total']
            titulo = f"Calidad de Ruta"

        fig = go.Figure(data=[go.Pie(
            labels=etiquetas,
            values=valores,
            hole=0.4,
            marker=dict(colors=['#6A75CF']*len(valores), line=dict(color='white', width=2)),
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
    

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Verificar si al menos un archivo está presente en la solicitud
        if not any(request.files.get(key) for key in ['semanaFile', 'detalleNsFile', 'detalleVokFile', 'detalleCalidadRutaFile']):
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)
        
        # Obtener los archivos de la solicitud
        semana_file = request.files.get('semanaFile')
        detalle_ns_file = request.files.get('detalleNsFile')
        detalle_vok_file = request.files.get('detalleVokFile')
        detalle_calidad_ruta_file = request.files.get('detalleCalidadRutaFile')
        
        # Procesar cada archivo si está presente
        if semana_file and allowed_file(semana_file.filename):
            semana_filepath = os.path.join(SEMANAS_FOLDER, semana_file.filename)
            semana_file.save(semana_filepath)
            flash(f'Archivo {semana_file.filename} subido exitosamente', 'success')
        
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

if __name__ == '__main__':
    app.run(debug=True)
