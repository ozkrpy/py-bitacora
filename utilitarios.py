# LIBRERIA PARA FUNCIONES
from datetime import datetime, date
from models import db as dbmodel, Cargas
from sqlalchemy import func

def referencias_vehiculo(cargas):
    sum_monto_carga=0
    sum_litros_carga=0
    min_odo=dbmodel.session.query(func.min(Cargas.odometro)).scalar()
    max_odo=dbmodel.session.query(func.max(Cargas.odometro)).scalar()
    min_fecha_carga=dbmodel.session.query(func.min(Cargas.fecha_carga)).scalar()
    max_fecha_carga=dbmodel.session.query(func.max(Cargas.fecha_carga)).scalar()
    recorrido=max_odo-min_odo

    
    for carga in cargas:
        sum_monto_carga += carga.monto_carga
        sum_litros_carga += (carga.monto_carga/carga.precio)

    prom_litros=(sum_litros_carga/len(cargas)) # dbmodel.session.query(func.avg(Cargas.monto_carga/Cargas.precio)).scalar()
    consumo=((sum_litros_carga*100)/recorrido)
    prom_recorrido=int(recorrido/len(cargas))
    print(date.today(), max_fecha_carga, datetime.utcnow())
    dias_ultima_carga=date.today()-max_fecha_carga
    
    datos_calculados={ 
        "suma_total_cargas": sum_monto_carga,
        "suma_total_litros": sum_litros_carga,
        "promedio_litros_por_recarga": prom_litros,
        "odometro_inicial": min_odo,
        "odometro_ultimo": max_odo,
        "distancia_recorrida": recorrido,
        "consumo_por_100km": consumo, 
        "promedio_recorrido_por_tanque": prom_recorrido,
        "fecha_primera_carga": min_fecha_carga,
        "fecha_ultima_carga": max_fecha_carga,
        "promedio_dias_carga": dias_ultima_carga.days
    }
    
    #print(sum_monto_carga, sum_litros_carga, prom_litros, min_odo, max_odo, recorrido, consumo, prom_recorrido, min_fecha_carga, max_fecha_carga, dias_ultima_carga.days)
    return datos_calculados

#recargas = Cargas.query.all()
#print (referencias_vehiculo(recargas))