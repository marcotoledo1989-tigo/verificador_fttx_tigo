import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="Tigo Network Tool Pro", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #0033ab; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
            color: white !important; font-weight: bold;
        }
        .stTitle { color: #0033ab; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)

# --- 2. CARGA DE ARCHIVOS ---
st.sidebar.header("📁 Carga de Inventarios")
file_fttx = st.sidebar.file_uploader("1. Base FTTx", type=["xlsx", "xlsb"], key="fttx_up")
file_p2p = st.sidebar.file_uploader("2. Base P2P / Mufas", type=["xlsx", "xlsb"], key="p2p_up")

# --- 3. SELECTOR DE SOLUCIÓN (ESTO APAGA/PRENDE LAS CAPAS) ---
st.sidebar.markdown("---")
modo = st.sidebar.radio("🔎 Seleccionar Solución:", ["FTTx (Residencial)", "P2P (Empresas/Mufas)"])

@st.cache_data
def load_data(file):
    if file is not None:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        return df
    return None

# Carga solo el DataFrame necesario según el modo seleccionado
df_raw = None
if modo == "FTTx (Residencial)":
    df_raw = load_data(file_fttx)
else:
    df_raw = load_data(file_p2p)

# --- 4. FILTRADO DINÁMICO POR PROPIETARIO Y ATRIBUTOS ---
if df_raw is not None:
    st.sidebar.header("🏢 Filtros de Solución")

    df_filtered = df_raw.copy()

    # Filtro de Propietario (Aparece en ambos modos si la columna existe)
    if 'Propietario' in df_filtered.columns:
        props = ["Todos"] + sorted(df_filtered['Propietario'].dropna().unique().tolist())
        prop_sel = st.sidebar.selectbox("Propietario", props)
        if prop_sel != "Todos":
            df_filtered = df_filtered[df_filtered['Propietario'] == prop_sel]

    # Filtros extra solo si estamos en P2P
    if modo == "P2P (Empresas/Mufas)":
        if 'Tipo_Mufa' in df_filtered.columns:
            tipos = ["Todos"] + sorted(df_filtered['Tipo_Mufa'].dropna().unique().tolist())
            t_sel = st.sidebar.selectbox("Tipo de Mufa", tipos)
            if t_sel != "Todos":
                df_filtered = df_filtered[df_filtered['Tipo_Mufa'] == t_sel]

    # --- 5. PARÁMETROS GEOGRÁFICOS ---
    st.sidebar.header("📍 Ubicación")
    lat_user = st.sidebar.number_input("Latitud", value=-33.574263, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=-70.559033, format="%.6f")
    radio = st.sidebar.slider("Radio de búsqueda (m)", 50, 500, 5000)

    # Cálculo de distancia y filtrado final
    df_filtered['Lat'] = pd.to_numeric(df_filtered['Lat'], errors='coerce')
    df_filtered['Lon'] = pd.to_numeric(df_filtered['Lon'], errors='coerce')
    df_filtered = df_filtered.dropna(subset=['Lat', 'Lon'])
    df_filtered["Distancia_m"] = (np.sqrt((df_filtered["Lat"]-lat_user)**2 + (df_filtered["Lon"]-lon_user)**2) * 111320).round(1)
    res = df_filtered[df_filtered["Distancia_m"] <= radio].copy()

    # --- 6. INTERFAZ: MAPA Y TABLA ---
    st.title(f"🚀 Verificador {modo} Tigo")

    # MAPA
    st.subheader("📍 Mapa de Red Filtrado")
    m = folium.Map(location=[lat_user, lon_user], zoom_start=17)
    folium.Marker([lat_user, lon_user], icon=folium.Icon(color='blue', icon='home')).add_to(m)

    for _, row in res.iterrows():
        if modo == "FTTx (Residencial)":
            libres = row.get('Cantidad de fibras libres', 0)
            color = "red" if libres == 0 else ("orange" if libres == 1 else "green")
            folium.CircleMarker([row["Lat"], row["Lon"]], radius=9, color=color, fill=True).add_to(m)
        else:
            folium.Marker([row["Lat"], row["Lon"]], icon=folium.Icon(color='purple', icon='wrench')).add_to(m)

    st_folium(m, width="100%", height=500, key=f"{modo}_{lat_user}_{len(res)}")

    # TABLA
    st.markdown("---")
    st.subheader(f"📊 Listado Detallado de {modo}")
    if not res.empty:
        # Definición de columnas según el modo (estilo escritorio)
        if modo == "FTTx (Residencial)":
            res['ESTADO'] = res['Cantidad de fibras libres'].apply(lambda x: "🔴 SAT" if x == 0 else ("🟡 CRI" if x == 1 else "✅ OK"))
            cols = ['ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO']
        else:
            cols = ['ID_MUFA', 'Nombre_Calle', 'Tipo_Mufa', 'Capacidad', 'Distancia_m']

        cols_final = [c for c in cols if c in res.columns]
        st.dataframe(res[cols_final].sort_values("Distancia_m"), use_container_width=True)
    else:
        st.warning("No hay elementos para esta solución en el radio seleccionado.")

else:
    st.info("👋 Marco, selecciona una solución y sube el archivo correspondiente para ver la capa en el mapa.")

# Pie de página
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Created By V1.0 - Marco Toledo</p>", unsafe_allow_html=True)







    
