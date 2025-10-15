# GYM_App/modules/mensajes_masivos/forms.py
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, Length

class EnvioMasivoForm(FlaskForm):
    """Formulario para seleccionar el filtro y componer el mensaje masivo."""

    opciones_destinatario = [
        ('todos', 'Todos los Clientes (Histórico)'),
        ('activos', 'Clientes con Membresía Activa'),
        ('inactivos', 'Clientes con Membresía Vencida'),
        ('hombres', 'Solo Hombres'),
        ('mujeres', 'Solo Mujeres'),
        ('especifico', 'Cliente Específico (por ID/Email)'),
    ]
    
    # Campo de selección
    destinatario = SelectField(
        'Enviar a:',
        choices=opciones_destinatario,
        validators=[DataRequired()],
        default='todos'
    )
    
    # Campo para la búsqueda específica (opcional, solo si se elige 'especifico')
    cliente_especifico = StringField(
        'ID o Email del Cliente Específico (Opcional)',
        validators=[Length(max=120)]
    )

    # Contenido del Correo
    asunto = StringField(
        'Asunto del Correo',
        validators=[DataRequired(), Length(max=150)]
    )
    
    cuerpo = TextAreaField(
        'Cuerpo del Mensaje',
        validators=[DataRequired(), Length(min=10, max=5000)]
    )
    
    submit = SubmitField('Enviar Correos Masivos')