import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURACIÓN Y PERSISTENCIA ---
st.set_page_config(page_title="Tigo Network Tool Pro", layout="wide")

if 'lat' not in st.session_state:
    st.session_state.lat = -33.4372
if 'lon' not in st.session_state:
    st.session_state.lon = -70.6506

st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #0033ab; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label { color: white !important; font-weight: bold; }
        .stTitle { color: #0033ab; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)

# --- 2. BÚSQUEDA DE UBICACIÓN ---
st.sidebar.header("🔍 Ubicación de Consulta")
with st.sidebar.expander("Búsqueda por Dirección", expanded=True):
    calle = st.text_input("Calle")
    altura = st.text_input("Altura")
    comuna = st.text_input("Comuna", value="Santiago")
    if st.button("Ir a la ubicación"):
        geolocator = Nominatim(user_agent="tigo_tool_chile")
        location = geolocator.geocode(f"{calle} {altura}, {comuna}, Chile")
        if location:
            st.session_state.lat = location.latitude
            st.session_state.lon = location.longitude
            st.sidebar.success("Ubicación fijada")
        else:
            st.sidebar.error("No encontrada")

radio = st.sidebar.slider("Radio de búsqueda (m)", 50, 5000, 1000)

# --- 3. CARGA Y UNIFICACIÓN (CTO Y MUFAS) ---
st.sidebar.header("📁 Inventarios")
file_fttx = st.sidebar.file_uploader("Base FTTx", type=["xlsx", "xlsb"])
file_p2p = st.sidebar.file_uploader("Base P2P", type=["xlsx", "xlsb"])
modo = st.sidebar.radio("Solución:", ["FTTx (Residencial)", "P2P (Empresas/Mufas)"])

@st.cache_data
def load_and_clean(file, tipo):
    if file is None: return None
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()

    # Unificación por ID para ambos casos (CTO y Mufas)
    id_col = 'ID_CTO' if tipo == "FTTx" else 'ID_Mufa'
    if id_col in df.columns:
        agg_rules = {col: 'first' for col in df.columns if col != id_col}
        # Concatenar información variable si existe duplicado por ID
        for special_col in ['Fibra', 'Cable_Origen', 'Comentarios']:
            if special_col in df.columns:
                agg_rules[special_col] = lambda x: ', '.join(x.astype(str).unique())
        df = df.groupby(id_col).agg(agg_rules).reset_index()

    if tipo == "FTTx":
        df['Cantidad de fibras libres'] = pd.to_numeric(df['Cantidad de fibras libres'], errors='coerce')

    return df

df_raw = load_and_clean(file_fttx, "FTTx") if modo == "FTTx (Residencial)" else load_and_clean(file_p2p, "P2P")

if df_raw is not None:
    df_raw['Lat'] = pd.to_numeric(df_raw['Lat'], errors='coerce')
    df_raw['Lon'] = pd.to_numeric(df_raw['Lon'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Lat', 'Lon'])
    df_raw["Distancia_m"] = (np.sqrt((df_raw["Lat"]-st.session_state.lat)**2 + (df_raw["Lon"]-st.session_state.lon)**2) * 111320).round(1)
    res = df_raw[df_raw["Distancia_m"] <= radio].copy()

    # --- 4. MAPA ---
    st.title(f" Verificador {modo} Tigo")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
    folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

    for _, row in res.iterrows():
        if modo == "FTTx (Residencial)":
            # Identificación CTO en Mapa
            id_cto = row.get('ID_CTO', 'S/I')
            nombre_cto = row.get('Nombre_CTO', 'S/N')
            etiqueta_cto = f"ID: {id_cto} | CTO: {nombre_cto}"

            val = row.get('Cantidad de fibras libres')
            color = "gray" if pd.isna(val) else ("red" if val == 0 else ("orange" if val == 1 else "green"))

            folium.CircleMarker(
                [row["Lat"], row["Lon"]], radius=11, color=color, fill=True,
                tooltip=etiqueta_cto,
                popup=f"<b>{etiqueta_cto}</b><br>Libres: {val if not pd.isna(val) else 'S/I'}"
            ).add_to(m)
        else:
            # Identificación Mufa en Mapa
            id_mufa = row.get('ID_Mufa', 'S/I')
            nombre_mufa = row.get('Nombre_Mufa', 'S/N')
            etiqueta_mufa = f"ID: {id_mufa} | Mufa: {nombre_mufa}"

            kpi = str(row.get('ANÁLISIS', ''))
            color_mufa = "green" if "USAR" in kpi else "cadetblue"

            folium.Marker(
                [row["Lat"], row["Lon"]], icon=folium.Icon(color=color_mufa, icon='share-alt'),
                tooltip=etiqueta_mufa,
                popup=f"<b>{etiqueta_mufa}</b>"
            ).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_fixed_{st.session_state.lat}")

    # --- 5. TABLAS DETALLE ---
    st.markdown("---")
    if modo == "FTTx (Residencial)":
        st.subheader(f"📊 Detalle CTOs Encontradas ({len(res)})")
        res['ESTADO'] = res['Cantidad de fibras libres'].apply(lambda x: "⚪ SIN INFO" if pd.isna(x) else ("🔴 SATURADO" if x == 0 else ("🟡 CRÍTICO" if x == 1 else "✅ OK")))
        # ID al inicio para destacar la selección del mapa
        cols_cto = ['ID_CTO', 'ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO', 'Cantidad de fibras libres']
        st.dataframe(res[[c for c in cols_cto if c in res.columns]].sort_values("Distancia_m"), use_container_width=True)
    else:
        st.subheader(f"📊 Detalle Mufas Encontradas ({len(res)})")
        col1, col2 = st.columns([1.6, 1.4])
        with col1:
            cols_tec = ['ID_Mufa', 'Propietario', 'Nombre_OC', 'Distancia_m', 'Nombre_Mufa', 'Terminal de fibra óptica.Instalación', 'Cable_Origen']
            st.dataframe(res[[c for c in cols_tec if c in res.columns]].sort_values("Distancia_m"), use_container_width=True)
        with col2:
            cols_kpi = ['ID_Mufa', 'ANÁLISIS', 'Ocupados', 'Tipo_Mufa', 'Fibra', 'Consulta de Conexiones en TFO.Cuenta de la origen']
            st.dataframe(res[[c for c in cols_kpi if c in res.columns]], use_container_width=True)

# Pie de página
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Created By V1.0 - Marco Toledo</p>", unsafe_allow_html=True)


    
