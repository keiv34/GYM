from flask import Blueprint, render_template, request, jsonify, url_for, current_app, send_file
from GYM_App.extensions import db, mail
from GYM_App.models import Cliente, Servicio, ServicioCliente
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask_mail import Message
import qrcode
import os
import io
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

pagos_bp = Blueprint("pagos", __name__, template_folder="../../templates/pagos")


# --- GENERAR PDF TICKET ---
def generate_ticket_pdf(pago):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(80 * 2.83465, 200 * 2.83465))
    c.setFont('Helvetica-Bold', 12)
    c.drawString(10, 550, "GYM")
    c.setFont('Helvetica', 8)
    c.drawString(10, 535, "RECIBO DE PAGO")
    
    y = 510
    c.drawString(10, y, f"ID RECIBO: {pago.id}")
    y -= 15
    c.drawString(10, y, f"EMISIÓN: {pago.fecha_inicio.strftime('%d %b %Y %H:%M')}")
    
    y -= 25
    c.drawString(10, y, "--- DETALLES ---")
    y -= 15
    c.drawString(10, y, f"CLIENTE: {pago.cliente.nombre}")
    y -= 15
    c.drawString(10, y, f"ID CLIENTE: #{pago.cliente.id}")
    y -= 15
    c.drawString(10, y, f"SERVICIO: {pago.servicio.nombre}")
    y -= 15
    c.drawString(10, y, f"INICIO: {pago.fecha_inicio.strftime('%d-%m-%Y')}")
    y -= 15
    c.drawString(10, y, f"FIN: {pago.fecha_fin.strftime('%d-%m-%Y') if pago.fecha_fin else 'No aplica'}")
    
    y -= 25
    c.drawString(10, y, "--- COSTOS ---")
    y -= 15
    c.drawString(10, y, f"COSTO SERVICIO: ${pago.costo_servicio:.2f}")
    y -= 15
    c.drawString(10, y, f"COSTO INSCRIPCIÓN: ${pago.costo_inscripcion:.2f}")
    y -= 25
    c.setFont('Helvetica-Bold', 10)
    total = pago.costo_servicio + (pago.costo_inscripcion if pago.costo_inscripcion else 0)
    c.drawString(10, y, f"TOTAL: ${total:.2f}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# --- GENERAR PDF CREDENCIAL ---
def generate_credential_pdf(cliente, qr_image_path):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(350, 220), topMargin=10, bottomMargin=10, leftMargin=10, rightMargin=10)
    styles = getSampleStyleSheet()
    story = []
    styles['Normal'].alignment = 1
    story.append(Paragraph("<b>GYM</b>", styles['Normal']))
    story.append(Spacer(1, 10))
    
    # Foto de perfil
    if cliente.foto_perfil and os.path.exists(os.path.join(current_app.root_path, 'static', cliente.foto_perfil)):
        foto_path = os.path.join(current_app.root_path, 'static', cliente.foto_perfil)
    else:
        foto_path = os.path.join(current_app.root_path, 'static', 'uploads', 'default_profile.png')
    
    foto = Image(foto_path, width=80, height=80)
    qr = Image(qr_image_path, width=80, height=80)
    
    info = [
        [Paragraph(f"<b>Nombre:</b> {cliente.nombre}", styles['Normal'])],
        [Paragraph(f"<b>ID Cliente:</b> #{cliente.id}", styles['Normal'])],
        [Paragraph(f"<b>Teléfono:</b> {cliente.telefono}", styles['Normal'])],
        [Paragraph(f"<b>Fecha de Ingreso:</b> {cliente.fecha_registro.strftime('%d-%m-%Y')}", styles['Normal'])],
    ]
    info_table = Table(info)
    info_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 1)]))
    
    main_table = Table([[foto, info_table, qr]], colWidths=[90, 150, 90])
    main_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (0,0), 'CENTER'), ('ALIGN', (2,0), (2,0), 'CENTER')]))
    story.append(main_table)
    doc.build(story)
    buffer.seek(0)
    return buffer


# --- PROCESAR PAGO ---
@pagos_bp.route("/procesar", methods=["GET", "POST"])
def procesar_pago():
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        servicio_id = request.form.get("servicio_id")
        inscripcion_monto_str = request.form.get("inscripcion_monto")

        if not cliente_id or not servicio_id:
            return jsonify({'success': False, 'message': "Debe seleccionar un cliente y un servicio."})

        try:
            inscripcion_monto = float(inscripcion_monto_str) if inscripcion_monto_str else 0.0
        except ValueError:
            return jsonify({'success': False, 'message': "El monto de inscripción no es un número válido."})
        
        cliente = Cliente.query.get_or_404(cliente_id)
        servicio = Servicio.query.get_or_404(servicio_id)

        ultima_membresia = ServicioCliente.query.filter_by(cliente_id=cliente.id).order_by(ServicioCliente.fecha_fin.desc()).first()
        if ultima_membresia and ultima_membresia.fecha_fin and ultima_membresia.fecha_fin > datetime.utcnow():
            fecha_inicio = ultima_membresia.fecha_fin + timedelta(days=1)
        else:
            fecha_inicio = datetime.utcnow()

        fecha_fin = None
        if servicio.tipo_servicio == 'diaria':
            fecha_fin = fecha_inicio + timedelta(days=1)
        elif servicio.tipo_servicio == 'semanal':
            fecha_fin = fecha_inicio + timedelta(weeks=1)
        elif servicio.tipo_servicio == 'quincenal':
            fecha_fin = fecha_inicio + timedelta(days=15)
        elif servicio.tipo_servicio == 'mensual':
            fecha_fin = fecha_inicio + relativedelta(months=1)
        elif servicio.tipo_servicio == 'bimestral':
            fecha_fin = fecha_inicio + relativedelta(months=2)
        elif servicio.tipo_servicio == 'trimestral':
            fecha_fin = fecha_inicio + relativedelta(months=3)
        elif servicio.tipo_servicio == 'cuatrimestral':
            fecha_fin = fecha_inicio + relativedelta(months=4)
        elif servicio.tipo_servicio == 'semestral':
            fecha_fin = fecha_inicio + relativedelta(months=6)
        elif servicio.tipo_servicio == 'anual':
            fecha_fin = fecha_inicio + relativedelta(years=1)
        elif servicio.tipo_servicio == 'bienal':
            fecha_fin = fecha_inicio + relativedelta(years=2)

        # Desactivar membresías anteriores
        membresias_anteriores = ServicioCliente.query.filter_by(cliente_id=cliente.id, estatus=True).all()
        for membresia in membresias_anteriores:
            membresia.estatus = False

        nueva_membresia = ServicioCliente(
            cliente_id=cliente.id,
            servicio_id=servicio.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estatus=True,
            costo_servicio=servicio.costo,
            costo_inscripcion=inscripcion_monto,
            metodo_pago='Efectivo'
        )
        
        
        db.session.add(nueva_membresia)
        db.session.commit()

        try:
            ticket_buffer = generate_ticket_pdf(nueva_membresia)

            # Generar credencial si es primera membresía
            credencial_buffer = None
            if ServicioCliente.query.filter_by(cliente_id=cliente.id).count() == 1:
                qr_data = str(cliente.id)
                qr_img = qrcode.make(qr_data)
                qr_dir = os.path.join(current_app.root_path, 'static', 'qrcodes')
                os.makedirs(qr_dir, exist_ok=True)
                qr_path = os.path.join(qr_dir, f'qr_{cliente.id}.png')
                qr_img.save(qr_path)
                credencial_buffer = generate_credential_pdf(cliente, qr_path)

            # Enviar correo
            msg = Message(
                "Confirmación de Pago",
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[cliente.email]
            )
            msg.body = f"Hola {cliente.nombre},\nTu pago ha sido registrado correctamente.\nServicio: {servicio.nombre}"
            msg.attach("recibo_pago.pdf", "application/pdf", ticket_buffer.getvalue())
            if credencial_buffer:
                msg.attach("credencial_membresia.pdf", "application/pdf", credencial_buffer.getvalue())
            mail.send(msg)

            response = {
                'success': True,
                'message': "Pago procesado correctamente.",
                'ticket_url': url_for('pagos.generar_ticket', pago_id=nueva_membresia.id)
            }
            if credencial_buffer:
                response['credencial_url'] = url_for('pagos.generar_credencial', cliente_id=cliente.id)

            return jsonify(response)
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f"Error al procesar el pago: {str(e)}"})

    # --- LISTAR PAGOS ORDENADOS ---
    servicios = Servicio.query.all()
    pagos = ServicioCliente.query.order_by(ServicioCliente.id.desc()).all()  # 🔹 más recientes primero
    return render_template("procesar_pago.html", servicios=servicios, pagos=pagos)


# --- BUSCAR CLIENTES PARA AUTOCOMPLETE ---
@pagos_bp.route('/api/clientes')
def buscar_clientes():
    query = request.args.get('q', '')
    clientes = Cliente.query.filter(
        (Cliente.nombre.ilike(f'%{query}%')) |
        (Cliente.id.ilike(f'{query}')) |
        (Cliente.email.ilike(f'%{query}%'))
    ).all()
    resultados = [{'id': c.id, 'label': f"{c.nombre} ({c.email})", 'value': c.nombre} for c in clientes]
    return jsonify(resultados)


# --- GENERAR TICKET PDF ---
@pagos_bp.route("/ticket/<int:pago_id>")
def generar_ticket(pago_id):
    pago = ServicioCliente.query.get_or_404(pago_id)
    buffer = generate_ticket_pdf(pago)
    return send_file(buffer, as_attachment=False, download_name=f"recibo_{pago.id}.pdf", mimetype="application/pdf")


# --- GENERAR CREDENCIAL PDF ---
@pagos_bp.route("/credencial/<int:cliente_id>")
def generar_credencial(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    qr_path = os.path.join(current_app.root_path, 'static', 'qrcodes', f'qr_{cliente.id}.png')
    buffer = generate_credential_pdf(cliente, qr_path)
    return send_file(buffer, as_attachment=False, download_name=f"credencial_{cliente.id}.pdf", mimetype="application/pdf")


# --- VER DETALLES DEL PAGO ---
@pagos_bp.route("/detalles/<int:pago_id>")
def ver_detalles_pago(pago_id):
    pago = ServicioCliente.query.get_or_404(pago_id)
    return render_template("detalles_pago.html", pago=pago)
