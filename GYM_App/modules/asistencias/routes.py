from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from GYM_App.extensions import db
from GYM_App.models import Cliente, Asistencia, ServicioCliente
from datetime import datetime, time
from sqlalchemy import func
import pytz

asistencias_bp = Blueprint("asistencias", __name__, template_folder="../../templates/asistencias")

HORA_APERTURA = time(6, 0, 0)
HORA_CIERRE = time(22, 0, 0)
MEXICO_TZ = pytz.timezone('America/Mexico_City')

@asistencias_bp.route("/")
def index():
    return render_template("asistencia.html")

@asistencias_bp.route("/asistencia", methods=["POST"])
def registrar_asistencia():
    entrada_usuario = request.form.get("entrada_usuario")
    
    # 1. Obtener la hora actual en la zona horaria local
    now_local = datetime.now(MEXICO_TZ)
    
    # 2. Verificar si el gimnasio está abierto
    if not (HORA_APERTURA <= now_local.time() <= HORA_CIERRE):
        flash("El gimnasio está cerrado. El horario de acceso es de 6:00 a.m. a 10:00 p.m.", "warning")
        return redirect(url_for("asistencias.index"))
        
    try:
        cliente = Cliente.query.get(int(entrada_usuario))
    except (ValueError, TypeError):
        cliente = Cliente.query.get(entrada_usuario)
    
    if not cliente:
        flash("Cliente no encontrado.", "danger")
        return redirect(url_for("asistencias.index"))

    # 3. Verificar si el cliente tiene una membresía activa
    membresia_activa = ServicioCliente.query.filter(
        ServicioCliente.cliente_id == cliente.id,
        ServicioCliente.estatus == True
    ).first()

    if not membresia_activa:
        flash(f"El cliente {cliente.nombre} no tiene una membresía activa.", "danger")
        return redirect(url_for("asistencias.index"))

    # 4. Verificar si ya asistió hoy (basado en la fecha local)
    # Crea un objeto datetime para el inicio del día local y lo convierte a UTC
    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_local.astimezone(pytz.utc)

    asistencia_hoy = Asistencia.query.filter(
        Asistencia.cliente_id == cliente.id,
        Asistencia.fecha >= today_start_utc
    ).first()

    if asistencia_hoy:
        flash(f"El cliente {cliente.nombre} ya registró su asistencia el día de hoy.", "warning")
        return redirect(url_for("asistencias.index"))

    # 5. Registrar la nueva asistencia
    nueva_asistencia = Asistencia(cliente_id=cliente.id)
    db.session.add(nueva_asistencia)
    db.session.commit()
    
    flash(f"¡Asistencia de {cliente.nombre} registrada con éxito!", "success")
    return redirect(url_for("asistencias.index"))


# Ruta API para validar acceso (misma lógica que la anterior)
@asistencias_bp.route("/api/asistencia/validar/<string:entrada_usuario>")
def validar_asistencia_api(entrada_usuario):
    now_local = datetime.now(MEXICO_TZ)
    
    if not (HORA_APERTURA <= now_local.time() <= HORA_CIERRE):
        return jsonify({"status": "error", "message": "El gimnasio está cerrado."}), 403
    
    try:
        cliente = Cliente.query.get(int(entrada_usuario))
    except (ValueError, TypeError):
        cliente = Cliente.query.get(entrada_usuario)
    
    if not cliente:
        return jsonify({"status": "error", "message": "Cliente no encontrado."}), 404

    membresia_activa = ServicioCliente.query.filter(
        ServicioCliente.cliente_id == cliente.id,
        ServicioCliente.estatus == True
    ).first()

    if not membresia_activa:
        return jsonify({"status": "error", "message": f"El cliente {cliente.nombre} no tiene membresía activa."}), 403

    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_local.astimezone(pytz.utc)

    asistencia_hoy = Asistencia.query.filter(
        Asistencia.cliente_id == cliente.id,
        Asistencia.fecha >= today_start_utc
    ).first()
    
    if asistencia_hoy:
        return jsonify({"status": "error", "message": f"El cliente {cliente.nombre} ya registró su asistencia hoy."}), 403

    return jsonify({"status": "success", "message": f"Acceso permitido para {cliente.nombre}.", "cliente": {"id": cliente.id, "nombre": cliente.nombre}})

@asistencias_bp.route("/historial")
def historial():
    """
    Ruta para la página principal del historial de asistencias.
    No procesa los filtros, el frontend se encarga de eso en tiempo real.
    """
    return render_template("historial_asistencia.html")

@asistencias_bp.route("/api/historial")
def get_historial_api():
    """
    Ruta API que devuelve todas las asistencias en formato JSON para la búsqueda en tiempo real.
    """
    asistencias = (
        db.session.query(Asistencia, Cliente)
        .join(Cliente, Asistencia.cliente_id == Cliente.id)
        .order_by(Asistencia.fecha.desc())
        .all()
    )
    
    historial_data = []
    for asistencia, cliente in asistencias:
        historial_data.append({
            'id': asistencia.id,
            'cliente_nombre': cliente.nombre,
            'fecha': asistencia.fecha.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(historial_data)