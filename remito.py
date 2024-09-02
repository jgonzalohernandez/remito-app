import streamlit as st
import pyodbc
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import utils
import pandas as pd
import os
from datetime import datetime

# Función para conectar a la base de datos SQL Server
def conectar_db():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-GO4SP4V;'
        'DATABASE=Motoya;'
        'Trusted_Connection=yes;'
    )
    return conn

# Función para leer el número de remito desde la base de datos
def leer_numero_remito():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(RemitoNumero) FROM Remitos")
    max_remito = cursor.fetchone()[0]
    conn.close()
    if max_remito:
        return max_remito + 1
    else:
        return 5940  # Número inicial si no hay registros

# Función para guardar el remito en la base de datos
def guardar_en_base_datos(remito_numero, fecha, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, lluvia, exclusividad, cantidad_bultos, pdf_path):
    conn = conectar_db()
    cursor = conn.cursor()

    # Insertar en la tabla Remitos
    cursor.execute("""
        INSERT INTO Remitos (RemitoNumero, Fecha, Cliente, Domicilio, Sector, Solicitante, Moto, TotalImporte, Lluvia, Exclusividad, CantidadBultos, PDFPath)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, remito_numero, fecha, cliente, domicilio, sector, solicitante, moto, total_importe, lluvia, exclusividad, cantidad_bultos, pdf_path)
    
    # Obtener el ID del remito recién insertado
    remito_id = cursor.execute("SELECT SCOPE_IDENTITY()").fetchval()

    # Insertar en la tabla DetalleRemitos
    for index, row in detalle_df.iterrows():
        cursor.execute("""
            INSERT INTO DetalleRemitos (RemitoID, Direccion, Monto)
            VALUES (?, ?, ?)
        """, remito_id, row['Dirección'], row['Monto'])

    conn.commit()
    cursor.close()
    conn.close()

# Función para cargar la lista de remitos guardados
def cargar_remitos_guardados(carpeta_remitos='remitos'):
    if not os.path.exists(carpeta_remitos):
        os.makedirs(carpeta_remitos)
    remitos = [f for f in os.listdir(carpeta_remitos) if f.endswith('.pdf')]
    return remitos

# El resto de las funciones permanece igual (cargar_logo, generar_pdf, guardar_en_csv, etc.)

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
cantidad_bultos = 0
if bultos:
    cantidad_bultos = st.number_input("Cantidad de bultos", min_value=1, value=1)
    total_importe += 2500 * cantidad_bultos

if 'numero_remito' not in st.session_state:
    st.session_state['numero_remito'] = leer_numero_remito()

logo_image_path = "logo motoya curvas-1.jpg"

if st.button("Generar Remito"):
    if cliente and domicilio and sector y solicitante and moto and not detalle_df.empty:
        fecha_str = fecha.strftime('%Y-%m-%d')
        pdf_path = generar_pdf(st.session_state['numero_remito'], fecha_str, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, logo_image_path, lluvia, exclusividad, cantidad_bultos)
        st.success(f"Remito generado con éxito: {pdf_path}")
        st.download_button(label="Descargar Remito", data=open(pdf_path, "rb"), file_name=pdf_path, mime="application/pdf")
        
        # Guardar en la base de datos
        guardar_en_base_datos(st.session_state['numero_remito'], fecha_str, cliente, domicilio, sector, solicitante, moto, detalle_df, total_importe, lluvia, exclusividad, cantidad_bultos, pdf_path)
        
        st.session_state['numero_remito'] += 1
    else:
        st.error("Por favor, completa todos los campos antes de generar el remito.")

st.header("Descargar Remitos Generados")
remitos_guardados = cargar_remitos_guardados()
remito_seleccionado = st.selectbox("Selecciona un remito para descargar", remitos_guardados)

if st.button("Descargar Remito Seleccionado"):
    with open(os.path.join('remitos', remito_seleccionado), 'rb') as f:
        st.download_button(label="Descargar Remito", data=f, file_name=remito_seleccionado, mime='application/pdf')
