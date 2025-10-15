from flask import Blueprint, jsonify, render_template, request
from GYM_App.extensions import db
from GYM_App.models import Cliente, ServicioCliente, Venta, Servicio
from sqlalchemy import func, extract
from datetime import datetime, timedelta

estadisticas_bp = Blueprint("estadisticas", __name__, url_prefix="/estadisticas")

@estadisticas_bp.route("/")
def dashboard():
    """
    Ruta principal para el dashboard de estadísticas.
    """
    return render_template("estadisticas/dashboard.html")

@estadisticas_bp.route("/api/resumen")
def get_resumen_data():
    """
    Retorna datos clave de resumen para el dashboard, con filtros de fecha.
    """
    try:
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')

        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d') if fecha_inicio_str else None
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d') if fecha_fin_str else datetime.now()

        # Consultas con filtro de fecha
        query_ventas = db.session.query(func.sum(Venta.total))
        query_servicios = db.session.query(func.sum(ServicioCliente.costo_servicio + ServicioCliente.costo_inscripcion))
        
        if fecha_inicio and fecha_fin:
            query_ventas = query_ventas.filter(Venta.fecha >= fecha_inicio, Venta.fecha <= fecha_fin)
            query_servicios = query_servicios.filter(ServicioCliente.fecha_inicio >= fecha_inicio, ServicioCliente.fecha_inicio <= fecha_fin)
        
        total_clientes = Cliente.query.count()
        clientes_activos = ServicioCliente.query.filter_by(estatus=True).count()

        ingresos_ventas = query_ventas.scalar() or 0
        ingresos_servicios = query_servicios.scalar() or 0
        ingresos_total = ingresos_ventas + ingresos_servicios

        query_nuevos = Cliente.query
        if fecha_inicio and fecha_fin:
            query_nuevos = query_nuevos.filter(Cliente.fecha_registro >= fecha_inicio, Cliente.fecha_registro <= fecha_fin)
        
        nuevos_clientes_periodo = query_nuevos.count()

        resumen = {
            "total_clientes": total_clientes,
            "clientes_activos": clientes_activos,
            "ingresos_total": f"{ingresos_total:.2f}",
            "ingresos_servicios": f"{ingresos_servicios:.2f}",
            "ingresos_ventas": f"{ingresos_ventas:.2f}",
            "nuevos_clientes_mes": nuevos_clientes_periodo
        }
        
        return jsonify(resumen)
    except Exception as e:
        print(f"Error en get_resumen_data: {e}")
        return jsonify({"error": "No se pudieron obtener los datos de resumen."}), 500

@estadisticas_bp.route("/api/ingresos-mensuales")
def get_ingresos_mensuales():
    """
    Retorna los ingresos de los últimos 12 meses o de un rango de fecha para un gráfico de líneas.
    """
    try:
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')

        if fecha_inicio_str and fecha_fin_str:
            start_date = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
            end_date = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

        ingresos_por_mes = {}
        current_month_date = start_date.replace(day=1)
        
        while current_month_date <= end_date:
            next_month_date = current_month_date.replace(day=28) + timedelta(days=4)
            next_month_date = next_month_date.replace(day=1) - timedelta(seconds=1)

            ingresos_ventas = db.session.query(func.sum(Venta.total)).filter(
                Venta.fecha >= current_month_date,
                Venta.fecha <= next_month_date
            ).scalar() or 0
            
            ingresos_servicios = db.session.query(
                func.sum(ServicioCliente.costo_servicio + ServicioCliente.costo_inscripcion)
            ).filter(
                ServicioCliente.fecha_inicio >= current_month_date,
                ServicioCliente.fecha_inicio <= next_month_date
            ).scalar() or 0
            
            ingresos_totales = ingresos_ventas + ingresos_servicios
            
            mes_label = current_month_date.strftime("%b/%y")
            ingresos_por_mes[mes_label] = float(f"{ingresos_totales:.2f}")

            current_month_date = next_month_date.replace(day=2) + timedelta(days=1)
            current_month_date = current_month_date.replace(day=1)

        data = {
            "labels": list(ingresos_por_mes.keys()),
            "ingresos": list(ingresos_por_mes.values())
        }
        
        return jsonify(data)
    except Exception as e:
        print(f"Error en get_ingresos_mensuales: {e}")
        return jsonify({"error": "No se pudieron obtener los datos de ingresos mensuales."}), 500

@estadisticas_bp.route("/api/distribucion-edad")
def get_distribucion_edad():
    """
    Retorna la distribución de clientes por rango de edad, con filtros de fecha.
    """
    try:
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')

        query = Cliente.query
        if fecha_inicio_str and fecha_fin_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
            query = query.filter(Cliente.fecha_registro >= fecha_inicio, Cliente.fecha_registro <= fecha_fin)

        data_edades = query.with_entities(Cliente.edad).all()
        
        edades = [edad[0] for edad in data_edades if edad[0] is not None]
        
        rangos = {
            "18-25": 0,
            "26-40": 0,
            "41-60": 0,
            "+60": 0
        }
        
        for edad in edades:
            if 18 <= edad <= 25:
                rangos["18-25"] += 1
            elif 26 <= edad <= 40:
                rangos["26-40"] += 1
            elif 41 <= edad <= 60:
                rangos["41-60"] += 1
            elif edad > 60:
                rangos["+60"] += 1

        data = {
            "labels": list(rangos.keys()),
            "data": list(rangos.values())
        }
        return jsonify(data)
    except Exception as e:
        print(f"Error en get_distribucion_edad: {e}")
        return jsonify({"error": "No se pudieron obtener los datos de distribución por edad."}), 500

@estadisticas_bp.route("/api/distribucion-servicio")
def get_distribucion_servicio():
    """
    Retorna la distribución de clientes por tipo de servicio.
    """
    try:
        distribucion = db.session.query(
            Servicio.tipo_servicio,
            func.count(ServicioCliente.id)
        ).join(ServicioCliente, Servicio.id == ServicioCliente.servicio_id).filter(
            ServicioCliente.estatus == True
        ).group_by(Servicio.tipo_servicio).all()
        
        labels = [row[0] for row in distribucion]
        data = [row[1] for row in distribucion]
        
        return jsonify({"labels": labels, "data": data})
    except Exception as e:
        print(f"Error en get_distribucion_servicio: {e}")
        return jsonify({"error": "No se pudieron obtener los datos de distribución por servicio."}), 500

@estadisticas_bp.route("/api/estatus-clientes")
def get_estatus_clientes():
    """
    Retorna la distribución de clientes por estatus (activo/inactivo).
    """
    try:
        activos = ServicioCliente.query.filter_by(estatus=True).count()
        inactivos = ServicioCliente.query.filter_by(estatus=False).count()
        
        data = {
            "labels": ["Activos", "Inactivos"],
            "data": [activos, inactivos]
        }
        return jsonify(data)
    except Exception as e:
        print(f"Error en get_estatus_clientes: {e}")
        return jsonify({"error": "No se pudieron obtener los datos de estatus de clientes."}), 500

@estadisticas_bp.route("/api/distribucion-genero")
def get_distribucion_genero():
    """
    Retorna la distribución de clientes por género.
    """
    try:
        distribucion = db.session.query(
            Cliente.sexo,
            func.count(Cliente.id)
        ).group_by(Cliente.sexo).all()

        labels = [row[0] for row in distribucion]
        data = [row[1] for row in distribucion]
        
        return jsonify({"labels": labels, "data": data})
    except Exception as e:
        print(f"Error en get_distribucion_genero: {e}")
        return jsonify({"error": "No se pudieron obtener los datos de distribución por género."}), 500