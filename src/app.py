import streamlit as st
import pandas as pd
import os
import json
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE ARCHIVOS ---
ARCHIVO_DATOS = "data/mis_gastos.csv"
ARCHIVO_CONFIG = "config/config.json"

# --- LISTAS DE DATOS ---
CATEGORIAS_GASTOS = {
    "Comida": ["Supermercado", "Restaurante", "Glovo/Delivery", "Otros"],
    "Transporte": ["Gasolina", "Metro/Bus", "Taxi/Uber", "Mantenimiento", "Otros"],
    "Ocio": ["Bar", "Cine", "Fiesta", "Suscripciones", "Viajes", "Otros"],
    "Servicios": ["Luz", "Agua", "Internet", "Teléfono", "Otros"],
    "Vivienda": ["Alquiler", "Hipoteca", "Reparaciones", "Otros"],
    "Salud": ["Farmacia", "Médico", "Gimnasio", "Otros"]
}

# Nuevas opciones para ingresos
ORIGENES_INGRESOS = ["Bizum", "Transferencia", "Efectivo", "Regalo", "Venta 2ª Mano", "Otros"]

# --- FUNCIONES DE GESTIÓN DE DATOS ---

def cargar_config():
    default_config = {
        "salario_bruto": 2000.0,
        "irpf_porcentaje": 15.0,
        "seguridad_social_porcentaje": 6.35,
        "ahorros_actuales": 5000.0,
        "presupuestos": {k: 200.0 for k in CATEGORIAS_GASTOS.keys()},
        "gastos_fijos": [
            {"titulo": "Spotify", "importe": 21, "categoria": "Ocio", "subcategoria": "Suscripciones"},
            {"titulo": "iCloud", "importe": 2.99, "categoria": "Servicios", "subcategoria": "Internet"}
        ]
    }
    if not os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG, 'w') as f:
            json.dump(default_config, f)
        return default_config
    
    with open(ARCHIVO_CONFIG, 'r') as f:
        return json.load(f)

def guardar_config(config):
    with open(ARCHIVO_CONFIG, 'w') as f:
        json.dump(config, f)

def cargar_datos():
    if not os.path.exists(ARCHIVO_DATOS):
        df = pd.DataFrame(columns=["Fecha", "Mes", "Categoria", "Subcategoria", "Importe", "Metodo_Pago", "Notas"])
        df.to_csv(ARCHIVO_DATOS, index=False)
        return df
    
    df = pd.read_csv(ARCHIVO_DATOS)
    df = df.fillna("")
    return df

def guardar_gasto(nuevo_gasto):
    df = cargar_datos()
    nuevo_df = pd.DataFrame([nuevo_gasto])
    df_final = pd.concat([df, nuevo_df], ignore_index=True)
    df_final.to_csv(ARCHIVO_DATOS, index=False)

def procesar_gastos_fijos():
    """Añade gastos fijos automáticos (siempre negativos)"""
    df = cargar_datos()
    config = cargar_config()
    mes_actual = datetime.now().strftime("%B")
    gastos_fijos = config.get("gastos_fijos", [])
    
    cambios = False
    for fijo in gastos_fijos:
        existe = False
        if not df.empty:
            filtro = (df["Mes"] == mes_actual) & (df["Notas"] == "Gasto Fijo Automático") & (df["Subcategoria"] == fijo["subcategoria"])
            if not df[filtro].empty:
                existe = True
        
        if not existe:
            nuevo = {
                "Fecha": datetime.now().strftime("%Y-%m-01"),
                "Mes": mes_actual,
                "Categoria": fijo["categoria"],
                "Subcategoria": fijo["subcategoria"],
                "Importe": -abs(fijo["importe"]),
                "Metodo_Pago": "Tarjeta Personal",
                "Notas": "Gasto Fijo Automático"
            }
            nuevo_df = pd.DataFrame([nuevo])
            df = pd.concat([df, nuevo_df], ignore_index=True)
            cambios = True
            st.toast(f"✅ Gasto fijo añadido: {fijo['titulo']}")
            
    if cambios:
        df.to_csv(ARCHIVO_DATOS, index=False)

def crear_gauge(categoria, gasto_real, presupuesto):
    # Color de la barra (Igual que antes)
    color_barra = "#2ecc71" if gasto_real <= presupuesto else "#e74c3c"
    
    ref_trucada = (2 * gasto_real) - presupuesto

    # Creamos el gráfico con el MODO ORIGINAL
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta", # Mantenemos el modo original
        value = gasto_real,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': categoria, 'font': {'size': 17}}, # Título nativo visible y tamaño original
        
        delta = {
            'reference': ref_trucada, 
            'increasing': {'color': "#2ecc71"}, 
            'decreasing': {'color': "#e74c3c"}
        },
        
        gauge = {
            'axis': {'range': [None, max(presupuesto, gasto_real)], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color_barra},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, presupuesto], 'color': "whitesmoke"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': presupuesto
            }
        }
    ))
    fig.update_layout(height=270, margin=dict(l=20, r=20, t=60, b=20))
    return fig

# --- INTERFAZ GRÁFICA ---

st.set_page_config(page_title="Mi Finanzas Pro", layout="wide")

procesar_gastos_fijos()
config = cargar_config()
df = cargar_datos()

# TABS PRINCIPALES
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & KPIs", "📝 Registrador", "⚙️ Configuración"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.title("💸 Mi Situación Financiera")
    
    if not df.empty:
        meses_disponibles = df["Mes"].unique()
        meses_disponibles = [m for m in meses_disponibles if m]
        
        if len(meses_disponibles) > 0:
            mes_seleccionado = st.selectbox("Selecciona Mes a Analizar", meses_disponibles, index=len(meses_disponibles)-1)
            df_mes = df[df["Mes"] == mes_seleccionado]
            
            # Separar Gastos e Ingresos
            df_gastos = df_mes[df_mes["Importe"] < 0]
            df_ingresos = df_mes[df_mes["Importe"] > 0]
            
            # Cálculos
            gastos_cobee = df_gastos[df_gastos["Metodo_Pago"] == "Cobee"]["Importe"].sum()
            gastos_personales = df_gastos[df_gastos["Metodo_Pago"] == "Tarjeta Personal"]["Importe"].sum()
            ingresos_extra = df_ingresos["Importe"].sum()
            
            salario_bruto = config["salario_bruto"]
            base_imponible = salario_bruto - gastos_cobee 
            impuestos = base_imponible * (config["irpf_porcentaje"] / 100)
            ss = salario_bruto * (config["seguridad_social_porcentaje"] / 100)
            salario_neto_estimado = base_imponible - impuestos - ss
            
            dinero_actual = config["ahorros_actuales"] + ingresos_extra + gastos_personales
            dinero_final_mes = dinero_actual + salario_neto_estimado

            # KPIs
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("💰 Dinero Disponible HOY", f"{dinero_actual:.2f} €", delta=f"{ingresos_extra:.2f}€ ingresados (extras)")
            col2.metric("📅 Previsto Fin de Mes", f"{dinero_final_mes:.2f} €")
            col3.metric("💳 Gasto Cobee", f"{abs(gastos_cobee):.2f} €", delta="Se descuenta del Bruto", delta_color="inverse")
            col4.metric("📉 Nómina Neta Estimada", f"{salario_neto_estimado:.2f} €")

            st.markdown("---")
            
            # Presupuestos
            # --- PRESUPUESTOS CON CORONAS CIRCULARES ---
            st.subheader("🎯 Control de Presupuestos (Gastos)")
            
            gastos_por_cat = df_gastos.groupby("Categoria")["Importe"].sum().abs()
            
            # Creamos columnas para organizar los "relojes" (3 por fila)
            categorias_list = list(config["presupuestos"].items())
            
            # Iteramos en bloques de 3 para maquetación
            for i in range(0, len(categorias_list), 3):
                cols = st.columns(3)
                # Procesamos hasta 3 categorías en esta fila
                for j in range(3):
                    if i + j < len(categorias_list):
                        cat, presupuesto = categorias_list[i + j]
                        gasto_real = gastos_por_cat.get(cat, 0.0)
                        
                        with cols[j]:
                            fig = crear_gauge(cat, gasto_real, presupuesto)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Texto resumen debajo del gráfico
                            restante = presupuesto - gasto_real
                            if restante >= 0:
                                st.caption(f"✅ Quedan {restante:.2f}€")
                            else:
                                st.caption(f"⚠️ Te has pasado {abs(restante):.2f}€")
        else:
             st.info("No hay datos válidos para mostrar.")
    else:
        st.info("No hay datos para mostrar aún.")

# --- TAB 2: REGISTRADOR ---
with tab2:
    st.header("Registrar Movimiento")
    
    # Definimos la función que se ejecutará AL PULSAR el botón (Callback)
    def guardar_callback(fecha_val, cat_val, sub_val, metodo_val, tipo_val):
        # 1. Recuperamos importe y notas desde el session_state (usando sus keys)
        importe_val = st.session_state.nuevo_importe
        notas_val = st.session_state.nueva_nota
        
        if importe_val > 0:
            # Lógica de signo
            if tipo_val == "🔴 Gasto":
                importe_final = -abs(importe_val)
            else:
                importe_final = abs(importe_val)

            # Construimos el objeto
            nuevo = {
                "Fecha": fecha_val,
                "Mes": fecha_val.strftime("%B"), # Ojo: esto guardará el mes en idioma del sistema
                "Categoria": cat_val,
                "Subcategoria": sub_val,
                "Importe": importe_final,
                "Metodo_Pago": metodo_val,
                "Notas": notas_val
            }
            
            # Guardamos
            guardar_gasto(nuevo)
            
            # --- AQUÍ SÍ PODEMOS LIMPIAR ---
            # Como esto se ejecuta antes de recargar la página, es legal modificar el estado
            st.session_state.nuevo_importe = 0.0
            st.session_state.nueva_nota = ""
            
            # Guardamos un mensaje de éxito en el estado para mostrarlo tras la recarga
            st.session_state.mensaje_exito = f"{tipo_val.split()[1]} guardado correctamente!"
        else:
            st.session_state.mensaje_error = "El importe debe ser mayor a 0"

    # --- INTERFAZ ---
    
    # Mostramos mensajes pendientes (si existen del click anterior)
    if "mensaje_exito" in st.session_state:
        st.success(st.session_state.mensaje_exito)
        del st.session_state.mensaje_exito # Lo borramos para que no salga siempre
    if "mensaje_error" in st.session_state:
        st.error(st.session_state.mensaje_error)
        del st.session_state.mensaje_error

    tipo_movimiento = st.radio("¿Qué quieres registrar?", ["🔴 Gasto", "🟢 Ingreso"], horizontal=True)
    
    col_a, col_b = st.columns(2)
    
    # Variables auxiliares para recoger los datos de los inputs que NO tienen key
    cat_sel = ""
    sub_sel = ""
    metodo = ""
    
    with col_a:
        fecha = st.date_input("Fecha", datetime.today())
        
        if tipo_movimiento == "🔴 Gasto":
            cat_sel = st.selectbox("Categoría", list(CATEGORIAS_GASTOS.keys()))
            sub_sel = st.selectbox("Subcategoría", CATEGORIAS_GASTOS[cat_sel])
        else:
            cat_sel = "Ingreso"
            sub_sel = st.selectbox("Origen del dinero", ORIGENES_INGRESOS)
            metodo = sub_sel # En ingreso, el método es el origen
    
    with col_b:
        if tipo_movimiento == "🔴 Gasto":
            metodo = st.radio("Método de Pago", ["Tarjeta Personal", "Cobee"], horizontal=True)
        else:
            pass
        
        # IMPORTANTE: Los inputs que queremos borrar deben tener KEY
        st.number_input("Importe (€)", min_value=0.0, format="%.2f", key="nuevo_importe")
        st.text_input("Notas / Concepto", placeholder="Ej: Regalo cumpleaños...", key="nueva_nota")

    # BOTÓN CON CALLBACK
    # Pasamos las variables que NO están en session_state (fecha, cats) como argumentos (args)
    st.button(
        "Guardar Movimiento", 
        use_container_width=True,
        on_click=guardar_callback,
        args=(fecha, cat_sel, sub_sel, metodo, tipo_movimiento)
    )

    st.markdown("---")
    st.subheader("Últimos 10 movimientos")
    
    def color_signo(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    if not df.empty:
        st.dataframe(
            df.tail(10).sort_index(ascending=False).style.map(color_signo, subset=['Importe']).format({'Importe': '{:.2f}€'}), 
            use_container_width=True
        )

# --- TAB 3: CONFIGURACIÓN ---
with tab3:
    st.header("⚙️ Ajustes")
    
    with st.form("form_config"):
        st.subheader("Datos Salariales")
        nuevo_bruto = st.number_input("Salario Bruto Mensual", value=config["salario_bruto"])
        nuevo_irpf = st.number_input("% IRPF", value=config["irpf_porcentaje"])
        
        st.subheader("Estado Actual")
        nuevos_ahorros = st.number_input("Ahorros Iniciales (Base)", value=config["ahorros_actuales"])
        
        st.subheader("Presupuestos (Límites de Gasto)")
        nuevos_presupuestos = {}
        cols = st.columns(3)
        for i, (cat, val) in enumerate(config["presupuestos"].items()):
            with cols[i % 3]:
                nuevos_presupuestos[cat] = st.number_input(f"Tope {cat}", value=val)
        
        if st.form_submit_button("Guardar Configuración"):
            config["salario_bruto"] = nuevo_bruto
            config["irpf_porcentaje"] = nuevo_irpf
            config["ahorros_actuales"] = nuevos_ahorros
            config["presupuestos"] = nuevos_presupuestos
            guardar_config(config)
            st.success("Configuración actualizada")
            st.rerun()