from datetime import datetime
from main import db

class Cargas(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    fecha_carga = db.Column(db.Date, nullable=False)
    odometro = db.Column(db.Integer)
    emblema = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Integer)
    monto_carga = db.Column(db.Integer)
    
    # se va representar a si misma
    def __repr__(self):
        return f'{self.date}, {self.odometro}, {self.fecha_carga}, {self.emblema}: {self.precio}, {self.monto_carga/self.precio}'