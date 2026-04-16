import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

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
    "🛠️ Administrar Datos (Borrar/Editar)",
    "📜 Historial de Movimientos"
]
choice = st.sidebar.radio("Menú Principal", menu)
st.write("---")

# ---------------- 1. DASHBOARD FINANCIERO ----------------
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
        
        with col1:
            ventas_modelo = df_ventas.groupby('MODELO')['CANTIDAD'].sum().reset_index()
            fig_barras = px.bar(ventas_modelo, x='MODELO', y='CANTIDAD', 
                                title="Equipos más vendidos (Unidades)", 
                                color='MODELO', template="plotly_white")
            st.plotly_chart(fig_barras, use_container_width=True)
            
        with col2:
            pagos = df_ventas.groupby('TIPO_PAGO')['GANANCIA_TOTAL'].sum().reset_index()
            fig_pie = px.pie(pagos, names='TIPO_PAGO', values='GANANCIA_TOTAL', 
                             title="Ingresos por Método de Pago", hole=0.4, template="plotly_white")
            st.plotly_chart(fig_pie, use_container_width=True)
            
    else:
        st.info("Aún no hay ventas registradas para generar los gráficos.")

# ---------------- 2. REGISTRAR VENTA ----------------
elif choice == "🛒 Registrar Venta":
    st.subheader("🧾 Nueva Venta de Equipos/Cables")
    if not df_inv.empty:
        productos_disponibles = df_inv[df_inv['QUEDAN'] > 0]['MODELO'].tolist()
        if productos_disponibles:
            with st.form("form_venta"):
                modelo = st.selectbox("Modelo vendido:", productos_disponibles)
                
                idx = df_inv.index[df_inv['MODELO'] == modelo].tolist()[0]
                costo_base = df_inv.at[idx, 'COSTO_BASE']
                stock_actual = df_inv.at[idx, 'QUEDAN']
                
                c1, c2 = st.columns(2)
                cant = c1.number_input(f"Cantidad (Disp: {stock_actual}):", min_value=1, max_value=int(stock_actual), step=1)
                tipo_pago = c2.selectbox("Tipo de Pago:", ["DIVISAS", "PAGO MOVIL", "ZELLE", "BINANCE", "EFECTIVO BS"])
                
                c3, c4 = st.columns(2)
                precio_compra = c3.number_input("Costo Unitario:", value=float(costo_base), min_value=0.0)
                precio_venta = c4.number_input("Precio de Venta ($):", min_value=0.0)
                
                if st.form_submit_button("Registrar Venta"):
                    ganancia_unit = precio_venta - precio_compra
                    ganancia_total = ganancia_unit * cant
                    total_invertido = precio_compra * cant
                    
                    hora_local = datetime.utcnow() - timedelta(hours=4)
                    fecha_str = hora_local.strftime("%d/%m/%Y")
                    
                    nueva_venta = pd.DataFrame({
                        "FECHA": [fecha_str], "MODELO": [modelo], "CANTIDAD": [cant], 
                        "TIPO_PAGO": [tipo_pago], "PRECIO_COMPRA": [precio_compra], 
                        "PRECIO_VENTA": [precio_venta], "GANANCIA_UNITARIA": [ganancia_unit],
                        "GANANCIA_TOTAL": [ganancia_total], "TOTAL_INVERTIDO": [total_invertido]
                    })
                    
                    df_ventas = pd.concat([df_ventas, nueva_venta], ignore_index=True)
                    conn.update(worksheet="Ventas", data=df_ventas)
                    
                    df_inv.at[idx, 'VENDIDOS'] += cant
                    df_inv.at[idx, 'QUEDAN'] -= cant
                    conn.update(worksheet="Inventario", data=df_inv)
                    
                    guardar_historial("Venta", modelo, cant, precio_venta * cant, ganancia_total)
                    st.success(f"✅ Venta registrada! Ganancia: ${ganancia_total:,.2f}")
        else:
            st.error("No tienes productos con stock disponible.")
    else:
        st.warning("Primero registra modelos en el inventario.")

# ---------------- 3. GESTIONAR INVENTARIO ----------------
elif choice == "📦 Gestionar Inventario":
    st.subheader("🎧 Catálogo de Panasound")
    with st.expander("➕ Agregar Nuevo Modelo"):
        with st.form("form_inv"):
            n_modelo = st.text_input("Nombre del Modelo:")
            c1, c2 = st.columns(2)
            n_comprados = c1.number_input("Cantidad total comprada:", min_value=1, step=1)
            n_costo = c2.number_input("Costo base por unidad ($):", min_value=0.0)
            
            if st.form_submit_button("Guardar Modelo"):
                if n_modelo:
                    nuevo_prod = pd.DataFrame({
                        "MODELO": [n_modelo], "COMPRADOS": [n_comprados], 
                        "VENDIDOS": [0], "QUEDAN": [n_comprados], "COSTO_BASE": [n_costo]
                    })
                    df_inv = pd.concat([df_inv, nuevo_prod], ignore_index=True)
                    conn.update(worksheet="Inventario", data=df_inv)
                    guardar_historial("Ingreso Inventario", n_modelo, n_comprados, n_comprados * n_costo, 0)
                    st.success("Modelo agregado correctamente.")
                    st.rerun()
                    
    st.write("### Stock Actual")
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)

# ---------------- 4. ADMINISTRAR DATOS ----------------
elif choice == "🛠️ Administrar Datos (Borrar/Editar)":
    st.subheader("🛠️ Panel de Control de Administrador")
    st.warning("⚠️ Precaución: Cualquier cambio guardado aquí sobrescribirá tu base de datos de Google Sheets.")
    
    tab1, tab2 = st.tabs(["📝 Editar Ventas", "📦 Editar Inventario"])
    
    with tab1:
        st.write("**Instrucciones:** Selecciona la casilla a la izquierda de la fila que quieres borrar y presiona la tecla `Delete/Suprimir`, o haz doble clic para corregir.")
        if not df_ventas.empty:
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
