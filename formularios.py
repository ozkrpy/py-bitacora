from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.fields.core import IntegerField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField
from utilitarios import listar_tipos
#from models import TiposMovimiento


class FormularioCombustible(FlaskForm):
    fecha_registro = StringField()
    fecha_carga = DateField('DatePicker', format='%Y-%m-%d')
    odometro = IntegerField('Odometro', validators={DataRequired()})
    emblema = StringField('Estacion', validators={DataRequired()})
    precio = IntegerField('Precio', validators={DataRequired()})
    monto = IntegerField('Monto', validators={DataRequired()})
    submit = SubmitField('Confirmar')

class FormularioMovimientos(FlaskForm):
    fecha_registro = StringField()
    fecha_operacion = DateField('DatePicker', format='%Y-%m-%d')
    descripcion = StringField('Descripcion', validators={DataRequired()})
    monto_operacion = IntegerField('Monto', validators={DataRequired()})
    tipo_operacion = SelectField('Tipo', choices=listar_tipos(), coerce=int)
    tipo_operacion_view = StringField()
    submit = SubmitField('Confirmar')
