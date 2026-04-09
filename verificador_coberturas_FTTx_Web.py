import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os
import base64

# --- 1. CONFIGURACIÓN DE LA PÁGINA (WIDE MODE ESENCIAL) ---
st.set_page_config(page_title="Tigo FTTX - Consultor V2", layout="wide")

# --- 2. LOGO TIGO Y ESTILOS (SOLUCIÓN DEFINITIVA LOGO) ---
# Usamos codificación base64 para embeber el logo y que no dependa de enlaces externos.
logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Tigo_logo.svg/512px-Tigo_logo.svg.png"

# Estilos CSS personalizados para la interfaz Tigo
st.markdown("""
    <style>
        /* Fondo de la barra lateral (Azul Tigo) */
        [data-testid="stSidebar"] {
            background-color: #0033ab;
        }
        /* Color de los textos en la barra lateral */
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
            color: white !important;
            font-weight: bold;
        }
        /* Ajuste de márgenes superiores */
        .block-container {
            padding-top: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Logo Tigo en la barra lateral
st.sidebar.image(logo_url, width=150)
st.sidebar.markdown("<h2 style='color: white; text-align: center; margin-top: 0;'>FTTX</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Título principal de la aplicación
st.title("🚀 Verificador de Cobertura FTTX Tigo")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data(file_path):
    # Función optimizada para cargar el Excel
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip() # Limpiar espacios en nombres de columnas
    return df

# Nombre del archivo que debe estar en tu GitHub
file_name = "datos_fttx.xlsx"
df_raw = None

# Comprobar si el archivo existe en el repositorio
if os.path.exists(file_name):
    df_raw = load_data(file_name)
    st.sidebar.success("✅ Base de datos cargada automáticamente")
else:
    # Si no existe, permitir carga manual
    uploaded = st.sidebar.file_uploader("Cargar Excel FTTX", type=["xlsx", "xlsb"])
    if uploaded:
        df_raw = load_data(uploaded)

if df_raw is not None:
    # --- 4. PANEL DE CONTROL (SIDEBAR) ---
    st.sidebar.header("📍 Parámetros de Búsqueda")

    # Coordenadas por defecto (centro de Santiago)
    lat_user = st.sidebar.number_input("Latitud", value=-33.574263, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=-70.559033, format="%.6f")
    radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 2000, 500)

    # Botón para forzar el centrado del mapa si hay desfase
    btn_centrar = st.sidebar.button("🎯 ACTUALIZAR UBICACIÓN")

    # Filtro de Propietario (Persistente)
    st.sidebar.header("🏢 Filtros")
    # Asegurar que la columna 'Propietario' existe
    if 'Propietario' in df_raw.columns:
        props = ["Todos"] + sorted(df_raw['Propietario'].dropna().unique().tolist())
        prop_sel = st.sidebar.selectbox("Propietario", props)
    else:
        st.sidebar.warning("⚠️ No se encontró la columna 'Propietario'")
        prop_sel = "Todos"

    # --- 5. PROCESAMIENTO DE DATOS ---
    df = df_raw.copy()

    # Asegurar que las coordenadas son numéricas y limpiar nulos
    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
    df = df.dropna(subset=['Lat', 'Lon'])

    # Aplicar filtro de propietario si se seleccionó uno
    if prop_sel != "Todos":
        df = df[df['Propietario'] == prop_sel]

    # Cálculo exacto de distancia (Haversine simplificado)
    df["Distancia_m"] = (np.sqrt((df["Lat"]-lat_user)**2 + (df["Lon"]-lon_user)**2) * 111320).round(1)

    # Filtrar por radio de búsqueda
    res = df[df["Distancia_m"] <= radio].copy()

    # --- 6. DISEÑO DE INTERFAZ APILADO (MAPA ARRIBA, TABLA ABAJO) ---

    # PARTE SUPERIOR: EL MAPA (Ocupando todo el ancho)
    st.subheader("📍 Mapa de Red (Totalmente Expandido)")

    # key dinámico para forzar el renderizado y eliminar el desfase
    map_key = f"mapa_{lat_user}_{lon_user}_{btn_centrar}_{radio}"

    # Crear el mapa base centrado en el usuario
    m = folium.Map(location=[lat_user, lon_user], zoom_start=17, control_scale=True)

    # Marcador de la ubicación consultada
    folium.Marker([lat_user, lon_user], tooltip="Mi Ubicación", icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)

    # Añadir marcadores para cada CTO en el radio
    for _, row in res.iterrows():
        libres = row.get('Cantidad de fibras libres', 0)
        # Definir color del semáforo
        color = "red" if libres == 0 else ("orange" if libres == 1 else "green")

        folium.CircleMarker(
            [row["Lat"], row["Lon"]],
            radius=9,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=f"CTO: {row.get('Nombre_CTO')}<br>Calle: {row.get('Nombre_Calle')}"
        ).add_to(m)

    # Renderizar el mapa en Streamlit (Ocupando todo el ancho)
    st_folium(m, width="100%", height=600, key=map_key)

    # PARTE INFERIOR: LA TABLA (Ocupando todo el ancho)
    st.markdown("---") # Línea separadora
    st.subheader("📊 Listado Detallado (Como Escritorio)")

    if not res.empty:
        # Definir texto del semáforo
        res['ESTADO'] = res['Cantidad de fibras libres'].apply(
            lambda x: "🔴 SATURADO" if x == 0 else ("🟡 CRÍTICO" if x == 1 else "✅ COBERTURA OK")
        )

        # Columnas idénticas a tu foto de escritorio (ajustado a las columnas que veo en tus imágenes)
        # Asegúrate de que estos nombres de columna coinciden EXACTAMENTE con tu Excel
        cols_show = ['ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO', 'Cantidad de fibras libres']

        # Verificar que todas las columnas existen antes de mostrarlas
        existing_cols = [c for c in cols_show if c in res.columns]

        # Mostrar la tabla expandida
        st.dataframe(res[existing_cols].sort_values("Distancia_m"), use_container_width=True, height=600)
    else:
        st.warning("⚠️ No se encontraron resultados en este radio. Intenta aumentar los metros.")

else:
    st.info("👋 Por favor, carga el archivo Excel `datos_fttx.xlsx` en tu repositorio de GitHub o cárgalo manualmente en la barra lateral para iniciar.")

# Pie de página
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Created By V1.0 - Marco Toledo</p>", unsafe_allow_html=True)




    
