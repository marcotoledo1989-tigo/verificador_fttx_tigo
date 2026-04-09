import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

# 1. CONFIGURACIÓN E IDENTIDAD VISUAL
st.set_page_config(page_title="Tigo FTTX - Versión Final", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #0033ab; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
            color: white !important; font-weight: bold;
        }
        .stTitle { color: #0033ab; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/4/40/Tigo_logo.svg", width=150)
st.sidebar.markdown("<h3 style='color: white; text-align: center;'>Consultor FTTX</h3>", unsafe_allow_html=True)

# --- LÓGICA DE CARGA DE DATOS ---
@st.cache_data # Optimiza la velocidad de carga
def load_data(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()
    return df

file_name = "datos_fttx.xlsx"
df_raw = None

if os.path.exists(file_name):
    df_raw = load_data(file_name)
    st.sidebar.success("✅ Base de datos cargada")
else:
    uploaded = st.sidebar.file_uploader("Cargar Excel FTTX", type=["xlsx", "xlsb"])
    if uploaded:
        df_raw = load_data(uploaded)

if df_raw is not None:
    # 2. PANEL DE CONTROL (SIDEBAR)
    st.sidebar.header("📍 Parámetros")
    lat_user = st.sidebar.number_input("Latitud", value=-33.4372, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=-70.6500, format="%.6f")
    radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 2000, 500)

    # Botón de Centrado (Solución al problema de 'Salto')
    centrar = st.sidebar.button("🎯 CENTRAR MAPA")

    # Filtro de Propietario (Siempre Visible)
    st.sidebar.header("🏢 Filtros")
    if 'Propietario' in df_raw.columns:
        props = ["Todos"] + sorted(df_raw['Propietario'].dropna().unique().tolist())
        prop_sel = st.sidebar.selectbox("Propietario", props)

    # 3. PROCESAMIENTO
    df = df_raw.copy()
    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
    df = df.dropna(subset=['Lat', 'Lon'])

    if 'Propietario' in df.columns and prop_sel != "Todos":
        df = df[df['Propietario'] == prop_sel]

    df["Distancia_m"] = (np.sqrt((df["Lat"]-lat_user)**2 + (df["Lon"]-lon_user)**2) * 111320).round(1)
    res = df[df["Distancia_m"] <= radio].copy()

    # 4. INTERFAZ PRINCIPAL
    st.title("🚀 Verificador FTTX Tigo")

    col1, col2 = st.columns([1.8, 1.2])

    with col1:
        st.subheader("📍 Mapa de Cobertura")
        # El mapa usa un 'key' que cambia al presionar el botón de centrar
        map_key = f"map_{lat_user}_{lon_user}_{centrar}"
        m = folium.Map(location=[lat_user, lon_user], zoom_start=17)
        folium.Marker([lat_user, lon_user], icon=folium.Icon(color='blue', icon='home')).add_to(m)

        for _, row in res.iterrows():
            libres = row.get('Cantidad de fibras libres', 0)
            color = "red" if libres == 0 else ("orange" if libres == 1 else "green")
            folium.CircleMarker(
                [row["Lat"], row["Lon"]], radius=9, color=color, fill=True,
                popup=f"CTO: {row.get('ID_CTO')}<br>Calle: {row.get('Nombre_Calle')}"
            ).add_to(m)

        st_folium(m, width=750, height=550, key=map_key)

    with col2:
        st.subheader("📊 Listado Detallado")
        if not res.empty:
            res['ESTADO'] = res['Cantidad de fibras libres'].apply(
                lambda x: "🔴 SAT" if x == 0 else ("🟡 CRI" if x == 1 else "✅ OK")
            )
            # Columnas completas como en escritorio
            cols_show = ['ID_CTO', 'Nombre_Calle', 'Propietario', 'ESTADO', 'Distancia_m']
            st.dataframe(res[cols_show].sort_values("Distancia_m"), height=550)
        else:
            st.warning("Sin resultados en este radio.")

else:
    st.warning("⚠️ Esperando archivo de datos...")

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Version Final 1.0 - Marco Toledo</p>", unsafe_allow_html=True)



    
