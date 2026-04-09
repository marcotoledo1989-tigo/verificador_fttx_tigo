import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import streamlit_authenticator as stauth
from geopy.geocoders import Nominatim # Para búsqueda por dirección

# --- 1. CONFIGURACIÓN Y SEGURIDAD ---
st.set_page_config(page_title="Tigo Network Tool Pro", layout="wide")

# (Opcional: Aquí puedes reinsertar el bloque de autenticator si lo requieres)

st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #0033ab; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label { color: white !important; font-weight: bold; }
        .stTitle { color: #0033ab; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)

# --- 2. ENTRADA DE DATOS (BÚSQUEDA) ---
st.sidebar.header("🔍 Entrada de Ubicación")
metodo_busqueda = st.sidebar.radio("Método:", ["Dirección Manual", "Coordenadas"])

lat_user, lon_user = -33.4372, -70.6506 # Default Santiago

if metodo_busqueda == "Dirección Manual":
    calle = st.sidebar.text_input("Nombre Calle")
    altura = st.sidebar.text_input("Altura (Número)")
    comuna = st.sidebar.text_input("Comuna", value="Santiago")
    if st.sidebar.button("Buscar Dirección"):
        try:
            geolocator = Nominatim(user_agent="tigo_tool")
            location = geolocator.geocode(f"{calle} {altura}, {comuna}, Chile")
            if location:
                lat_user, lon_user = location.latitude, location.longitude
                st.sidebar.success("Ubicación encontrada")
            else:
                st.sidebar.error("Dirección no hallada")
        except:
            st.sidebar.error("Error en servicio de mapas")
else:
    lat_user = st.sidebar.number_input("Latitud", value=lat_user, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=lon_user, format="%.6f")

radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 3000, 1000)

# --- 3. CARGA Y PROCESAMIENTO ---
st.sidebar.header("📁 Inventarios")
file_fttx = st.sidebar.file_uploader("Base FTTx (CTOs)", type=["xlsx", "xlsb"])
file_p2p = st.sidebar.file_uploader("Base P2P (Mufas)", type=["xlsx", "xlsb"])

modo = st.sidebar.selectbox("Consultar:", ["FTTx (Residencial)", "P2P (Empresas/Mufas)"])

@st.cache_data
def process_data(file, tipo):
    if file is None: return None
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()

    if tipo == "FTTx":
        # Evitar completar vacíos con 0 para no saturar erróneamente
        df['Cantidad de fibras libres'] = pd.to_numeric(df['Cantidad de fibras libres'], errors='coerce')

    elif tipo == "P2P":
        # UNIFICACIÓN DE MUFAS POR ID
        # Agrupamos por ID_Mufa y unimos los valores de fibras/cables si hay duplicados
        df = df.groupby('ID_Mufa').agg(lambda x: x.iloc[0] if x.nunique() <= 1 else ', '.join(x.astype(str))).reset_index()

    return df

df_raw = process_data(file_fttx, "FTTx") if modo == "FTTx (Residencial)" else process_data(file_p2p, "P2P")

if df_raw is not None:
    # Filtrado Geográfico
    df_raw['Lat'] = pd.to_numeric(df_raw['Lat'], errors='coerce')
    df_raw['Lon'] = pd.to_numeric(df_raw['Lon'], errors='coerce')
    df_raw = df_raw.dropna(subset=['Lat', 'Lon'])
    df_raw["Distancia_m"] = (np.sqrt((df_raw["Lat"]-lat_user)**2 + (df_raw["Lon"]-lon_user)**2) * 111320).round(1)
    res = df_raw[df_raw["Distancia_m"] <= radio].copy()

    # --- 4. MAPA ---
    st.title(f" Verificador {modo}")
    m = folium.Map(location=[lat_user, lon_user], zoom_start=17)
    folium.Marker([lat_user, lon_user], icon=folium.Icon(color='blue', icon='home')).add_to(m)

    for _, row in res.iterrows():
        if modo == "FTTx (Residencial)":
            val = row['Cantidad de fibras libres']
            # Semáforo: Gris para vacíos, Rojo 0, Naranja 1, Verde >1
            color = "gray" if pd.isna(val) else ("red" if val == 0 else ("orange" if val == 1 else "green"))
            folium.CircleMarker([row["Lat"], row["Lon"]], radius=9, color=color, fill=True).add_to(m)
        else:
            kpi = row.get('ANÁLISIS', '')
            icon_c = 'green' if 'USAR' in str(kpi) else 'red'
            folium.Marker([row["Lat"], row["Lon"]], icon=folium.Icon(color=icon_c, icon='settings')).add_to(m)

    st_folium(m, width="100%", height=500)

    # --- 5. DETALLE ESTILO ESCRITORIO ---
    st.markdown("---")
    if modo == "FTTx (Residencial)":
        st.subheader(f"📊 FTTX: {len(res)} puntos analizados")
        def set_semaforo(x):
            if pd.isna(x): return "⚪ SIN INFO"
            return "🔴 SAT" if x == 0 else ("🟡 CRI" if x == 1 else "✅ OK")
        res['ESTADO'] = res['Cantidad de fibras libres'].apply(set_semaforo)
        st.dataframe(res[['ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO', 'Cantidad de fibras libres']], use_container_width=True)
    else:
        st.subheader(f"📊 Mostrando {len(res)} mufas UNIFICADAS")
        col1, col2 = st.columns(2)
        with col1: # Detalle técnico (Foto 2)
            cols_1 = ['ID_Mufa', 'Distancia_m', 'Nombre_Mufa', 'Terminal de fibra óptica.Función', 'Terminal de fibra óptica.Instalación', 'Terminal de fibra óptica.Situación']
            st.dataframe(res[[c for c in cols_1 if c in res.columns]], use_container_width=True)
        with col2: # Análisis KPI (Foto 1)
            cols_2 = ['ID_Mufa', 'ANÁLISIS KPI', 'Ocupados', 'Tipo_Mufa', 'Fibra']
            st.dataframe(res[[c for c in cols_2 if c in res.columns]], use_container_width=True)


# Pie de página
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Created By V1.0 - Marco Toledo</p>", unsafe_allow_html=True)








    
