import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN DE PÁGINA E IDENTIDAD
st.set_page_config(page_title="Tigo FTTX - Verificador", layout="wide")

# Estilos CSS para replicar la versión escritorio
st.markdown("""
    <style>
        /* Fondo de la barra lateral (Azul Tigo) */
        [data-testid="stSidebar"] {
            background-color: #0033ab;
            color: white;
        }
        /* Color de los textos en la barra lateral */
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
            color: white !important;
            font-weight: bold;
        }
        /* Estilo para los botones */
        .stButton>button {
            background-color: #00d0ff;
            color: #0033ab;
            border-radius: 5px;
            font-weight: bold;
            border: none;
        }
    </style>
    """, unsafe_allow_html=True)

# Logo de Tigo en la parte superior de la barra lateral
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Tigo_logo.svg/1200px-Tigo_logo.svg.png", width=150)
st.sidebar.markdown("---")

st.title("🚀 Verificador de Cobertura FTTX")

# 2. CARGA DE ARCHIVO
uploaded_file = st.sidebar.file_uploader("1. CARGAR EXCEL FTTX", type=["xlsx", "xlsb"])

# 3. PARÁMETROS DE BÚSQUEDA
st.sidebar.header("2. UBICACIÓN DE CONSULTA")
lat_user = st.sidebar.number_input("Latitud", value=-33.437263, format="%.6f")
lon_user = st.sidebar.number_input("Longitud", value=-70.650033, format="%.6f")
radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 2000, 500)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()

        # Limpieza y Conversión
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
        df = df.dropna(subset=['Lat', 'Lon'])

        # Cálculo de Distancia
        df["Distancia_m"] = (np.sqrt((df["Lat"]-lat_user)**2 + (df["Lon"]-lon_user)**2) * 111320).round(1)
        res = df[df["Distancia_m"] <= radio].copy()

        if not res.empty:
            # Lógica de Semáforo (Marco Toledo)
            res['ESTADO'] = res['Cantidad de fibras libres'].apply(
                lambda x: "🔴 SATURADO" if x == 0 else ("🟡 CRÍTICO" if x == 1 else "✅ COBERTURA OK")
            )

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("📍 Mapa de Red FTTX")
                # El mapa salta a la coordenada ingresada gracias a la 'key'
                m = folium.Map(location=[lat_user, lon_user], zoom_start=17)
                folium.Marker([lat_user, lon_user], tooltip="Punto de Consulta", icon=folium.Icon(color='blue', icon='home')).add_to(m)

                for _, row in res.iterrows():
                    color_punto = "red" if "🔴" in row['ESTADO'] else ("orange" if "🟡" in row['ESTADO'] else "green")
                    folium.CircleMarker(
                        [row["Lat"], row["Lon"]], radius=9, color=color_punto, fill=True,
                        popup=f"CTO: {row.get('ID_CTO')}<br>Libres: {row.get('Cantidad de fibras libres')}"
                    ).add_to(m)

                st_folium(m, width=700, height=500, key=f"map_{lat_user}_{lon_user}")

            with col2:
                st.subheader("📊 Listado de CTOs")
                # Mostrar columnas clave
                st.dataframe(res[['ID_CTO', 'ESTADO', 'Distancia_m']].sort_values("Distancia_m"), height=500)
        else:
            st.warning("No se encontraron puntos en este radio.")

    except Exception as e:
        st.error(f"Error en el proceso: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: right; color: #80a3ff;'>Created by Marco Toledo</p>", unsafe_allow_html=True)

    
