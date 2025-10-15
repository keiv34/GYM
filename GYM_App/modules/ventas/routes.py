from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from GYM_App.extensions import db
from GYM_App.models import Venta, DetalleVenta, Producto
from datetime import datetime

ventas_bp = Blueprint('ventas', __name__, template_folder="../../templates/ventas")

@ventas_bp.route('/punto-de-venta')
def punto_de_venta():
    return render_template("punto_de_venta.html")

# 🔎 Búsqueda en tiempo real
@ventas_bp.route('/buscar-producto')
def buscar_producto():
    query = request.args.get("query")
    if not query:
        return jsonify(None)

    producto = Producto.query.filter(Producto.nombre.ilike(f"%{query}%")).first()
    if not producto:
        return jsonify(None)

    return jsonify({
        "id": producto.id,
        "nombre": producto.nombre,
        "precio": float(producto.precio),
        "stock": producto.stock,
        "imagen_url": producto.imagen_url if producto.imagen_url else None
    })

@ventas_bp.route("/agregar-a-venta", methods=["POST"])
def agregar_a_venta():
    producto_id = request.form.get("producto_id")
    cantidad = int(request.form.get("cantidad"))
    producto = Producto.query.get_or_404(producto_id)

    if cantidad > producto.stock:
        flash("La cantidad solicitada supera el stock disponible.", "warning")
        return redirect(url_for("ventas.punto_de_venta"))

    if 'venta_actual' not in session:
        session['venta_actual'] = []
        session['total_venta'] = 0

    item_ya_en_venta = False
    for item in session['venta_actual']:
        if item['id'] == producto.id:
            item['cantidad'] += cantidad
            item['subtotal'] += producto.precio * cantidad
            item_ya_en_venta = True
            break
    
    if not item_ya_en_venta:
        session['venta_actual'].append({
            'id': producto.id,
            'nombre': producto.nombre,
            'cantidad': cantidad,
            'precio': producto.precio,
            'subtotal': producto.precio * cantidad
        })
    
    session['total_venta'] += producto.precio * cantidad
    session.modified = True
    return redirect(url_for("ventas.punto_de_venta"))

@ventas_bp.route("/remover-de-venta/<int:item_index>")
def remover_de_venta(item_index):
    if 'venta_actual' in session and len(session['venta_actual']) > item_index:
        item = session['venta_actual'].pop(item_index)
        session['total_venta'] -= item['subtotal']
        session.modified = True
        flash(f"{item['nombre']} removido de la venta.", "info")
    return redirect(url_for("ventas.punto_de_venta"))

@ventas_bp.route("/confirmar-venta", methods=["POST"])
def confirmar_venta():
    if 'venta_actual' not in session or not session['venta_actual']:
        flash("No hay productos en la venta para confirmar.", "danger")
        return redirect(url_for("ventas.punto_de_venta"))

    nueva_venta = Venta(fecha=datetime.now(), total=session['total_venta'])
    db.session.add(nueva_venta)
    db.session.flush()

    for item in session['venta_actual']:
        producto = Producto.query.get(item['id'])
        if producto:
            producto.stock -= item['cantidad']
            detalle = DetalleVenta(
                venta_id=nueva_venta.id,
                producto_id=producto.id,
                cantidad=item['cantidad'],
                precio_unitario=item['precio']
            )
            db.session.add(detalle)
            
    nueva_venta.metodo_pago = 'EFECTIVO'

    db.session.commit()
    session.pop('venta_actual', None)
    session.pop('total_venta', None)

    # ✅ Solo flash de éxito, sin raw JS
    flash("Venta completada exitosamente.", "success")
    return redirect(url_for("ventas.punto_de_venta", venta_id=nueva_venta.id))


@ventas_bp.route('/recibo/<int:venta_id>')
def mostrar_recibo(venta_id):
    venta = Venta.query.get(venta_id)
    if not venta:
        flash("Venta no encontrada.", "danger")
        return redirect(url_for('ventas.punto_de_venta'))
    
    detalles = [
        {'nombre': d.producto.nombre, 'cantidad': d.cantidad, 'subtotal': d.cantidad * d.precio_unitario}
        for d in venta.detalles
    ]
    return render_template('recibo.html', venta=venta, detalles=detalles)

@ventas_bp.route('/historial')
def historial_ventas():
    ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    return render_template('historial_ventas.html', ventas=ventas)
