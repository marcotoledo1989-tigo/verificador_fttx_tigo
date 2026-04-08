import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Tigo FTTX Web", layout="wide")

st.title("🚀 Verificador de Cobertura FTTX")

# Sidebar para cargar y filtrar
uploaded_file = st.sidebar.file_uploader("1. Cargar Excel FTTX", type=["xlsx", "xlsb"])

# Coordenadas de entrada (Usar PUNTO para decimales)
st.sidebar.header("2. Ubicación de Consulta")
lat_user = st.sidebar.number_input("Latitud", value=-33.437263, format="%.6f")
lon_user = st.sidebar.number_input("Longitud", value=-70.650033, format="%.6f")
radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 2000, 500)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()

        # Limpieza y conversión
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
        df = df.dropna(subset=['Lat', 'Lon'])

        # Cálculo de distancia
        df["Distancia_m"] = (np.sqrt((df["Lat"]-lat_user)**2 + (df["Lon"]-lon_user)**2) * 111320).round(1)
        res = df[df["Distancia_m"] <= radio].copy()

        # Lógica de Semáforo
        def definir_estado(fila):
            libres = fila.get('Cantidad de fibras libres', 0)
            if libres == 0: return "🔴 SATURADO"
            if libres == 1: return "🟡 CRÍTICO"
            return "✅ COBERTURA OK"

        if not res.empty:
            res['ESTADO'] = res.apply(definir_estado, axis=1)

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("📍 Mapa de Red")
                # CLAVE: location= usa las variables lat_user y lon_user para moverse
                m = folium.Map(location=[lat_user, lon_user], zoom_start=16)
                folium.Marker([lat_user, lon_user], tooltip="Punto de Consulta", icon=folium.Icon(color='blue')).add_to(m)

                for _, row in res.iterrows():
                    color_punto = "red" if "🔴" in row['ESTADO'] else ("orange" if "🟡" in row['ESTADO'] else "green")
                    folium.CircleMarker(
                        [row["Lat"], row["Lon"]],
                        radius=8,
                        color=color_punto,
                        fill=True,
                        popup=f"CTO: {row.get('ID_CTO', 'S/N')}"
                    ).add_to(m)

                # Esto asegura que el mapa se redibuje en la nueva posición
                st_folium(m, width=800, height=500, key=f"map_{lat_user}_{lon_user}")

            with col2:
                st.subheader("📊 Detalle de CTOs")
                st.dataframe(res[['ID_CTO', 'ESTADO', 'Distancia_m']].sort_values("Distancia_m"))
        else:
            st.warning("No hay CTOs en este radio. Prueba aumentando el radio de búsqueda.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Carga el archivo Excel para ver el mapa.")
    
