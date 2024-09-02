import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import utils
import pandas as pd
import os
from datetime import datetime
import pyodbc

# Configuración de la conexión a la base de datos SQL Server
def conectar_db():
    conn_str = (
        r'DRIVER={SQL Server};'
        r'SERVER=localhost;'
        r'DATABASE=MOTOYA;'
        r'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

# Función para cargar la lista de remitos guardados desde la base de datos
def cargar_remitos_guardados():
    conn = conectar_db()
    query = "SELECT NumeroRemito, PDFPath FROM Remitos"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Función para cargar la imagen del logo desde un archivo JPG
def cargar_logo(path, width):
    img = utils.ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return path, width, int(width * aspect)

# Función para leer el número de remito desde la base de datos
def leer_numero_remito():
    conn = conectar_db()
    query = "SELECT MAX(NumeroRemito) FROM Remitos"
    result = pd.read_sql(query, conn)
    conn.close()
    if result.iloc[0, 0] is not None:
        return result.iloc[0, 0] + 1
    else:
        return 5940  # Número inicial si no hay registros

# Función para guardar el número de remito en la base de datos
def guardar_numero_remito(remito_numero, pdf_path):
    conn = conectar_db()
    cursor = conn.cursor()
    query = "INSERT INTO Remitos (NumeroRemito, Fecha, Cliente, Domicilio, Sector, Solicitante, Moto, TotalImporte, Lluvia, Exclusividad, CantidadBultos, PDFPath) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    cursor.execute(query, remito_numero)
    conn.commit()
    conn.close()

# Función para generar el remito en PDF
def generar_pdf(remito_numero, fecha, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, logo_path, lluvia, exclusividad, cantidad_bultos, carpeta_remitos='remitos'):
    # Asegurar que la carpeta de remitos exista
    if not os.path.exists(carpeta_remitos):
        os.makedirs(carpeta_remitos)
    
    # Definir la ruta completa del PDF
    pdf_path = os.path.join(carpeta_remitos, f'remito_{remito_numero}.pdf')
    
    # Crear el PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)

    # Colocar el logo como marca de agua en toda la página, con mayor opacidad
    logo, logo_ancho, logo_alto = cargar_logo(logo_path, 210*mm)  # Ajustamos el tamaño para que cubra toda la página
    c.saveState()
    c.setFillAlpha(0.3)  # Aumentar la opacidad del logo para que se vea más oscuro
    c.drawImage(logo, (210*mm - logo_ancho) / 2, (297*mm - logo_alto) / 2, width=logo_ancho, height=logo_alto, mask='auto')
    c.restoreState()

    # Información de la empresa en la parte superior izquierda con mayor espacio entre los elementos
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, 280*mm, "Motoya Mensajería")
    c.drawString(20*mm, 275*mm, "Cel.: 15-4194-6280")
    c.drawString(20*mm, 270*mm, "Email: motoyamensajeria@gmail.com")
    c.drawString(20*mm, 265*mm, "Web: www.motoya.com.ar")

    # Título centrado "ORDEN DE SERVICIO"
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(105*mm, 255*mm, "ORDEN DE SERVICIO")

    # Número de Servicio alineado a la derecha
    c.setFont("Helvetica", 10)
    c.drawRightString(195*mm, 255*mm, f"N° de Servicio: {remito_numero}")

    # Fecha del remito alineada a la derecha
    c.setFont("Helvetica", 10)
    c.drawRightString(195*mm, 250*mm, f"Fecha: {fecha}")

    # Ajuste del margen de la caja para los datos del cliente (con más espacio interno)
    margin_top = 240*mm  # Ajuste de la posición de la caja para que no se solape con los datos de la empresa
    inner_margin = 10*mm  # Incrementar margen interno para evitar que los datos toquen las líneas de la caja

    # Cuadro para el área del cliente
    c.rect(15*mm, margin_top - 55*mm, 180*mm, 55*mm, stroke=1, fill=0)  # Aumentar la altura de la caja
    c.drawString(20*mm + inner_margin, margin_top - 10*mm, f"Cliente: {cliente}")
    c.drawString(20*mm + inner_margin, margin_top - 20*mm, f"Domicilio: {domicilio}")
    c.drawString(20*mm + inner_margin, margin_top - 30*mm, f"Sector: {sector}")
    c.drawString(20*mm + inner_margin, margin_top - 40*mm, f"Solicitante: {solicitante}")
    c.drawString(20*mm + inner_margin, margin_top - 50*mm, f"Moto: {moto}")

    # Detalle del servicio con líneas punteadas (sin cajas)
    c.setDash(1, 2)
    detalle_y_position = 160*mm
    for index, row in detalle_df.iterrows():
        c.drawString(20*mm, detalle_y_position, f"{row['Dirección']}")
        c.drawRightString(195*mm, detalle_y_position, f"${row['Monto']:.2f}")
        c.line(15*mm, detalle_y_position - 2*mm, 195*mm, detalle_y_position - 2*mm)
        detalle_y_position -= 10*mm

    # Agregar el detalle de los bultos si corresponde
    if cantidad_bultos > 0:
        c.drawString(20*mm, detalle_y_position, f"Bulto(s) ({cantidad_bultos}):")
        c.drawRightString(195*mm, detalle_y_position, f"${2500 * cantidad_bultos:.2f}")  # Valor del bulto actualizado a $2500
        c.line(15*mm, detalle_y_position - 2*mm, 195*mm, detalle_y_position - 2*mm)
        detalle_y_position -= 10*mm

    # Calcular los incrementos por exclusividad y lluvia sobre el total
    total_direcciones_monto = detalle_df["Monto"].sum() + (2500 * cantidad_bultos)  # Valor del bulto actualizado a $2500
    if exclusividad:
        exclusividad_monto = total_direcciones_monto * 0.50
        c.drawString(20*mm, detalle_y_position, "Exclusividad (50% incremento):")
        c.drawRightString(195*mm, detalle_y_position, f"${exclusividad_monto:.2f}")
        c.line(15*mm, detalle_y_position - 2*mm, 195*mm, detalle_y_position - 2*mm)
        detalle_y_position -= 10*mm
        total_importe += exclusividad_monto

    if lluvia:
        lluvia_monto = total_direcciones_monto * 0.50
        c.drawString(20*mm, detalle_y_position, "Lluvia (50% incremento):")
        c.drawRightString(195*mm, detalle_y_position, f"${lluvia_monto:.2f}")
        c.line(15*mm, detalle_y_position - 2*mm, 195*mm, detalle_y_position - 2*mm)
        detalle_y_position -= 10*mm
        total_importe += lluvia_monto

    c.setDash(1, 0)

    # Importe total alineado a la derecha
    c.drawRightString(195*mm, detalle_y_position - 10*mm, f"Importe Total: ${total_importe:.2f}")

    # Cuadro de firma y aclaración con líneas punteadas
    firma_y_position = detalle_y_position - 30*mm
    c.setDash(1, 2)
    c.line(20*mm, firma_y_position + 15*mm, 100*mm, firma_y_position + 15*mm)
    c.line(20*mm, firma_y_position + 5*mm, 100*mm, firma_y_position + 5*mm)
    c.setDash(1, 0)

    c.drawString(20*mm, firma_y_position + 20*mm, "Firma:")
    c.drawString(20*mm, firma_y_position + 10*mm, "Aclaración:")

    # Texto adicional en la parte inferior
    texto_y_position = firma_y_position - 15*mm
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, texto_y_position, "La mercadería viaja por cuenta y riesgo del cliente. Los días de lluvia y los horarios nocturnos sufren un incremento del 50%.")
    c.drawString(20*mm, texto_y_position - 5*mm, "Cada trámite incluye una tolerancia de espera de hasta 10 minutos, transcurrido ese lapso se cobrará la demora. (Regla general del Servicio)")

    c.save()
    return pdf_path

# Función para guardar el remito en un archivo CSV
def guardar_en_csv(remito_numero, fecha, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, lluvia, exclusividad, cantidad_bultos):
    # Obtener el nombre del archivo CSV basado en el mes y año
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    mes_anio = fecha_obj.strftime('%Y-%m')
    csv_path = f'remitos_{mes_anio}.csv'

    # Crear un DataFrame con la información del remito
    df = pd.DataFrame({
        'Fecha': [fecha],
        'Número de Remito': [remito_numero],
        'Cliente': [cliente],
        'Domicilio': [domicilio],
        'Sector': [sector],
        'Solicitante': [solicitante],
        'Moto': [moto],
        'Total Importe': [total_importe],
        'Lluvia': ['Sí' if lluvia else 'No'],
        'Exclusividad': ['Sí' if exclusividad else 'No'],
        'Cantidad de Bultos': [cantidad_bultos],
    })
    
    # Agregar los detalles del remito al DataFrame
    for i, row in detalle_df.iterrows():
        df[f'Dirección {i+1}'] = [row['Dirección']]
        df[f'Monto {i+1}'] = [row['Monto']]
    
    # Verificar si el archivo ya existe
    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')
    else:
        df.to_csv(csv_path, mode='w', header=True, index=False, sep=';', encoding='utf-8-sig')

    # Guardar los detalles del remito en la base de datos
    conn = conectar_db()
    cursor = conn.cursor()
    for i, row in detalle_df.iterrows():
        query = "INSERT INTO DetalleRemitos (NumeroRemito, Direccion, Monto) VALUES (?, ?, ?)"
        cursor.execute(query, remito_numero, row['Dirección'], row['Monto'])
    conn.commit()
    conn.close()

# Interfaz de Streamlit
st.title("Generador de Remitos Digitales")

# Campo para la fecha
fecha = st.date_input("Fecha del Remito", value=datetime.now())

# Campos del formulario
cliente = st.text_input("Nombre del Cliente")
domicilio = st.text_input("Domicilio del Cliente")
sector = st.text_input("Sector del Cliente")
solicitante = st.text_input("Solicitante del Servicio")
moto = st.text_input("Moto que realizó el Servicio")

# Guardar el estado de las direcciones y montos en st.session_state
if 'detalle_data' not in st.session_state:
    st.session_state.detalle_data = []

# Actualizar la cantidad de filas sin perder los datos previos
num_rows = st.number_input("Cantidad de filas", min_value=1, max_value=20, value=len(st.session_state.detalle_data) or 1)

# Ajustar la lista de datos según la cantidad de filas
if len(st.session_state.detalle_data) < num_rows:
    for _ in range(num_rows - len(st.session_state.detalle_data)):
        st.session_state.detalle_data.append({"Dirección": "", "Monto": 0.0})
elif len(st.session_state.detalle_data) > num_rows:
    st.session_state.detalle_data = st.session_state.detalle_data[:num_rows]

# Mostrar los campos para cada fila
for i in range(num_rows):
    col1, col2 = st.columns([2, 1])
    with col1:
        st.session_state.detalle_data[i]["Dirección"] = st.text_input(f"Dirección {i+1}", value=st.session_state.detalle_data[i]["Dirección"], key=f"direccion_{i}")
    with col2:
        monto_str = st.text_input(f"Monto {i+1}", value=str(st.session_state.detalle_data[i]["Monto"]), key=f"monto_{i}")
        try:
            st.session_state.detalle_data[i]["Monto"] = float(monto_str)
        except ValueError:
            st.session_state.detalle_data[i]["Monto"] = 0.0

# Convertir la lista de detalles en un DataFrame
detalle_df = pd.DataFrame(st.session_state.detalle_data)

# Sumar los montos para calcular el total
total_importe = detalle_df["Monto"].sum()

# Checkbox para seleccionar si llueve
lluvia = st.checkbox("¿Está lloviendo? (Incrementa un 50% la importación)")

# Checkbox para seleccionar si es un viaje exclusivo
exclusividad = st.checkbox("¿Es un viaje exclusivo? (Incrementa un 50% la importación)")

# Seleccionar si hay bultos y la cantidad de bultos
bultos = st.checkbox("¿Hay bultos? (Costo por bulto: $2500)")
cantidad_bultos = 0
if bultos:
    cantidad_bultos = st.number_input("Cantidad de bultos", min_value=1, value=1)
    total_importe += 2500 * cantidad_bultos  # Valor del bulto actualizado a $2500

# Leer el número de remito desde el archivo
if 'numero_remito' not in st.session_state:
    st.session_state['numero_remito'] = leer_numero_remito()

# Logo del talonario (ruta de la imagen JPG)
logo_image_path = "logo motoya curvas-1.jpg"

# Botón para generar el PDF del remito
if st.button("Generar Remito"):
    if cliente and domicilio and sector and solicitante and moto and not detalle_df.empty:
        fecha_str = fecha.strftime('%Y-%m-%d')
        pdf_path = generar_pdf(st.session_state['numero_remito'], fecha_str, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, logo_image_path, lluvia, exclusividad, cantidad_bultos)
        st.success(f"Remito generado con éxito: {pdf_path}")
        st.download_button(label="Descargar Remito", data=open(pdf_path, "rb"), file_name=pdf_path, mime="application/pdf")
        
        # Guardar el remito en el archivo CSV
        guardar_en_csv(st.session_state['numero_remito'], fecha_str, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, lluvia, exclusividad, cantidad_bultos)
        
        # Guardar el remito en la base de datos
        guardar_numero_remito(st.session_state['numero_remito'], pdf_path)
        
        # Incrementar y guardar el nuevo número de remito
        st.session_state['numero_remito'] += 1
        guardar_numero_remito(st.session_state['numero_remito'], pdf_path)
    else:
        st.error("Por favor, completa todos los campos antes de generar el remito.")

# Botón para descargar el archivo CSV
if st.button("Descargar CSV de Remitos"):
    mes_anio = fecha.strftime('%Y-%m')
    csv_path = f'remitos_{mes_anio}.csv'
    with open(csv_path, 'rb') as f:
        st.download_button(label="Descargar CSV", data=f, file_name=csv_path, mime='text/csv')

# Sección para descargar remitos generados
st.header("Descargar Remitos Generados")
remitos_guardados = cargar_remitos_guardados()
remito_seleccionado = st.selectbox("Selecciona un remito para descargar", remitos_guardados['PDFPath'])

if st.button("Descargar Remito Seleccionado"):
    with open(os.path.join('remitos', remito_seleccionado), 'rb') as f:
        st.download_button(label="Descargar Remito", data=f, file_name=remito_seleccionado, mime='application/pdf')
