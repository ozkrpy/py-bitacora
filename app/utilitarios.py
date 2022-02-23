# LIBRERIA PARA FUNCIONES
from datetime import datetime, date
from app.models import AgrupadorGastos, GastosFijos, Movimientos, TiposMovimiento, Cargas, Tarjetas
from app.parametros import DEUDA_BASICA
from app import db as dbmodel
from sqlalchemy import func

from itertools import groupby
from operator import itemgetter

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
        "vehiculo": 'GAC GS3',
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

def referencias_vehiculo_puntual(anno):
    sum_monto_carga=0
    sum_litros_carga=0
    min_odo=dbmodel.session.query(func.min(Cargas.odometro)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    max_odo=dbmodel.session.query(func.max(Cargas.odometro)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    min_fecha_carga=dbmodel.session.query(func.min(Cargas.fecha_carga)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    max_fecha_carga=dbmodel.session.query(func.max(Cargas.fecha_carga)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    recorrido=max_odo-min_odo
    cargas = Cargas.query.filter(func.strftime("%Y", Cargas.fecha_carga)==anno).all()
    for carga in cargas:
        sum_monto_carga += carga.monto_carga
        sum_litros_carga += (carga.monto_carga/carga.precio)
    prom_litros=(sum_litros_carga/len(cargas)) # dbmodel.session.query(func.avg(Cargas.monto_carga/Cargas.precio)).scalar()
    consumo=((sum_litros_carga*100)/recorrido)
    prom_recorrido=int(recorrido/len(cargas))
    dias_ultima_carga=max_fecha_carga-min_fecha_carga
    promedio_dias_recarga = (dias_ultima_carga.days / len(cargas))
    datos_calculados={ 
        "vehiculo": 'GAC GS3',
        "anno": anno,
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
        "promedio_dias_carga": promedio_dias_recarga#dias_ultima_carga.days
    }
    return datos_calculados

def listar_tipos():
    tipos = TiposMovimiento.query.all()
    d = [(tipo.id, tipo.tipo) for tipo in tipos]
    return d#{(tipo.id, tipo.tipo) for tipo in tipos}

def listar_tarjetas():
    tipos = Tarjetas.query.all()
    d = [(tipo.id, tipo.banco) for tipo in tipos]
    return d#{(tipo.id, tipo.tipo) for tipo in tipos}

def balance_cuenta():
    balance_mes = []
    anno = datetime.now().strftime("%Y")
    movimientos = dbmodel.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), Movimientos.id_tipo_movimiento.label('tipo'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion), Movimientos.id_tipo_movimiento).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).all()
    for key,keydata in groupby(movimientos, key=itemgetter(0)):
        sumatoria_mes = 0
        for data in keydata:
            if data.tipo == 10:
                sumatoria_mes -= data.total
            else:
                sumatoria_mes += data.total
        item = (key, sumatoria_mes)
        balance_mes.append(item)
    sum_deudas = dbmodel.session.query(func.sum(Movimientos.monto_operacion)).filter(Movimientos.id_tipo_movimiento!=10).scalar()
    sum_pagos = dbmodel.session.query(func.sum(Movimientos.monto_operacion)).filter(Movimientos.id_tipo_movimiento==10).scalar()
    sum_montos = sum_deudas - sum_pagos
    return sum_montos, balance_mes

def balance_cuenta_puntual(movimientos):
    sum_montos = 0
    for movimiento in movimientos:
        if movimiento.id_tipo_movimiento == 10:
            sum_montos -= movimiento.monto_operacion
        else:
            sum_montos += movimiento.monto_operacion
    return sum_montos

def listar_agrupador():
    grupos = AgrupadorGastos.query.all()
    d = [(grupo.id, grupo.agrupador) for grupo in grupos]
    return d

def precarga_deudas(mes: str):
    fecha_generacion = datetime.strptime(mes, '%Y-%m')
    g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='CASA', monto=DEUDA_BASICA['CASA'], operacion=False, pagado=False, id_agrupador_gastos=2)
    dbmodel.session.add(g)
    dbmodel.session.commit()
    g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='CHECHY', monto=DEUDA_BASICA['CHECHY'], operacion=False, pagado=False, id_agrupador_gastos=2)
    dbmodel.session.add(g)
    dbmodel.session.commit()
    g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='SEGURO_AUTO', monto=DEUDA_BASICA['SEGURO_AUTO'], operacion=False, pagado=False, id_agrupador_gastos=3)
    dbmodel.session.add(g)
    dbmodel.session.commit()
    g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='CONTADORA', monto=DEUDA_BASICA['CONTADORA'], operacion=False, pagado=False, id_agrupador_gastos=1)
    dbmodel.session.add(g)
    dbmodel.session.commit()
    # g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='PAGO_TARJETA', monto=DEUDA_BASICA['PAGO_TARJETA'], operacion=False, pagado=False, id_agrupador_gastos=3)
    # dbmodel.session.add(g)
    # dbmodel.session.commit()
    # g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='COMBUSTIBLE', monto=DEUDA_BASICA['COMBUSTIBLE'], operacion=False, pagado=False, id_agrupador_gastos=3)
    # dbmodel.session.add(g)
    # dbmodel.session.commit()
    # g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion='SUPERMERCADO', monto=DEUDA_BASICA['SUPERMERCADO'], operacion=False, pagado=False, id_agrupador_gastos=3)
    # dbmodel.session.add(g)
    # dbmodel.session.commit()
    return True

def deuda_total(deudas):
    saldo = 0
    for deuda in deudas:
        if deuda.pagado:
            if not deuda.operacion:
                saldo += deuda.monto
            else:
                saldo -= deuda.monto
    return saldo

def saldo_grupo(result):
    list_dict = []
    saldo = 0
    for i in result:
        i_dict = i._asdict()  # sqlalchemy.util._collections.result , has a method called _asdict()
        list_dict.append(i_dict)
    for item in list_dict:
        if item['acreedor']=='CREDITO':
            saldo -= item['total']
        else:
            saldo += item['total']
    return saldo

def movimientos_tarjeta(id, mes=0):
    if mes==0:
        return dbmodel.session.query(Movimientos).filter(Movimientos.id_tarjeta==id).order_by(Movimientos.fecha_operacion).all()
    return dbmodel.session.query(Movimientos).filter(Movimientos.id_tarjeta==id).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).order_by(Movimientos.fecha_operacion).all()