# LIBRERIA PARA FUNCIONES
from datetime import datetime, date
from models import Movimientos, TiposMovimiento, db as dbmodel, Cargas
from sqlalchemy import func
from parametros import LIMITE_CREDITO_TJ

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
    return datos_calculados

def listar_tipos():
    tipos = TiposMovimiento.query.all()
    d = [(tipo.id, tipo.tipo) for tipo in tipos]
    return d#{(tipo.id, tipo.tipo) for tipo in tipos}

def balance_cuenta():
    sum_montos = dbmodel.session.query(func.sum(Movimientos.monto_operacion)).scalar()
    #balance = LIMITE_CREDITO_TJ - sum_montos
    return sum_montos 

def balance_cuenta_puntual(movimientos):
    sum_montos = 0
    for movimiento in movimientos:
        sum_montos += movimiento.monto_operacion
    return sum_montos