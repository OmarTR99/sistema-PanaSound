import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px  # ¡NUEVO! La herramienta para gráficos profesionales

# Configuración de la página
st.set_page_config(page_title="Panasound Store", page_icon="logo.png", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestaña):
    try:
        return conn.read(worksheet=pestaña, ttl=0).dropna(how="all")
    except:
        return pd.DataFrame()

df_inv = cargar_datos("Inventario")
df_ventas = cargar_datos("Ventas")
df_historial = cargar_datos("Historial")

def guardar_historial(tipo, modelo, cantidad, monto, ganancia=0):
    try:
        hora_local = datetime.utcnow() - timedelta(hours=4)
        fecha_str = hora_local.strftime("%d/%m/%Y %I:%M %p")
        nuevo_reg = pd.DataFrame({
            "FECHA": [fecha_str], "TIPO_MOVIMIENTO": [tipo], "MODELO": [modelo], 
            "CANTIDAD": [cantidad], "MONTO_TOTAL": [monto], "GANANCIA_REAL": [ganancia]
        })
        global df_historial
        df_historial = pd.concat([df_historial, nuevo_reg], ignore_index=True)
        conn.update(worksheet="Historial", data=df_historial)
    except:
        pass

for col in ['COMPRADOS', 'VENDIDOS', 'QUEDAN', 'COSTO_BASE']:
    if col in df_inv.columns:
        df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# Menú Lateral
st.sidebar.image("logo.png", use_container_width=True)

menu = [
    "📊 Dashboard Financiero", 
    "🛒 Registrar Venta", 
    "📦 Gestionar Inventario", 
    "🛠️ Administrar Datos (Borrar/Editar)", # ¡NUEVA PESTAÑA!
    "📜 Historial de Movimientos"
]
choice = st.sidebar.radio("Menú Principal", menu)
st.write("---")

# ---------------- 1. DASHBOARD FINANCIERO (CON GRÁFICOS) ----------------
if choice == "📊 Dashboard Financiero":
    st.subheader("💰 Resumen de Ingresos y Ganancias")
    if not df_ventas.empty:
        for col in ['CANTIDAD', 'GANANCIA_TOTAL', 'TOTAL_INVERTIDO', 'PRECIO_VENTA']:
            df_ventas[col] = pd.to_numeric(df_ventas[col], errors='coerce').fillna(0)
            
        ingresos_totales = (df_ventas['PRECIO_VENTA'] * df_ventas['CANTIDAD']).sum()
        ganancia_neta = df_ventas['GANANCIA_TOTAL'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("💸 Ingresos Brutos Totales", f"${ingresos_totales:,.2f}")
        c2.metric("🟢 Ganancia Neta (Libre)", f"${ganancia_neta:,.2f}")
        
        st.write("---")
        st.subheader("📈 Análisis de Rendimiento")
        
        col1, col2 = st.columns(2)
        
        # GRÁFICO 1: Barras de modelos más vendidos
        with col1:
            ventas_modelo = df_ventas.groupby('MODELO')['CANTIDAD'].sum().reset_index()
            fig_barras = px.bar(ventas_modelo, x='MODELO', y='CANTIDAD', 
                                title="Equipos más vendidos (Unidades)", 
                                color='MODELO', template="plotly_white")
            st.plotly_chart(fig_barras, use_container_width=True)
            
        # GRÁFICO 2: Gráfico de dona para métodos de pago
        with col2:
            pagos = df_ventas.groupby('TIPO_PAGO')['GANANCIA_TOTAL'].sum().reset_index()
            fig_pie = px.pie(pagos, names='TIPO_PAGO', values='GANANCIA_TOTAL', 
                             title="Ingresos por Método de Pago", hole=0.4, template="plotly_white")
            st.plotly_chart(fig_pie, use_container_width=True)
            
    else:
        st.info("Aún no hay ventas registradas para generar los gráficos.")

# ---------------- 2. REGISTRAR VENTA ----------------
elif choice == "🛒 Registrar Venta":
    # (El código de Registrar Venta se mantiene igual, no lo copio todo para ahorrar espacio, 
    # pero asegúrate de que esté en tu archivo)
    st.info("Esta sección funciona igual que antes.")

# ---------------- 3. GESTIONAR INVENTARIO ----------------
elif choice == "📦 Gestionar Inventario":
     # (El código de Inventario se mantiene igual)
     st.info("Esta sección funciona igual que antes.")

# ---------------- 4. ADMINISTRAR DATOS (LA MAGIA DE BORRAR) ----------------
elif choice == "🛠️ Administrar Datos (Borrar/Editar)":
    st.subheader("🛠️ Panel de Control de Administrador")
    st.warning("⚠️ Precaución: Cualquier cambio guardado aquí sobrescribirá tu base de datos de Google Sheets.")
    
    tab1, tab2 = st.tabs(["📝 Editar Ventas", "📦 Editar Inventario"])
    
    with tab1:
        st.write("**Instrucciones:** Selecciona la casilla a la izquierda de la fila que quieres borrar y presiona la tecla `Delete/Suprimir`, o haz doble clic en cualquier celda para corregir un texto o número.")
        if not df_ventas.empty:
            # Aquí está la función data_editor que permite borrar y editar
            ventas_editadas = st.data_editor(df_ventas, num_rows="dynamic", key="editor_ventas", use_container_width=True)
            
            if st.button("💾 Guardar Cambios en Ventas"):
                conn.update(worksheet="Ventas", data=ventas_editadas)
                st.success("¡Ventas actualizadas y guardadas con éxito!")
                st.rerun()
        else:
            st.write("No hay ventas registradas.")
            
    with tab2:
        if not df_inv.empty:
            inv_editado = st.data_editor(df_inv, num_rows="dynamic", key="editor_inv", use_container_width=True)
            
            if st.button("💾 Guardar Cambios en Inventario"):
                conn.update(worksheet="Inventario", data=inv_editado)
                st.success("¡Inventario actualizado con éxito!")
                st.rerun()

# ---------------- 5. HISTORIAL DE MOVIMIENTOS ----------------
elif choice == "📜 Historial de Movimientos":
    st.subheader("📜 Registro Total de Operaciones")
    if not df_historial.empty:
        st.dataframe(df_historial.sort_index(ascending=False), use_container_width=True)
