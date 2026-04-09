import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

# 1. CONFIGURACIÓN Y ESTILO TIGO
st.set_page_config(page_title="Tigo FTTX - Consultor", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #0033ab; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
            color: white !important; font-weight: bold;
        }
        .stTitle { color: #0033ab; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Logo Tigo (Enlace directo optimizado)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/4/40/Tigo_logo.svg", width=150)
st.sidebar.markdown("<h3 style='color: white; text-align: center;'>Consultor FTTX</h3>", unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data
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
    # 2. PANEL DE CONTROL
    st.sidebar.header("📍 Parámetros")
    # Usamos st.session_state para forzar la actualización de coordenadas
    lat_user = st.sidebar.number_input("Latitud", value=-33.574263, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=-70.559033, format="%.6f")
    radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 2000, 500)

    # Botón para centrar mapa y corregir desfase
    btn_centrar = st.sidebar.button("🎯 ACTUALIZAR UBICACIÓN")

    st.sidebar.header("🏢 Filtros")
    props = ["Todos"] + sorted(df_raw['Propietario'].dropna().unique().tolist())
    prop_sel = st.sidebar.selectbox("Propietario", props)

    # 3. PROCESAMIENTO
    df = df_raw.copy()
    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
    df = df.dropna(subset=['Lat', 'Lon'])

    if prop_sel != "Todos":
        df = df[df['Propietario'] == prop_sel]

    # Cálculo exacto de distancia
    df["Distancia_m"] = (np.sqrt((df["Lat"]-lat_user)**2 + (df["Lon"]-lon_user)**2) * 111320).round(1)
    res = df[df["Distancia_m"] <= radio].copy()

    # 4. INTERFAZ PRINCIPAL
    st.title("🚀 Verificador FTTX Tigo")

    col1, col2 = st.columns([1.6, 1.4])

    with col1:
        st.subheader("📍 Mapa de Red")
        # El key dinámico soluciona el desfase al forzar el renderizado
        map_key = f"map_{lat_user}_{lon_user}_{btn_centrar}_{radio}"

        m = folium.Map(location=[lat_user, lon_user], zoom_start=17, control_scale=True)
        # Marcador de usuario
        folium.Marker([lat_user, lon_user], tooltip="Mi Ubicación", icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)

        for _, row in res.iterrows():
            libres = row.get('Cantidad de fibras libres', 0)
            color = "red" if libres == 0 else ("orange" if libres == 1 else "green")
            folium.CircleMarker(
                [row["Lat"], row["Lon"]],
                radius=9, color=color, fill=True, fill_opacity=0.7,
                popup=f"CTO: {row.get('Nombre_CTO')}<br>Calle: {row.get('Nombre_Calle')}"
            ).add_to(m)

        st_folium(m, width=700, height=550, key=map_key)

    with col2:
        st.subheader("📊 Listado Detallado (Como Escritorio)")
        if not res.empty:
            res['ESTADO'] = res['Cantidad de fibras libres'].apply(
                lambda x: "🔴 SATURADO" if x == 0 else ("🟡 CRÍTICO" if x == 1 else "✅ COBERTURA OK")
            )
            # Columnas idénticas a tu foto de escritorio
            cols_show = ['ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO', 'Cantidad de fibras libres']
            st.dataframe(res[cols_show].sort_values("Distancia_m"), height=550)
        else:
            st.warning("No hay resultados en este radio.")

else:
    st.info("👋 Por favor, carga el archivo Excel para iniciar.")

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Version Gold 1.1 - Marco Toledo</p>", unsafe_allow_html=True)





    
