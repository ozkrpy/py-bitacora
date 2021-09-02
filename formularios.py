from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.core import IntegerField
from wtforms.validators import DataRequired

class NuevaRecargaCombustible(FlaskForm):
    fecha_registro = StringField()
    fecha_carga = StringField('Fecha', validators={DataRequired()})
    odometro = IntegerField('Odometro', validators={DataRequired()})
    emblema = StringField('Estacion', validators={DataRequired()})
    precio = IntegerField('Precio', validators={DataRequired()})
    monto = IntegerField('Monto', validators={DataRequired()})
    submit = SubmitField('Confirmar')

    '''
       id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.Date, nullable=False)
        fecha_carga = db.Column(db.Date, nullable=False)
        odometro = db.Column(db.Integer)
        emblema = db.Column(db.String(100), nullable=False)
        precio = db.Column(db.Integer)
        monto_carga = db.Column(db.Integer)
    '''