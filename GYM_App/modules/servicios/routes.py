from flask import Blueprint, render_template, request, redirect, url_for, flash
from GYM_App.extensions import db
from GYM_App.models import Servicio
from datetime import datetime

servicios_bp = Blueprint("servicios", __name__, template_folder="../../templates/servicios")

@servicios_bp.route("/")
def listar_servicios():
    servicios = Servicio.query.all()
    return render_template("listado_servicios.html", servicios=servicios)

@servicios_bp.route("/crear", methods=["GET", "POST"])
def crear_servicio():
    if request.method == "POST":
        nombre = request.form["nombre"]
        tipo_servicio = request.form["tipo_servicio"]
        costo = request.form["costo"]
        
        nuevo_servicio = Servicio(
            nombre=nombre,
            tipo_servicio=tipo_servicio,
            costo=costo
        )
        db.session.add(nuevo_servicio)
        db.session.commit()
        flash("Servicio creado exitosamente.", "success")
        return redirect(url_for("servicios.listar_servicios"))
    return render_template("crear_servicio.html")

@servicios_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    if request.method == "POST":
        servicio.nombre = request.form["nombre"]
        servicio.tipo_servicio = request.form["tipo_servicio"]
        servicio.costo = request.form["costo"]
        
        db.session.commit()
        flash("Servicio actualizado exitosamente.", "success")
        return redirect(url_for("servicios.listar_servicios"))
    return render_template("editar_servicio.html", servicio=servicio)

@servicios_bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_servicio(id):
    servicio = Servicio.query.get_or_404(id)
    db.session.delete(servicio)
    db.session.commit()
    flash("Servicio eliminado exitosamente.", "success")
    return redirect(url_for("servicios.listar_servicios"))