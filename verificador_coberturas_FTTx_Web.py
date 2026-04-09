import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURACIÓN Y PERSISTENCIA ---
st.set_page_config(page_title="Tigo Network Tool Pro", layout="wide")

# Mantener la ubicación fija en la sesión para que no regrese al centro
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

# --- 2. BÚSQUEDA DE DIRECCIÓN ---
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
           st.success("Ubicación fijada")
       else:
           st.error("No encontrada")

with st.sidebar.expander("Coordenadas Manuales"):
   st.session_state.lat = st.number_input("Latitud", value=st.session_state.lat, format="%.6f")
   st.session_state.lon = st.number_input("Longitud", value=st.session_state.lon, format="%.6f")

radio = st.sidebar.slider("Radio de búsqueda (m)", 100, 3000, 1000)

# --- 3. CARGA Y UNIFICACIÓN (MUFAS FOTO 9) ---
st.sidebar.header("📁 Inventarios")
file_fttx = st.sidebar.file_uploader("Base FTTx", type=["xlsx", "xlsb"])
file_p2p = st.sidebar.file_uploader("Base P2P", type=["xlsx", "xlsb"])
modo = st.sidebar.radio("Solución:", ["FTTx (Residencial)", "P2P (Empresas/Mufas)"])

@st.cache_data
def load_and_clean(file, tipo):
   if file is None: return None
   df = pd.read_excel(file)
   df.columns = df.columns.str.strip()

   if tipo == "P2P":
       # Unificamos por ID_Mufa para que no se repitan filas 
       # Concatenamos fibras y cables si son distintos
       agg_rules = {col: 'first' for col in df.columns if col != 'ID_Mufa'}
       if 'Fibra' in df.columns: agg_rules['Fibra'] = lambda x: ', '.join(x.astype(str).unique())
       if 'Cable_Origen' in df.columns: agg_rules['Cable_Origen'] = lambda x: ', '.join(x.astype(str).unique())
       df = df.groupby('ID_Mufa').agg(agg_rules).reset_index()
   return df

df_raw = load_and_clean(file_fttx, "FTTx") if modo == "FTTx (Residencial)" else load_and_clean(file_p2p, "P2P")

if df_raw is not None:
   # Filtrado Geográfico
   df_raw['Lat'] = pd.to_numeric(df_raw['Lat'], errors='coerce')
   df_raw['Lon'] = pd.to_numeric(df_raw['Lon'], errors='coerce')
   df_raw = df_raw.dropna(subset=['Lat', 'Lon'])
   df_raw["Distancia_m"] = (np.sqrt((df_raw["Lat"]-st.session_state.lat)**2 + (df_raw["Lon"]-st.session_state.lon)**2) * 111320).round(1)
   res = df_raw[df_raw["Distancia_m"] <= radio].copy()

   # --- 4. MAPA ---
   st.title(f" Verificador {modo} Tigo")
   m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=18)
   folium.Marker([st.session_state.lat, st.session_state.lon], tooltip="Consulta", icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

   for _, row in res.iterrows():
       if modo == "FTTx (Residencial)":
           libres = pd.to_numeric(row.get('Cantidad de fibras libres'), errors='coerce')
           color = "gray" if pd.isna(libres) else ("red" if libres == 0 else ("orange" if libres == 1 else "green"))
           folium.CircleMarker([row["Lat"], row["Lon"]], radius=10, color=color, fill=True).add_to(m)
       else:
           kpi = str(row.get('ANÁLISIS', ''))
           color_mufa = "green" if "USAR" in kpi else "cadetblue"
           folium.Marker([row["Lat"], row["Lon"]], icon=folium.Icon(color=color_mufa, icon='share-alt')).add_to(m)

   st_folium(m, width="100%", height=500, key=f"map_{st.session_state.lat}")

   # --- 5. TABLAS (FOTOS 4, 5 Y 7) ---
   st.markdown("---")
   if modo == "FTTx (Residencial)":
       st.subheader(f"📊 Detalle CTOs ({len(res)} puntos)")
       res['ESTADO'] = res['Cantidad de fibras libres'].apply(lambda x: "⚪ SIN INFO" if pd.isna(x) else ("🔴 SATURADO" if x == 0 else ("🟡 CRÍTICO" if x == 1 else "✅ OK")))
       st.dataframe(res[['ESTADO', 'Propietario', 'Distancia_m', 'Nombre_Calle', 'Nombre_CTO', 'Cantidad de fibras libres']], use_container_width=True)
   else:
       st.subheader(f"📊 Detalle Mufas Unificadas ({len(res)})")
       col1, col2 = st.columns([1.5, 1])
       with col1: # Columnas según Foto 5 y 9
           cols_tec = ['ID_Mufa', 'Distancia_m', 'Propietario', 'Nombre_Mufa', 'Terminal de fibra óptica.Función', 'Terminal de fibra óptica.Instalación', 'Terminal de fibra óptica.Situación', 'Cable_Origen']
           st.dataframe(res[[c for c in cols_tec if c in res.columns]], use_container_width=True)
       with col2: # Columnas según Foto 4 y 7
           cols_kpi = ['ID_Mufa', 'ANÁLISIS KPI', 'Ocupados', 'Tipo_Mufa', 'Fibra', 'Consulta de Conexiones en TFO.Cuenta de la origen']
           st.dataframe(res[[c for c in cols_kpi if c in res.columns]], use_container_width=True)

else:
   st.info("Sube los archivos para activar el mapa y el análisis.")

# Pie de página
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='text-align: center; color: white;'>Created By V1.0 - Marco Toledo</p>", unsafe_allow_html=True)



    
