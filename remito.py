import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import utils
import pandas as pd
import os
from datetime import datetime
from github import Github
import base64
import io

# Obtén el token desde la variable de entorno o reemplázalo por el token de GitHub aquí
GITHUB_TOKEN = os.getenv('GITHUB_PAT')  # Asegúrate de que este valor esté configurado
REPO_NAME = "tu-usuario/ArchivosGenerados"  # Reemplaza con tu repositorio

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# Función para subir archivos a GitHub
def subir_a_github(ruta_archivo, nombre_archivo):
    with open(ruta_archivo, 'rb') as file:
        contenido = file.read()
        contenido_base64 = base64.b64encode(contenido).decode('utf-8')
        
    # Verifica si el archivo ya existe
    try:
        contenido_existente = repo.get_contents(nombre_archivo)
        repo.update_file(contenido_existente.path, f"Actualiza {nombre_archivo}", contenido_base64, contenido_existente.sha)
    except:
        repo.create_file(nombre_archivo, f"Sube {nombre_archivo}", contenido_base64)

# Función para cargar la lista de remitos guardados en el repositorio de GitHub
def cargar_remitos_guardados_github():
    remitos = []
    try:
        contenidos = repo.get_contents("")
        for contenido in contenidos:
            if contenido.path.endswith('.pdf'):
                remitos.append(contenido.path)
    except Exception as e:
        st.error(f"Error al cargar remitos guardados: {e}")
    return remitos

# Función para leer el número de remito desde GitHub
def leer_numero_remito():
    try:
        contenido = repo.get_contents("ultimo_remito.txt")
        numero_remito = int(contenido.decoded_content.decode('utf-8'))
        return numero_remito
    except:
        return 5980  # Valor inicial si no hay registros

# Función para guardar el número de remito en GitHub
def guardar_numero_remito(numero):
    try:
        contenido = repo.get_contents("ultimo_remito.txt")
        repo.update_file(contenido.path, "Actualiza último remito", str(numero), contenido.sha)
    except:
        repo.create_file("ultimo_remito.txt", "Crea archivo de último remito", str(numero))

# Función para generar el remito en PDF
def generar_pdf(remito_numero, fecha, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, logo_path, lluvia, exclusividad, cantidad_bultos):
    carpeta_remitos = 'remitos'

    if not os.path.exists(carpeta_remitos):
        os.makedirs(carpeta_remitos)

    pdf_path = os.path.join(carpeta_remitos, f'remito_{remito_numero}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=A4)

    logo, logo_ancho, logo_alto = cargar_logo(logo_path, 210 * mm)
    c.saveState()
    c.setFillAlpha(0.3)
    c.drawImage(logo, (210 * mm - logo_ancho) / 2, (297 * mm - logo_alto) / 2, width=logo_ancho, height=logo_alto, mask='auto')
    c.restoreState()

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, 280 * mm, "Motoya Mensajería")
    c.drawString(20 * mm, 275 * mm, "Cel.: 15-4194-6280")
    c.drawString(20 * mm, 270 * mm, "Email: motoyamensajeria@gmail.com")
    c.drawString(20 * mm, 265 * mm, "Web: www.motoya.com.ar")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(105 * mm, 255 * mm, "ORDEN DE SERVICIO")

    c.setFont("Helvetica", 10)
    c.drawRightString(195 * mm, 255 * mm, f"N° de Servicio: {remito_numero}")
    c.drawRightString(195 * mm, 250 * mm, f"Fecha: {fecha}")

    margin_top = 240 * mm
    inner_margin = 10 * mm

    c.rect(15 * mm, margin_top - 55 * mm, 180 * mm, 55 * mm, stroke=1, fill=0)
    c.drawString(20 * mm + inner_margin, margin_top - 10 * mm, f"Cliente: {cliente}")
    c.drawString(20 * mm + inner_margin, margin_top - 20 * mm, f"Domicilio: {domicilio}")
    c.drawString(20 * mm + inner_margin, margin_top - 30 * mm, f"Sector: {sector}")
    c.drawString(20 * mm + inner_margin, margin_top - 40 * mm, f"Solicitante: {solicitante}")
    c.drawString(20 * mm + inner_margin, margin_top - 50 * mm, f"Moto: {moto}")

    c.setDash(1, 2)
    detalle_y_position = 160 * mm
    for index, row in detalle_df.iterrows():
        c.drawString(20 * mm, detalle_y_position, f"{row['Dirección']}")
        c.drawRightString(195 * mm, detalle_y_position, f"${row['Monto']:.2f}")
        c.line(15 * mm, detalle_y_position - 2 * mm, 195 * mm, detalle_y_position - 2 * mm)
        detalle_y_position -= 10 * mm

    if cantidad_bultos > 0:
        c.drawString(20 * mm, detalle_y_position, f"Bulto(s) ({cantidad_bultos}):")
        c.drawRightString(195 * mm, detalle_y_position, f"${2500 * cantidad_bultos:.2f}")
        c.line(15 * mm, detalle_y_position - 2 * mm, 195 * mm, detalle_y_position - 2 * mm)
        detalle_y_position -= 10 * mm

    total_direcciones_monto = detalle_df["Monto"].sum() + (2500 * cantidad_bultos)
    if exclusividad:
        exclusividad_monto = total_direcciones_monto * 0.50
        c.drawString(20 * mm, detalle_y_position, "Exclusividad (50% incremento):")
        c.drawRightString(195 * mm, detalle_y_position, f"${exclusividad_monto:.2f}")
        c.line(15 * mm, detalle_y_position - 2 * mm, 195 * mm, detalle_y_position - 2 * mm)
        detalle_y_position -= 10 * mm
        total_importe += exclusividad_monto

    if lluvia:
        lluvia_monto = total_direcciones_monto * 0.50
        c.drawString(20 * mm, detalle_y_position, "Lluvia (50% incremento):")
        c.drawRightString(195 * mm, detalle_y_position, f"${lluvia_monto:.2f}")
        c.line(15 * mm, detalle_y_position - 2 * mm, 195 * mm, detalle_y_position - 2 * mm)
        detalle_y_position -= 10 * mm
        total_importe += lluvia_monto

    c.setDash(1, 0)
    c.drawRightString(195 * mm, detalle_y_position - 10 * mm, f"Importe Total: ${total_importe:.2f}")

    firma_y_position = detalle_y_position - 30 * mm
    c.setDash(1, 2)
    c.line(20 * mm, firma_y_position + 15 * mm, 100 * mm, firma_y_position + 15 * mm)
    c.line(20 * mm, firma_y_position + 5 * mm, 100 * mm, firma_y_position + 5 * mm)
    c.setDash(1, 0)

    c.drawString(20 * mm, firma_y_position + 20 * mm, "Firma:")
    c.drawString(20 * mm, firma_y_position + 10 * mm, "Aclaración:")

    texto_y_position = firma_y_position - 15 * mm
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, texto_y_position, "La mercadería viaja por cuenta y riesgo del cliente.")
    c.save()

    # Sube el PDF generado a GitHub
    subir_a_github(pdf_path, f'remito_{remito_numero}.pdf')

    return pdf_path

# Función para guardar el remito en un archivo CSV
def guardar_en_csv(remito_numero, fecha, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, lluvia, exclusividad, cantidad_bultos):
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
    mes_anio = fecha_obj.strftime('%Y-%m')
    csv_path = f'remitos_{mes_anio}.csv'

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

    for i, row in detalle_df.iterrows():
        df[f'Dirección {i+1}'] = [row['Dirección']]
        df[f'Monto {i+1}'] = [row['Monto']]

    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')
    else:
        df.to_csv(csv_path, mode='w', header=True, index=False, sep=';', encoding='utf-8-sig')

    # Sube el CSV generado a GitHub
    subir_a_github(csv_path, csv_path)

# Interfaz de Streamlit
st.title("Generador de Remitos Digitales")

fecha = st.date_input("Fecha del Remito", value=datetime.now())
cliente = st.text_input("Nombre del Cliente")
domicilio = st.text_input("Domicilio del Cliente")
sector = st.text_input("Sector del Cliente")
solicitante = st.text_input("Solicitante del Servicio")
moto = st.text_input("Moto que realizó el Servicio")

if 'detalle_data' not in st.session_state:
    st.session_state.detalle_data = []

num_rows = st.number_input("Cantidad de filas", min_value=1, max_value=20, value=len(st.session_state.detalle_data) or 1)

if len(st.session_state.detalle_data) < num_rows:
    for _ in range(num_rows - len(st.session_state.detalle_data)):
        st.session_state.detalle_data.append({"Dirección": "", "Monto": 0.0})
elif len(st.session_state.detalle_data) > num_rows:
    st.session_state.detalle_data = st.session_state.detalle_data[:num_rows]

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

detalle_df = pd.DataFrame(st.session_state.detalle_data)
total_importe = detalle_df["Monto"].sum()

lluvia = st.checkbox("¿Está lloviendo? (Incrementa un 50% la importación)")
exclusividad = st.checkbox("¿Es un viaje exclusivo? (Incrementa un 50% la importación)")
bultos = st.checkbox("¿Hay bultos? (Costo por bulto: $2500)")
cantidad_bultos = st.number_input("Cantidad de bultos", min_value=1, value=1) if bultos else 0
total_importe += 2500 * cantidad_bultos

if 'numero_remito' not in st.session_state:
    st.session_state['numero_remito'] = leer_numero_remito()

logo_image_path = "logo motoya curvas-1.jpg"

if st.button("Generar Remito"):
    if cliente and domicilio and sector and solicitante and moto and not detalle_df.empty:
        fecha_str = fecha.strftime('%Y-%m-%d')
        pdf_path = generar_pdf(st.session_state['numero_remito'], fecha_str, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, logo_image_path, lluvia, exclusividad, cantidad_bultos)
        st.success(f"Remito generado con éxito: {pdf_path}")
        st.download_button(label="Descargar Remito", data=open(pdf_path, "rb"), file_name=pdf_path, mime="application/pdf")
        guardar_en_csv(st.session_state['numero_remito'], fecha_str, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, lluvia, exclusividad, cantidad_bultos)
        st.session_state['numero_remito'] += 1
        guardar_numero_remito(st.session_state['numero_remito'])
    else:
        st.error("Por favor, completa todos los campos antes de generar el remito.")

if st.button("Descargar CSV de Remitos"):
    mes_anio = fecha.strftime('%Y-%m')
    csv_path = f'remitos_{mes_anio}.csv'
    with open(csv_path, 'rb') as f:
        st.download_button(label="Descargar CSV", data=f, file_name=csv_path, mime='text/csv')

st.header("Descargar Remitos Generados")
remitos_guardados = cargar_remitos_guardados_github()
remito_seleccionado = st.selectbox("Selecciona un remito para descargar", remitos_guardados)

if st.button("Descargar Remito Seleccionado"):
    contenido_remito = repo.get_contents(remito_seleccionado)
    st.download_button(label="Descargar Remito", data=base64.b64decode(contenido_remito.content), file_name=remito_seleccionado, mime='application/pdf')
