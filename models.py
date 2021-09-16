from datetime import datetime
from main import db

class Cargas(db.Model):
    __tablename__='cargas'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    fecha_carga = db.Column(db.Date, nullable=False)
    odometro = db.Column(db.Integer)
    emblema = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Integer)
    monto_carga = db.Column(db.Integer)
    def __repr__(self):
        return f'{self.date}, {self.odometro}, {self.fecha_carga}, {self.emblema}: {self.precio}, {self.monto_carga/self.precio}'

class Movimientos(db.Model):
    __tablename__='movimientos'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    fecha_operacion = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.String(100), nullable=False)
    monto_operacion = db.Column(db.Integer)
    id_tipo_movimiento = db.Column(db.Integer, db.ForeignKey('tipos_movimiento.id'), nullable=True)
    tipo_movimiento = db.relationship('TiposMovimiento',backref='tipo_movimiento', foreign_keys=[id_tipo_movimiento])
    def __repr__(self):
        return f'{self.id}, {self.date}, {self.fecha_operacion}, {self.descripcion}, {self.monto_operacion}, {self.id_tipo_movimiento}, {self.tipo_movimiento}'

class TiposMovimiento(db.Model):
    __tablename__='tipos_movimiento'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100), nullable=False)
    def __repr__(self):
        return f'{self.id}, {self.tipo}'

class GastosFijos(db.Model):
    __tablename__='gastos_fijos'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    fecha_pagar = db.Column(db.Date, nullable=False)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Integer)
    pagado = db.Column(db.Boolean, server_default=u'False')
    id_agrupador_gastos = db.Column(db.Integer, db.ForeignKey('agrupador_gastos.id'), nullable=True)
    agrupador_gastos = db.relationship('AgrupadorGastos',backref='agrupador_gastos', foreign_keys=[id_agrupador_gastos])
    def __repr__(self):
        return f'{self.id}, {self.date}, {self.descripcion}, {self.monto}, {self.id_agrupador_gastos}, {self.agrupador_gastos}'

class AgrupadorGastos(db.Model):
    __tablename__='agrupador_gastos'
    id = db.Column(db.Integer, primary_key=True)
    agrupador = db.Column(db.String(100), nullable=False)
    def __repr__(self):
        return f'{self.id}, {self.agrupador}'
