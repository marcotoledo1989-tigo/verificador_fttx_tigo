import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import re

# Configuración de página
st.set_page_config(page_title="Tigo FTTX Web", layout="wide")

# Estilo Tigo en la barra lateral
st.sidebar.markdown("# TIGO FTTX")
st.sidebar.markdown("### Verificador de Cobertura")

# 1. CARGA DE ARCHIVO
uploaded_file = st.sidebar.file_uploader("Cargar Excel FTTX", type=["xlsx", "xlsb"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # 2. FILTROS EN BARRA LATERAL
    st.sidebar.header("Parámetros de Búsqueda")
    lat_user = st.sidebar.number_input("Latitud", value=-33.437, format="%.6f")
    lon_user = st.sidebar.number_input("Longitud", value=-70.650, format="%.6f")
    radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 2000, 500)

    # Filtro de Propietario dinámico
    if 'Propietario' in df.columns:
        props = ["Todos"] + list(df['Propietario'].unique())
        prop_sel = st.sidebar.selectbox("Propietario", props)
        if prop_sel != "Todos":
            df = df[df['Propietario'] == prop_sel]

    # 3. LÓGICA DE ANÁLISIS
    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
    df = df.dropna(subset=['Lat', 'Lon'])

    # Cálculo de distancia
    df["Distancia_m"] = (np.sqrt((df["Lat"]-lat_user)**2 + (df["Lon"]-lon_user)**2) * 111320).round(1)
    res = df[df["Distancia_m"] <= radio].copy()

    if not res.empty:
        # Aplicar semáforo (Reglas Marco Toledo)
        def semaforo(libres):
            if libres == 0: return "🔴 SATURADO"
            if libres == 1: return "🟡 CRÍTICO"
            return "✅ COBERTURA OK"

        res['ESTADO'] = res['Cantidad de fibras libres'].apply(semaforo)

        # 4. VISUALIZACIÓN
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📍 Mapa de Cobertura")
            m = folium.Map(location=[lat_user, lon_user], zoom_start=16)
            folium.Marker([lat_user, lon_user], tooltip="Tu ubicación", icon=folium.Icon(color='blue')).add_to(m)

            for _, row in res.iterrows():
                color = "red" if "🔴" in row['ESTADO'] else ("orange" if "🟡" in row['ESTADO'] else "green")
                folium.CircleMarker(
                    [row["Lat"], row["Lon"]], radius=8, color=color, fill=True,
                    popup=f"CTO: {row.get('ID_CTO', 'S/N')}"
                ).add_to(m)
            st_folium(m, width=700, height=500)

        with col2:
            st.subheader("📊 Listado de CTOs")
            st.dataframe(res[['ID_CTO', 'ESTADO', 'Cantidad de fibras libres', 'Distancia_m']].sort_values("Distancia_m"))
    else:
        st.warning("No se encontraron puntos en el radio seleccionado.")

st.sidebar.markdown("---")
st.sidebar.write("Created by Marco Toledo")
