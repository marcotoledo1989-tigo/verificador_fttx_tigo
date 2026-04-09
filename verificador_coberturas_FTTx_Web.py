import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="Tigo Network Tool Ultimate", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { background-color: #0033ab; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
            color: white !important; font-weight: bold;
        }
        .stTitle { color: #0033ab; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Logo Tigo estable
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/Tigo.svg", width=150)
st.sidebar.markdown("<h3 style='color: white; text-align: center; margin-top: 0;'>P2P & FTTx Tool</h3>", unsafe_allow_html=True)

# --- 2. CARGA DE ARCHIVOS ---
st.sidebar.header("📁 Carga de Inventarios")
file_fttx = st.sidebar.file_uploader("1. Base FTTx (CTOs)", type=["xlsx", "xlsb"], key="fttx_up")
file_p2p = st.sidebar.file_uploader("2. Base P2P / Mufas", type=["xlsx", "xlsb"], key="p2p_up")

# --- 3. SELECTOR DE SOLUCIÓN (APAGA/PRENDE CAPAS) ---
st.sidebar.markdown("---")
modo = st.sidebar.radio("🔎 Seleccionar Solución:", ["FTTx (Residencial)", "P2P (Empresas/Mufas)"])

@st.cache_data
def load_data(file):
    if file is not None:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        return df
    return None

# Seleccionar solo el DataFrame necesario para optimizar memoria
df_raw = load_data(file_fttx) if modo == "FTTx (Residencial)" else load_data(file_p2p)

# --- 4. FILTRADO Y PROCESAMIENTO ---
if df_raw is not None:
    st.sidebar.header("🏢 Filtros de Solución")
    df_filtered = df_raw.copy()

    # Filtro de Propietario
    if 'Propietario' in df_filtered.columns:
        props = ["Todos"] + sorted(df_filtered['Propietario'].dropna().unique().tolist())
        prop_sel = st.sidebar.selectbox("Propietario", props)
        if prop_sel != "Todos":
            df_filtered = df_filtered[df_filtered['Propietario'] == prop_sel]

    # Filtros técnicos exclusivos para P2P
    if modo == "P2P (Empresas/Mufas)":
        if 'Tipo_Mufa' in df_filtered.columns:
            tipos = ["Todos"] + sorted(df_filtered['Tipo_Mufa'].dropna().unique().tolist())
            t_sel = st.sidebar.selectbox("Tipo de Mufa", tipos)
            if t_sel != "Todos":
                df_filtered = df_filtered[df_filtered['Tipo_Mufa'] == t_sel]

        if 'Capacidad' in df_filtered.columns:
            caps = ["Todas"] + sorted(df_filtered['Capacidad'].dropna().unique().tolist())
            cap_sel = st.sidebar.selectbox("Capacidad (Fibras)", caps)
            if cap_sel != "Todas":
                df_filtered = df_filtered[df_filtered['Capacidad'] == cap_sel]

    # Parámetros Geográficos
    st.sidebar.header("📍 Ubicación")
    lat_user = st.sidebar.number_input("Latitud", value=-33.437263, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=-70.650033, format="%.6f")
    radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 3000, 1000)

    # Procesamiento final de datos
    df_filtered['Lat'] = pd.to_numeric(df_filtered['Lat'], errors='coerce')
    df_filtered['Lon'] = pd.to_numeric(df_filtered['Lon'], errors='coerce')
    df_filtered = df_filtered.dropna(subset=['Lat', 'Lon'])
    df_filtered["Distancia_m"] = (np.sqrt((df_filtered["Lat"]-lat_user)**2 + (df_filtered["Lon"]-lon_user)**2) * 111320).round(1)
    res = df_filtered[df_filtered["Distancia_m"] <= radio].copy()

    # --- 5. INTERFAZ: MAPA (ARRIBA) ---
    st.title(f" Verificador {modo} Tigo")
    st.subheader(f"📍 Mapa de Red ({len(res)} puntos)")

    m = folium.Map(location=[lat_user, lon_user], zoom_start=17)
    folium.Marker([lat_user, lon_user], tooltip="Consulta", icon=folium.Icon(color='blue', icon='home')).add_to(m)

    for _, row in res.iterrows():
        if modo == "FTTx (Residencial)":
            libres = row.get('Cantidad de fibras libres', 0)
            color = "green" if libres > 1 else ("orange" if libres == 1 else "red")
            nombre = row.get('Nombre_CTO', 'S/N')

            folium.CircleMarker(
                [row["Lat"], row["Lon"]], radius=10, color=color, fill=True, fill_opacity=0.8,
                tooltip=f"CTO: {nombre}", # TOOLTIP DINÁMICO
                popup=f"<b>CTO:</b> {nombre}<br><b>Fibras Libres:</b> {libres}"
            ).add_to(m)
        else:
            nombre = row.get('Nombre_Mufa', row.get('ID_Mufa', 'S/N'))
            kpi = row.get('ANÁLISIS KPI', 'S/D')
            icon_c = 'purple' if kpi == '✅ USAR' else 'cadetblue'

            folium.Marker(
                [row["Lat"], row["Lon"]], icon=folium.Icon(color=icon_c, icon='settings'),
                tooltip=f"Mufa: {nombre}", # TOOLTIP DINÁMICO
                popup=f"<b>Mufa:</b> {nombre}<br><b>KPI:</b> {kpi}<br><b>Función:</b> {row.get('Terminal de fibra óptica.Función', 'S/D')}"
            ).add_to(m)

    st_folium(m, width="100%", height=550, key=f"{modo}_{lat_user}_{len(res)}")

    # --- 6. INTERFAZ: TABLAS (ABAJO) ---
    st.markdown("---")
    if modo == "FTTx (Residencial)":
        st.subheader("📊 Listado Detallado CTOs")
        if not res.empty:
            res['ESTADO'] = res['Cantidad de fibras libres'].apply(lambda x: "🔴 SATURADO" if x == 0 else ("🟡 CRÍTICO" if x == 1 else "✅ OK"))
            cols = ['ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO', 'Cantidad de fibras libres']
            st.dataframe(res[[c for c in cols if c in res.columns]].sort_values("Distancia_m"), use_container_width=True)
    else:
        col1, col2 = st.columns([1.6, 1.4])
        with col1:
            st.subheader("📊 Detalle de Mufas")
            cols_p2p = ['ID_Mufa', 'Distancia_m', 'Propietario', 'Nombre_Mufa', 'Terminal de fibra óptica.Función', 'Terminal de fibra óptica.Instalación']
            st.dataframe(res[[c for c in cols_p2p if c in res.columns]].sort_values("Distancia_m"), use_container_width=True)
        with col2:
            st.subheader("📊 Resumen de Fibra (KPI)")
            cols_kpi = ['ID_Mufa', 'ANÁLISIS KPI', 'Tipo_Mufa', 'Ocupados', 'Fibra']
            st.dataframe(res[[c for c in cols_kpi if c in res.columns]].sort_values("ID_Mufa"), use_container_width=True)
else:
    st.info("👋 Marco, selecciona una solución y sube el archivo correspondiente para activar la herramienta.")

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Created By Version 1.1 - Marco Toledo</p>", unsafe_allow_html=True)







    
