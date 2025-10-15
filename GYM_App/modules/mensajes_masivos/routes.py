# GYM_App/modules/mensajes_masivos/routes.py (COMPLETO)
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app 
from flask_login import login_required, current_user # Importar current_user
from flask_mail import Message
from smtplib import SMTPRecipientsRefused, SMTPServerDisconnected, SMTPAuthenticationError
from socket import gaierror, error as socket_error

from GYM_App.extensions import db, mail
# Importamos el nuevo modelo de MensajeMasivo y Usuario (asumo que está en models.py)
from GYM_App.models import Cliente, ServicioCliente, MensajeMasivo, Usuario 
from .forms import EnvioMasivoForm
from datetime import datetime
from sqlalchemy import distinct 

mensajes_bp = Blueprint("mensajes", __name__, template_folder="../../templates/mensajes_masivos")


def get_recipient_emails(filtro, valor_especifico=None):
    """
    Filtra la base de datos para obtener la lista de correos electrónicos 
    basándose en el criterio de selección.
    """
    
    # Base query: Obtener todos los clientes con email no nulo.
    clientes_query = db.session.query(Cliente.email, Cliente.id).filter(Cliente.email.isnot(None))
    
    # Aplicar filtros según la selección (Lógica sin cambios)
    if filtro == 'todos':
        pass
    # ... (código de filtrado de clientes omitido por brevedad, es el mismo de antes) ...
    elif filtro == 'hombres':
        clientes_query = clientes_query.filter(Cliente.sexo == 'Masculino')
        
    elif filtro == 'mujeres':
        clientes_query = clientes_query.filter(Cliente.sexo == 'Femenino')
        
    elif filtro == 'especifico' and valor_especifico:
        try:
            cliente_id = int(valor_especifico)
            clientes_query = clientes_query.filter(Cliente.id == cliente_id)
        except ValueError:
            clientes_query = clientes_query.filter(Cliente.email == valor_especifico)
    
    elif filtro == 'activos' or filtro == 'inactivos':
        hoy = datetime.now()
        
        clientes_activos_ids = db.session.query(
            ServicioCliente.cliente_id
        ).filter(
            ServicioCliente.fecha_fin >= hoy,
            ServicioCliente.estatus == True
        ).distinct().subquery()
        
        if filtro == 'activos':
            clientes_query = clientes_query.filter(Cliente.id.in_(clientes_activos_ids))
        else:
            clientes_query = clientes_query.filter(Cliente.id.notin_(clientes_activos_ids))
            
    # Extraer solo los correos electrónicos únicos
    emails = [email for email, id in clientes_query.distinct().all() if email]
    
    return emails


@mensajes_bp.route("/historial")
@login_required 
def historial_mensajes():
    """Muestra el listado de mensajes masivos enviados."""
    
    # Paginación (opcional, pero recomendable para historiales largos)
    page = request.args.get('page', 1, type=int)
    
    # Consulta: ordenar por fecha de envío descendente
    mensajes = MensajeMasivo.query.order_by(MensajeMasivo.fecha_envio.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template("historial_mensajes.html", mensajes=mensajes)


@mensajes_bp.route("/enviar", methods=["GET", "POST"])
@login_required 
def enviar_mensaje_masivo():
        
    form = EnvioMasivoForm()
    
    if form.validate_on_submit():
        destinatario = form.destinatario.data
        valor_especifico = form.cliente_especifico.data.strip()
        asunto = form.asunto.data
        cuerpo = form.cuerpo.data
        
        # 1. Obtener la lista de correos
        recipient_emails = get_recipient_emails(destinatario, valor_especifico)
        
        if not recipient_emails:
            flash(f"No se encontraron clientes para el criterio '{destinatario}'. No se realizó ningún envío.", "warning")
            return redirect(url_for('mensajes.enviar_mensaje_masivo'))
        
        flash("⏳ Iniciando envío masivo de correos. Esto puede tardar algunos segundos o minutos. Por favor, espere hasta el mensaje de confirmación.", "info")
        
        # 2. Configurar y enviar los mensajes
        total_enviados = 0
        
        try:
            with mail.connect() as conn:
                sender_email = current_app.config['MAIL_USERNAME']
                
                for email in recipient_emails:
                    msg = Message(
                        subject=asunto,
                        recipients=[email],
                        body=cuerpo,
                        sender=sender_email
                    )
                    conn.send(msg)
                    total_enviados += 1
            
            # 3. REGISTRAR EN EL HISTORIAL TRAS ÉXITO
            nuevo_registro = MensajeMasivo(
                asunto=asunto,
                cuerpo_resumen=cuerpo[:300] + ('...' if len(cuerpo) > 300 else ''),
                destinatario_filtro=destinatario,
                total_enviados=total_enviados,
                usuario_id=current_user.id
            )
            db.session.add(nuevo_registro)
            db.session.commit()
            
            # MENSAJE DE ÉXITO FINAL
            flash(f"✅ ¡Proceso finalizado! Mensaje enviado exitosamente a {total_enviados} destinatario(s).", "success")
            return redirect(url_for('mensajes.historial_mensajes')) # Redirigir al historial

        # Manejo de Errores Específicos (Conexión, Credenciales, Servidor)
        except (gaierror, socket_error, SMTPServerDisconnected):
            flash("❌ **ERROR DE CONEXIÓN A INTERNET/SERVIDOR SMTP:** No se pudo alcanzar el servidor de correo. Por favor, verifica tu conexión a internet.", "danger")
        
        except SMTPAuthenticationError:
            flash("❌ **ERROR DE AUTENTICACIÓN:** Las credenciales del correo (MAIL_USERNAME o MAIL_PASSWORD) son incorrectas o la seguridad de la aplicación está bloqueando el acceso.", "danger")

        except Exception as e:
            if total_enviados > 0:
                 flash(f"⚠️ Error parcial al enviar. Se enviaron {total_enviados} correos antes del fallo. **Error Técnico:** {str(e)}", "warning")
            else:
                 flash(f"❌ Error al enviar los correos (0 enviados). **Error Técnico Genérico:** {str(e)}.", "danger")

            db.session.rollback() # Asegurar que no se guarde nada si falló a medias

    return render_template("envio_masivo.html", form=form)