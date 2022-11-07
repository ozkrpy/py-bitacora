from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, PasswordField, BooleanField, IntegerField
#from wtforms.fields.core import BooleanField, IntegerField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from wtforms.fields.html5 import DateField
from app.utilitarios import listar_agrupador, listar_tarjetas, listar_tipos
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class FormularioCombustible(FlaskForm):
    fecha_registro = StringField()
    fecha_carga = DateField('DatePicker', format='%Y-%m-%d', default=datetime.now())
    odometro = IntegerField('Odometro', validators={DataRequired()})
    emblema = StringField('Estacion', validators={DataRequired()})
    precio = IntegerField('Precio', validators={DataRequired()})
    monto = IntegerField('Monto', validators={DataRequired()})
    submit = SubmitField('Confirmar')

class FormularioMovimientos(FlaskForm):
    fecha_registro = StringField()
    fecha_operacion = DateField('DatePicker', format='%Y-%m-%d', default=datetime.now())
    descripcion = StringField('Descripcion', validators={DataRequired()})
    monto_operacion = IntegerField('Monto', validators={DataRequired()})
    tipo_operacion = SelectField('Tipo', choices=listar_tipos(), coerce=int)
    tipo_operacion_view = StringField()
    tarjeta = SelectField('Tarjeta', choices=listar_tarjetas(), coerce=int)
    tarjeta_view = StringField()
    submit = SubmitField('Confirmar')

class FormularioParametricos(FlaskForm):
    descripcion = StringField('Descripcion', validators={DataRequired()})
    submit = SubmitField('Confirmar')

class FormularioGastos(FlaskForm):
    fecha_pagar = DateField('DatePicker', format='%Y-%m-%d', default=datetime.now())
    descripcion = StringField('Descripcion', validators={DataRequired()})
    monto = IntegerField('Monto', validators={DataRequired()})
    agrupador = SelectField('Tipo', choices=listar_agrupador(), coerce=int)
    operacion = BooleanField('Pagado')
    pagado = BooleanField('Pagado')
    agrupador_view = StringField()
    submit = SubmitField('Confirmar')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class FormularioPendientes(FlaskForm):
    descripcion = StringField('Descripcion', validators={DataRequired()})
    monto = IntegerField('Monto', validators={DataRequired()})
    estado = BooleanField('Estado')
    cuotas = IntegerField('Cuotas')
    cuotas_pagadas = IntegerField('Cuotas Pagadas')
    tipo = SelectField('Tipo', choices=listar_agrupador(), coerce=int)
    submit = SubmitField('Confirmar')

class FormularioTarjetas(FlaskForm):
    banco = StringField('Banco', validators={DataRequired()})
    numero = StringField('Ult.Digito')
    vencimiento = StringField('Venc.', validators={DataRequired()})
    estado = BooleanField('Estado')
    submit = SubmitField('Confirmar')