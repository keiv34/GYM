# GYM_App/modules/cuadres/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from GYM_App.extensions import db
from GYM_App.models import CuadreCaja, Venta, ServicioCliente, Usuario
from sqlalchemy import func
from datetime import datetime

cuadres_bp = Blueprint("cuadres", __name__, template_folder="../../templates/cuadres")

# Fondo inicial de caja (ej. $100.00 para cambio)
FONDO_INICIAL = 100.00

# ----------------------------------------------------------------------
# FUNCIÓN CLAVE: CALCULA LAS VENTAS DEL PERIODO DESDE EL ÚLTIMO CIERRE
# ----------------------------------------------------------------------
def get_ventas_del_periodo():
    """Calcula el total de ventas (productos y servicios) desde el último cuadre,
    filtrando por método de pago (Efectivo y Tarjeta)."""
    
    ultimo_cuadre = CuadreCaja.query.order_by(CuadreCaja.fecha_cierre.desc()).first()
    
    # Define la fecha de inicio del periodo.
    if ultimo_cuadre:
        # Usa el momento exacto del último cierre para reiniciar el contador.
        fecha_inicio_periodo = ultimo_cuadre.fecha_cierre
    else:
        # Si no hay cuadres, usa una fecha segura y antigua para sumar todas las ventas históricas.
        # Si tu gimnasio es más reciente, ajusta este año.
        fecha_inicio_periodo = datetime(2023, 1, 1) 
    
    # --- 1. CONSULTAS DE VENTAS DE PRODUCTOS (Tabla Venta) ---
    
    # Ventas de Productos en Efectivo 🚨 Filtra por fecha y método de pago
    productos_efectivo = db.session.query(
        func.sum(Venta.total)
    ).filter(
        Venta.fecha >= fecha_inicio_periodo,
        Venta.metodo_pago == 'Efectivo'
    ).scalar() or 0.00
    
    # Ventas de Productos con Tarjeta
    productos_tarjeta = db.session.query(
        func.sum(Venta.total)
    ).filter(
        Venta.fecha >= fecha_inicio_periodo,
        Venta.metodo_pago == 'Tarjeta'
    ).scalar() or 0.00
    
    # --- 2. CONSULTAS DE PAGOS DE SERVICIOS (Tabla ServicioCliente) ---
    # El costo total es (costo_servicio + costo_inscripcion)
    
    # Pagos de Servicios en Efectivo 🚨 Filtra por fecha y método de pago
    servicios_efectivo = db.session.query(
        func.sum(ServicioCliente.costo_servicio + ServicioCliente.costo_inscripcion)
    ).filter(
        ServicioCliente.fecha_inicio >= fecha_inicio_periodo,
        ServicioCliente.metodo_pago == 'Efectivo'
    ).scalar() or 0.00

    # Pagos de Servicios con Tarjeta
    servicios_tarjeta = db.session.query(
        func.sum(ServicioCliente.costo_servicio + ServicioCliente.costo_inscripcion)
    ).filter(
        ServicioCliente.fecha_inicio >= fecha_inicio_periodo,
        ServicioCliente.metodo_pago == 'Tarjeta'
    ).scalar() or 0.00

    # 3. Consolidar resultados
    ventas_efectivo_sistema = float(productos_efectivo) + float(servicios_efectivo)
    ventas_tarjeta_sistema = float(productos_tarjeta) + float(servicios_tarjeta)
    ventas_total_sistema = ventas_efectivo_sistema + ventas_tarjeta_sistema

    # Crear el diccionario de totales
    totales = {
        'Efectivo': ventas_efectivo_sistema,
        'Tarjeta': ventas_tarjeta_sistema,
        'Total': ventas_total_sistema,
        'fecha_inicio_periodo': fecha_inicio_periodo.strftime('%d-%m-%Y %H:%M:%S')
    }
    
    return totales

# ----------------------------------------------------------------------
# RUTA: CIERRE DE CAJA
# ----------------------------------------------------------------------
@cuadres_bp.route("/cierre-caja", methods=["GET", "POST"])
@login_required
def cierre_caja():
    # Obtiene las ventas del periodo desde el último cierre
    totales = get_ventas_del_periodo()
    
    if request.method == "POST":
        try:
            monto_contado_efectivo = float(request.form.get("monto_contado_efectivo"))
        except (TypeError, ValueError):
            flash("El monto contado debe ser un número válido.", "danger")
            return redirect(url_for("cuadres.cierre_caja"))

        # Cálculo de la diferencia (Ventas en Efectivo del periodo + Fondo Inicial)
        efectivo_esperado = totales.get('Efectivo', 0.00) + FONDO_INICIAL
        diferencia = monto_contado_efectivo - efectivo_esperado
        
        # Guardar el cuadre
        nuevo_cuadre = CuadreCaja(
            ventas_efectivo_sistema=totales.get('Efectivo', 0.00),
            ventas_tarjeta_sistema=totales.get('Tarjeta', 0.00),
            ventas_total_sistema=totales.get('Total', 0.00),
            monto_contado_efectivo=monto_contado_efectivo,
            diferencia=diferencia,
            usuario_id=current_user.id
        )
        
        db.session.add(nuevo_cuadre)
        db.session.commit()
        
        # Mostrar mensaje de resultado
        if diferencia == 0:
            flash("✅ ¡Cierre de caja exitoso! Cifras perfectas.", "success")
        elif diferencia > 0:
            flash(f"⚠️ Cierre de caja con SOBRANTE de ${abs(diferencia):.2f}. Revisar.", "warning")
        else:
            flash(f"❌ Cierre de caja con FALTANTE de ${abs(diferencia):.2f}. ¡URGENTE! Revisar.", "danger")
            
        return redirect(url_for("cuadres.historial_cuadres"))

    # Contexto para el GET (Mostrar la pantalla de cierre)
    contexto = {
        'totales': totales,
        'fondo_inicial': FONDO_INICIAL,
        'efectivo_esperado': totales.get('Efectivo', 0.00) + FONDO_INICIAL,
        'fecha_cierre': datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    }
    
    return render_template("cierre_caja.html", **contexto)

# ----------------------------------------------------------------------
# RUTA: HISTORIAL
# ----------------------------------------------------------------------
@cuadres_bp.route("/historial")
@login_required
def historial_cuadres():
    cuadres = CuadreCaja.query.order_by(CuadreCaja.fecha_cierre.desc()).all()
    return render_template("historial_cuadres.html", cuadres=cuadres)