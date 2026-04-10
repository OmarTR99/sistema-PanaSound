import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# Configuración con Logo de Panasound
st.set_page_config(page_title="Panasound Store", page_icon="logo.png", layout="wide")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestaña):
    try:
        return conn.read(worksheet=pestaña, ttl=0).dropna(how="all")
    except:
        return pd.DataFrame()

df_inv = cargar_datos("Inventario")
df_ventas = cargar_datos("Ventas")
df_historial = cargar_datos("Historial")

# Función blindada para el historial
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

# Forzar números en el inventario
for col in ['COMPRADOS', 'VENDIDOS', 'QUEDAN', 'COSTO_BASE']:
    if col in df_inv.columns:
        df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# Menú Lateral
st.sidebar.image("logo.png", use_container_width=True) # Muestra el logo arriba del menú

menu = [
    "📊 Dashboard Financiero", 
    "🛒 Registrar Venta", 
    "📦 Gestionar Inventario", 
    "📑 Tabla de Ventas (Excel)",
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
        inversion_recuperada = df_ventas['TOTAL_INVERTIDO'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💸 Ingresos Brutos (Ventas)", f"${ingresos_totales:,.2f}")
        c2.metric("🟢 Ganancia Neta (Libre)", f"${ganancia_neta:,.2f}")
        c3.metric("🔁 Inversión Recuperada", f"${inversion_recuperada:,.2f}")
        
        st.write("### Ventas por Método de Pago")
        ventas_pago = df_ventas.groupby('TIPO_PAGO')['GANANCIA_TOTAL'].sum().reset_index()
        st.dataframe(ventas_pago, use_container_width=True)
    else:
        st.info("Aún no hay ventas registradas.")

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
                    
                    # 1. Guardar Venta
                    nueva_venta = pd.DataFrame({
                        "FECHA": [fecha_str], "MODELO": [modelo], "CANTIDAD": [cant], 
                        "TIPO_PAGO": [tipo_pago], "PRECIO_COMPRA": [precio_compra], 
                        "PRECIO_VENTA": [precio_venta], "GANANCIA_UNITARIA": [ganancia_unit],
                        "GANANCIA_TOTAL": [ganancia_total], "TOTAL_INVERTIDO": [total_invertido]
                    })
                    
                    df_ventas = pd.concat([df_ventas, nueva_venta], ignore_index=True)
                    conn.update(worksheet="Ventas", data=df_ventas)
                    
                    # 2. Descontar Inventario
                    df_inv.at[idx, 'VENDIDOS'] += cant
                    df_inv.at[idx, 'QUEDAN'] -= cant
                    conn.update(worksheet="Inventario", data=df_inv)
                    
                    # 3. Guardar en Historial
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
                    
                    # Guardar en historial
                    guardar_historial("Ingreso Inventario", n_modelo, n_comprados, n_comprados * n_costo, 0)
                    
                    st.success("Modelo agregado correctamente.")
                    st.rerun()
                    
    st.write("### Stock Actual")
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)

# ---------------- 4. TABLA DE VENTAS ----------------
elif choice == "📑 Tabla de Ventas (Excel)":
    st.subheader("📑 Registro de Ventas")
    if not df_ventas.empty:
        st.dataframe(df_ventas.sort_index(ascending=False), use_container_width=True)
    else:
        st.write("Aún no hay ventas para mostrar.")

# ---------------- 5. HISTORIAL DE MOVIMIENTOS ----------------
elif choice == "📜 Historial de Movimientos":
    st.subheader("📜 Registro Total de Operaciones")
    st.info("Aquí se guarda cada acción realizada con su fecha y hora exacta.")
    if not df_historial.empty:
        st.dataframe(df_historial.sort_index(ascending=False), use_container_width=True)
    else:
        st.write("El historial está vacío.")
