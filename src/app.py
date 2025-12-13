import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# --- CONFIGURACIÓN DE ARCHIVOS ---
ARCHIVO_DATOS = "mis_gastos.csv"
ARCHIVO_CONFIG = "config.json"

# --- CATEGORÍAS POR DEFECTO ---
CATEGORIAS = {
    "Comida": ["Supermercado", "Restaurante", "Glovo/Delivery", "Café"],
    "Transporte": ["Gasolina", "Metro/Bus", "Taxi/Uber", "Mantenimiento"],
    "Ocio": ["Cine", "Fiesta", "Suscripciones", "Viajes"],
    "Servicios": ["Luz", "Agua", "Internet", "Teléfono"],
    "Vivienda": ["Alquiler", "Hipoteca", "Reparaciones"],
    "Salud": ["Farmacia", "Médico", "Gimnasio"]
}

# --- FUNCIONES DE GESTIÓN DE DATOS ---

def cargar_config():
    # Valores por defecto si no existe el archivo
    default_config = {
        "salario_bruto": 2000.0,
        "irpf_porcentaje": 15.0,
        "seguridad_social_porcentaje": 6.35, # Aproximado estándar
        "ahorros_actuales": 5000.0,
        "presupuestos": {k: 200.0 for k in CATEGORIAS.keys()},
        "gastos_fijos": [
            {"titulo": "Spotify", "importe": 9.99, "categoria": "Ocio", "subcategoria": "Suscripciones"},
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
        # Añadimos columna 'Metodo_Pago'
        df = pd.DataFrame(columns=["Fecha", "Mes", "Categoria", "Subcategoria", "Importe", "Metodo_Pago", "Notas"])
        df.to_csv(ARCHIVO_DATOS, index=False)
        return df
    return pd.read_csv(ARCHIVO_DATOS)

def guardar_gasto(nuevo_gasto):
    df = cargar_datos()
    nuevo_df = pd.DataFrame([nuevo_gasto])
    df_final = pd.concat([df, nuevo_df], ignore_index=True)
    df_final.to_csv(ARCHIVO_DATOS, index=False)

def procesar_gastos_fijos():
    """Revisa si los gastos fijos de este mes ya están puestos. Si no, los añade."""
    df = cargar_datos()
    config = cargar_config()
    mes_actual = datetime.now().strftime("%B")
    gastos_fijos = config.get("gastos_fijos", [])
    
    cambios = False
    for fijo in gastos_fijos:
        # Comprobamos si ya existe este gasto fijo en este mes
        existe = False
        if not df.empty:
            filtro = (df["Mes"] == mes_actual) & (df["Notas"] == "Gasto Fijo Automático") & (df["Subcategoria"] == fijo["subcategoria"])
            if not df[filtro].empty:
                existe = True
        
        if not existe:
            # Lo añadimos
            nuevo = {
                "Fecha": datetime.now().strftime("%Y-%m-01"), # Día 1 del mes
                "Mes": mes_actual,
                "Categoria": fijo["categoria"],
                "Subcategoria": fijo["subcategoria"],
                "Importe": fijo["importe"],
                "Metodo_Pago": "Tarjeta Personal", # Asumimos personal por defecto
                "Notas": "Gasto Fijo Automático"
            }
            # No usamos guardar_gasto aquí para evitar abrir/cerrar archivo muchas veces, mejor al final
            nuevo_df = pd.DataFrame([nuevo])
            df = pd.concat([df, nuevo_df], ignore_index=True)
            cambios = True
            st.toast(f"✅ Gasto fijo añadido: {fijo['titulo']}")
            
    if cambios:
        df.to_csv(ARCHIVO_DATOS, index=False)

# --- INTERFAZ GRÁFICA ---

st.set_page_config(page_title="Mi Finanzas Pro", layout="wide")

# Inicialización
procesar_gastos_fijos()
config = cargar_config()
df = cargar_datos()

# TABS PRINCIPALES
tab1, tab2, tab3 = st.tabs(["📊 Dashboard & KPIs", "📝 Registrador", "⚙️ Configuración"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.title("💸 Mi Situación Financiera")
    
    if not df.empty:
        # FILTRO DE MES
        meses_disponibles = df["Mes"].unique()
        mes_seleccionado = st.selectbox("Selecciona Mes a Analizar", meses_disponibles, index=len(meses_disponibles)-1)
        
        df_mes = df[df["Mes"] == mes_seleccionado]
        
        # CÁLCULOS COMPLEJOS (Cobee vs Personal)
        gastos_cobee = df_mes[df_mes["Metodo_Pago"] == "Cobee"]["Importe"].sum()
        gastos_personales = df_mes[df_mes["Metodo_Pago"] == "Tarjeta Personal"]["Importe"].sum()
        
        # CÁLCULO DE NÓMINA PREVISTA
        # Lógica: Bruto - Cobee = Base Imponible. Luego quitamos IRPF y SS.
        salario_bruto = config["salario_bruto"]
        base_imponible = salario_bruto - gastos_cobee
        
        # Impuestos estimados
        impuestos = base_imponible * (config["irpf_porcentaje"] / 100)
        ss = salario_bruto * (config["seguridad_social_porcentaje"] / 100) # La SS suele ir sobre el bruto total base
        
        salario_neto_estimado = base_imponible - impuestos - ss
        
        # Dinero Actual vs Previsto
        # Dinero Actual = Ahorros (fijos en config) - Gastos Personales de este mes (asumiendo que los ahorros eran al inicio del mes)
        # Nota: Para hacerlo perfecto, "Ahorros" debería actualizarse mensualmente, aquí usamos el valor config como base.
        dinero_actual = config["ahorros_actuales"] - gastos_personales
        dinero_final_mes = dinero_actual + salario_neto_estimado

        # MOSTRAR KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Dinero Disponible HOY", f"{dinero_actual:.2f} €", delta=f"-{gastos_personales:.2f}€ gastados")
        col2.metric("📅 Previsto Fin de Mes", f"{dinero_final_mes:.2f} €", help="Dinero hoy + Nómina estimada")
        col3.metric("💳 Gasto Cobee", f"{gastos_cobee:.2f} €", help="Se descuenta de tu Bruto")
        col4.metric("📉 Nómina Neta Estimada", f"{salario_neto_estimado:.2f} €")

        st.markdown("---")
        
        # PRESUPUESTOS vs REALIDAD
        st.subheader("🎯 Control de Presupuestos")
        gastos_por_cat = df_mes.groupby("Categoria")["Importe"].sum()
        
        for cat, presupuesto in config["presupuestos"].items():
            gasto_real = gastos_por_cat.get(cat, 0.0)
            porcentaje = min(gasto_real / presupuesto, 1.0) if presupuesto > 0 else 0
            
            c1, c2 = st.columns([3, 1])
            with c1:
                st.write(f"**{cat}** ({gasto_real:.0f}€ / {presupuesto:.0f}€)")
                # Color de la barra cambia si te pasas
                color_barra = "red" if gasto_real > presupuesto else "green" 
                st.progress(porcentaje)
            with c2:
                diferencia = presupuesto - gasto_real
                if diferencia < 0:
                    st.error(f"⚠️ +{abs(diferencia):.0f}€")
                else:
                    st.success(f"✅ Quedan {diferencia:.0f}€")

    else:
        st.info("No hay datos para mostrar aún.")

# --- TAB 2: REGISTRADOR ---
with tab2:
    st.header("Nuevo Gasto")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        fecha = st.date_input("Fecha", datetime.today())
        cat_sel = st.selectbox("Categoría", list(CATEGORIAS.keys()))
        sub_sel = st.selectbox("Subcategoría", CATEGORIAS[cat_sel])
    
    with col_b:
        metodo = st.radio("Método de Pago", ["Tarjeta Personal", "Cobee"], horizontal=True)
        importe = st.number_input("Importe (€)", min_value=0.0, format="%.2f")
        notas = st.text_input("Notas (Opcional)")

    if st.button("Guardar Movimiento", use_container_width=True):
        if importe > 0:
            nuevo = {
                "Fecha": fecha,
                "Mes": fecha.strftime("%B"),
                "Categoria": cat_sel,
                "Subcategoria": sub_sel,
                "Importe": importe,
                "Metodo_Pago": metodo,
                "Notas": notas
            }
            guardar_gasto(nuevo)
            st.success("Guardado correctamente!")
            st.rerun() # Recarga la página para actualizar KPIs
        else:
            st.error("Pon un importe válido")
            
    st.markdown("---")
    st.subheader("Últimos 10 movimientos")
    st.dataframe(df.tail(10).sort_index(ascending=False), use_container_width=True)

# --- TAB 3: CONFIGURACIÓN ---
with tab3:
    st.header("⚙️ Ajustes de tu Economía")
    
    with st.form("form_config"):
        st.subheader("Datos Salariales")
        nuevo_bruto = st.number_input("Salario Bruto Mensual", value=config["salario_bruto"])
        nuevo_irpf = st.number_input("% IRPF", value=config["irpf_porcentaje"])
        
        st.subheader("Estado Actual")
        nuevos_ahorros = st.number_input("Ahorros Iniciales del Mes (Caja)", value=config["ahorros_actuales"])
        
        st.subheader("Presupuestos por Categoría")
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

    st.warning("Nota: Los gastos fijos (Spotify, etc) edítalos directamente en el archivo 'config.json' si quieres añadir más, o pídeme que añada un editor aquí.")