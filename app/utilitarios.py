# LIBRERIA PARA FUNCIONES
from datetime import datetime, date
from app.models import AgrupadorGastos, GastosFijos, Movimientos, TiposMovimiento, Cargas, Tarjetas, DeudasPendientes
# from app.parametros import DEUDA_BASICA
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
    prom_litros=0
    consumo=0
    prom_recorrido=0
    promedio_dias_recarga=0
    min_odo=dbmodel.session.query(func.min(Cargas.odometro)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    max_odo=dbmodel.session.query(func.max(Cargas.odometro)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    min_fecha_carga=dbmodel.session.query(func.min(Cargas.fecha_carga)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    max_fecha_carga=dbmodel.session.query(func.max(Cargas.fecha_carga)).filter(func.strftime("%Y", Cargas.fecha_carga)==anno).scalar()
    recorrido=max_odo-min_odo
    cargas = Cargas.query.filter(func.strftime("%Y", Cargas.fecha_carga)==anno).all()
    if len(cargas) > 1:
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
    tipos = Tarjetas.query.filter(Tarjetas.estado==True).all()
    d = [(tipo.id, tipo.banco) for tipo in tipos]
    return d#{(tipo.id, tipo.tipo) for tipo in tipos}

def balance_cuenta():
    balance_mes = []
    anno = datetime.now().strftime("%Y")
    movimientos = dbmodel.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), Movimientos.id_tipo_movimiento.label('tipo'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion), Movimientos.id_tipo_movimiento).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).all()
    for key,keydata in groupby(movimientos, key=itemgetter(0)):
        sumatoria_mes = 0
        for data in keydata:
            if data.tipo == 10 or data.tipo == 18:
                sumatoria_mes -= data.total
            else:
                sumatoria_mes += data.total
        item = (key, sumatoria_mes)
        balance_mes.append(item)
    sum_deudas = dbmodel.session.query(func.sum(Movimientos.monto_operacion)).filter((Movimientos.id_tipo_movimiento!=10)&(Movimientos.id_tipo_movimiento!=18)).scalar()
    sum_pagos = dbmodel.session.query(func.sum(Movimientos.monto_operacion)).filter((Movimientos.id_tipo_movimiento==10)|(Movimientos.id_tipo_movimiento==18)).scalar()
    sum_montos = sum_deudas - sum_pagos
    return sum_montos, balance_mes

def balance_cuenta_puntual(movimientos):
    sum_montos = 0
    for movimiento in movimientos:
        if movimiento.id_tipo_movimiento == 10 or movimiento.id_tipo_movimiento == 18:
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
    deudas = dbmodel.session.query(DeudasPendientes).filter(DeudasPendientes.estado==True).all()
    for deuda in deudas:
        descontado=False
        if deuda.descripcion=='DESCUENTO IPS' or deuda.descripcion=='SERVICIOS TELEFONIA' or deuda.descripcion=='INTERNET & TV' or deuda.descripcion=='REFERENCIA': 
            descontado=True
        g = GastosFijos(date=datetime.utcnow(), fecha_pagar=fecha_generacion, descripcion=deuda.descripcion, monto=deuda.monto, operacion=False, pagado=descontado, id_agrupador_gastos=deuda.id_agrupador)
        dbmodel.session.add(g)
        dbmodel.session.commit()
    return True

def deuda_total(deudas):
    saldo = 0
    for deuda in deudas:
        # if deuda.pagado:
        if deuda.pagado and deuda.descripcion!='REFERENCIA':
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

def calcular_disponibilidad(mes: str):
    # credito = dbmodel.session.query(func.sum(GastosFijos.monto).label('credito')).join(AgrupadorGastos).filter(AgrupadorGastos.agrupador=='CREDITO').filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==mes).scalar() 
    credito = dbmodel.session.query(func.sum(GastosFijos.monto).label('credito')).join(AgrupadorGastos).filter(AgrupadorGastos.agrupador=='CREDITO').filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==mes).filter(GastosFijos.pagado==True).scalar() 
    deudas_impagas = dbmodel.session.query(func.sum(GastosFijos.monto).label('pendientes')).join(AgrupadorGastos).filter(AgrupadorGastos.agrupador!='CREDITO').filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==mes).filter(GastosFijos.pagado==False).scalar()
    deudas_pagadas = dbmodel.session.query(func.sum(GastosFijos.monto).label('pagados')).join(AgrupadorGastos).filter(AgrupadorGastos.agrupador!='CREDITO').filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==mes).filter(GastosFijos.pagado==True).scalar() 
    if credito is None: credito = 0
    if deudas_impagas is None: deudas_impagas = 0
    if deudas_pagadas is None: deudas_pagadas = 0
    return credito, deudas_impagas, deudas_pagadas

def movimientos_agrupados(mes):
    operaciones=[]
    # movimientos = dbmodel.session.query(Movimientos.id.label('id_operacion'), Movimientos.fecha_operacion.label('fecha_operacion'), Movimientos.descripcion.label('descripcion'), Movimientos.monto_operacion.label('monto_operacion'), Movimientos.id_tipo_movimiento.label('id_tipo_movimiento'), TiposMovimiento.tipo.label('tipo_movimiento'), Movimientos.id_tarjeta.label('id_tarjeta'), Tarjetas.banco.label('banco')).join(Tarjetas).join(TiposMovimiento).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tipo_movimiento==TiposMovimiento.id).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).order_by(Movimientos.id_tarjeta).order_by(Movimientos.fecha_operacion).all()
    for movimiento in dbmodel.session.query(Movimientos.id.label('id_operacion'), Movimientos.fecha_operacion.label('fecha_operacion'), Movimientos.descripcion.label('descripcion'), Movimientos.monto_operacion.label('monto_operacion'), Movimientos.id_tipo_movimiento.label('id_tipo_movimiento'), TiposMovimiento.tipo.label('tipo_movimiento'), Movimientos.id_tarjeta.label('id_tarjeta'), Tarjetas.banco.label('banco')).join(Tarjetas).join(TiposMovimiento).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tipo_movimiento==TiposMovimiento.id).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).order_by(Movimientos.id_tarjeta).order_by(Movimientos.fecha_operacion).all():
        operaciones.append({'id_operacion':movimiento.id_operacion, 'fecha_operacion': movimiento.fecha_operacion, 'descripcion': movimiento.descripcion, 'monto_operacion': movimiento.monto_operacion, 'id_tipo_movimiento': movimiento.id_tipo_movimiento, 'tipo_movimiento': movimiento.tipo_movimiento, 'id_tarjeta': movimiento.id_tarjeta, 'banco': movimiento.banco})
    return operaciones

def balance_puntual_tarjeta(id):
    compras = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==id).filter(Movimientos.id_tipo_movimiento.notin_([10, 18])).scalar()
    pagos   = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==id).filter(Movimientos.id_tipo_movimiento.in_([10])).scalar()
    descuentos   = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==id).filter(Movimientos.id_tipo_movimiento.in_([18])).scalar()
    intereses   = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==id).filter(Movimientos.id_tipo_movimiento.in_([7])).scalar()
    if compras is None: compras = 0
    if pagos is None: pagos = 0
    if descuentos is None: descuentos = 0
    if intereses is None: intereses = 0
    return compras, pagos, descuentos, intereses

def saldos_mes_tarjeta(mes):
    balances=[]
    for tarjeta in dbmodel.session.query(Movimientos.id_tarjeta).distinct().filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).all():
        banco =  dbmodel.session.query(Tarjetas.banco).filter(Tarjetas.id==tarjeta.id_tarjeta).scalar()
        compras_mes = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==tarjeta.id_tarjeta).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).filter(Movimientos.id_tipo_movimiento.notin_([10, 18])).scalar()
        pagos_mes   = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==tarjeta.id_tarjeta).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).filter(Movimientos.id_tipo_movimiento.in_([10])).scalar()
        descuentos_mes = dbmodel.session.query(func.sum(Movimientos.monto_operacion).label('saldo')).join(Tarjetas).filter(Movimientos.id_tarjeta==Tarjetas.id).filter(Movimientos.id_tarjeta==tarjeta.id_tarjeta).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).filter(Movimientos.id_tipo_movimiento.in_([18])).scalar()
        compras, pagos, descuentos, intereses = balance_puntual_tarjeta(tarjeta.id_tarjeta)
        if compras_mes is None: compras_mes = 0
        if pagos_mes is None: pagos_mes = 0
        if descuentos_mes is None: descuentos_mes = 0
        balances.append({'banco': banco, 'compras_mes': compras_mes, 'pagos_mes': pagos_mes, 'descuentos_mes': descuentos_mes, 'balance_mes': compras_mes-pagos_mes-descuentos_mes, 'compras': compras, 'pagos': pagos, 'balance': compras-pagos-descuentos})
    return balances


def balances_tarjetas():
    saldos=[]
    for tarjeta in dbmodel.session.query(Tarjetas).filter(Tarjetas.estado==True).all():
        compras, pagos, descuentos, intereses = balance_puntual_tarjeta(tarjeta.id)
        saldos.append({'banco': tarjeta.banco, 'compras': compras, 'pagos': pagos, 'descuentos': descuentos, 'balance': compras-pagos-descuentos})
    return saldos

def resumenes_tarjeta_macro():
    estados = []
    for tarjeta in Tarjetas.query.all():
        compras, pagos, descuentos, intereses = balance_puntual_tarjeta(tarjeta.id)
        if compras != 0:
            porcentaje_descuento = int((descuentos * 100) / compras)
        else: 
            porcentaje_descuento = 0
        estados.append({'id':tarjeta.id, 'banco': tarjeta.banco, 'numero': tarjeta.numero, 'vencimiento': tarjeta.vencimiento, 'estado': tarjeta.estado, 'compras': compras, 'pagos': pagos, 'descuentos': descuentos, 'intereses': intereses, 'porcentaje': porcentaje_descuento})
    return estados