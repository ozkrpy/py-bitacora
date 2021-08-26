from main import db
from models import db as dbmodel, Cargas

from datetime import datetime

dbmodel.create_all()

# j = Jugador(nombre='ANON', numero_camiseta='23', date=datetime.utcnow())
# dbmodel.session.add(j)
# j = Jugador(nombre='ANON', numero_camiseta='24', date=datetime.utcnow())
# dbmodel.session.add(j)
# j = Jugador(nombre='ANON', numero_camiseta='25', date=datetime.utcnow())
# dbmodel.session.add(j)
j = Cargas(date=datetime.utcnow(), 
        fecha_carga=datetime(2019, 12, 25), 
        odometro=10917,
        emblema='Petropar Aeropuerto', 
        precio=6390, 
        monto_carga=201215)
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(), 
        fecha_carga=datetime(2020, 1, 8), 
        odometro=11262,
        emblema='Petropar Nu Guazu', 
        precio=6740, 
        monto_carga=290036)
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(), 
        fecha_carga=datetime(2020, 1, 23), 
        odometro=11593,
        emblema='Petropar Aeropuerto', 
        precio=6740, 
        monto_carga=268097)
dbmodel.session.add(j)
dbmodel.session.commit()

j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=1, month=2, year=2020), odometro=11769, emblema='texto', precio=6390, monto_carga=127238) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=2, month=2, year=2020), odometro=12162, emblema='texto', precio=6540, monto_carga=213000) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=7, month=2, year=2020), odometro=12587, emblema='texto', precio=6270, monto_carga=230000) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=9, month=2, year=2020), odometro=13019, emblema='texto', precio=6390, monto_carga=220136) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=21, month=2, year=2020), odometro=13364, emblema='texto', precio=6390, monto_carga=258297) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=29, month=2, year=2020), odometro=13634, emblema='texto', precio=6390, monto_carga=214883) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=3, month=4, year=2020), odometro=13927, emblema='texto', precio=6390, monto_carga=235000) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=13, month=6, year=2020), odometro=14189, emblema='texto', precio=6040, monto_carga=210029) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=26, month=7, year=2020), odometro=14576, emblema='texto', precio=6040, monto_carga=270000) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=2, month=9, year=2020), odometro=14994, emblema='texto', precio=6040, monto_carga=247888) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=18, month=10, year=2020), odometro=15389, emblema='texto', precio=6040, monto_carga=275007) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=29, month=11, year=2020), odometro=15784, emblema='texto', precio=6040, monto_carga=250000) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=25, month=12, year=2020), odometro=16104, emblema='texto', precio=6040, monto_carga=234497) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=31, month=1, year=2021), odometro=16443, emblema='texto', precio=5790, monto_carga=228080) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=5, month=3, year=2021), odometro=16832, emblema='texto', precio=6440, monto_carga=260498) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=6, month=4, year=2021), odometro=17133, emblema='texto', precio=6440, monto_carga=257793) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=23, month=5, year=2021), odometro=17496, emblema='texto', precio=6440, monto_carga=256125) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=4, month=7, year=2021), odometro=17886, emblema='texto', precio=6820, monto_carga=260176) 
dbmodel.session.add(j)
dbmodel.session.commit()
j = Cargas(date=datetime.utcnow(),fecha_carga=datetime(day=8, month=8, year=2021), odometro=18292, emblema='texto', precio=7220, monto_carga=342569) 
dbmodel.session.add(j)
dbmodel.session.commit()

print(Cargas.query.all())
