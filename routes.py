from main import app, db
from flask import render_template, redirect, url_for, flash, get_flashed_messages, request
from sqlalchemy import func
from formularios import FormularioGastos, FormularioMovimientos, FormularioCombustible, FormularioParametricos
from models import AgrupadorGastos, GastosFijos, db as dbmodel, Cargas, Movimientos, TiposMovimiento
from datetime import date, datetime, timedelta
from utilitarios import balance_cuenta, referencias_vehiculo, balance_cuenta_puntual, precarga_deudas, deuda_total, saldos_grupo
from parametros import SALARIO_NETO

@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = FormularioCombustible()
    cargas = Cargas.query.all()
    anno = datetime.now().strftime("%Y")
    fechas_referencia = {'mes_anterior':datetime.now() - timedelta(days=29), 'fecha_actual':datetime.now(),  'mes_siguiente':datetime.now() + timedelta(days=29)}
    referencias_principales = referencias_vehiculo(cargas)
    movimientos = dbmodel.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion)).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).all()
    balance_movimientos = balance_cuenta()
    gastos = dbmodel.session.query(AgrupadorGastos.agrupador.label('acreedor'), func.sum(GastosFijos.monto).label('total')).join(AgrupadorGastos).group_by(AgrupadorGastos.agrupador).filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==fechas_referencia['fecha_actual'].strftime('%Y-%m')).all()
    total_gasto = saldos_grupo(gastos)
    return render_template('home.html',  form=form, **referencias_principales, movimientos=movimientos, anno=anno, fechas_referencia=fechas_referencia, balance_movimientos=balance_movimientos, gastos=gastos, total_gasto=total_gasto) #usar ** permite que se manipule la variable directamente en el DOM

@app.route('/recargas', methods=['GET', 'POST'])
def recargas():
    cargas = Cargas.query.all()
    return render_template('combustible.html', cargas=cargas)

@app.route('/nueva_recarga', methods=['GET', 'POST'])
def nueva_recarga():
    form = FormularioCombustible()
    if form.validate_on_submit():
        carga = Cargas(date=datetime.utcnow(), 
                       fecha_carga=form.fecha_carga.data,
                       odometro=form.odometro.data, 
                       emblema=form.emblema.data,
                       precio=form.precio.data,
                       monto_carga=form.monto.data
                      )
        db.session.add(carga)
        db.session.commit()
        flash('Nueva recarga agregada con exito.') #esta bueno
        return redirect(url_for('index'))
    return render_template('recarga.html', form=form)

@app.route('/modificar_recarga/<int:recarga_id>', methods=['GET', 'POST'])
def modificar_recarga(recarga_id):
    recarga = Cargas.query.get(recarga_id)
    form = FormularioCombustible()
    if recarga:
        if form.validate_on_submit():
            recarga.fecha_carga = form.fecha_carga.data # hay que preparar un datepicker
            recarga.odometro = form.odometro.data
            recarga.emblema = form.emblema.data
            recarga.precio = form.precio.data
            recarga.monto_carga = form.monto.data
            db.session.commit()
            flash('Se modifico la recarga con exito.')
            return  redirect(url_for('recargas'))
        form.fecha_carga.data = recarga.fecha_carga
        form.odometro.data = recarga.odometro
        form.emblema.data = recarga.emblema
        form.precio.data = recarga.precio 
        form.monto.data = recarga.monto_carga
        return render_template('modificar_recarga.html', form=form, recarga_id=recarga.id)
    else:
        flash('No se encontro la recarga a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_recarga/<int:recarga_id>', methods=['GET', 'POST'])
def borrar_recarga(recarga_id):
    recarga = Cargas.query.get(recarga_id)
    form = FormularioCombustible()
    if recarga:
        form.fecha_carga.data = recarga.fecha_carga
        form.odometro.data = recarga.odometro
        form.emblema.data = recarga.emblema
        form.precio.data = recarga.precio 
        form.monto.data = recarga.monto_carga
        if form.validate_on_submit():
            db.session.delete(recarga)
            db.session.commit()
            flash('Lista de recargas actualizada.')
            return  redirect(url_for('recargas'))
        return render_template('borrar_recarga.html', form=form, recarga_id=recarga_id)
    else:
        flash('No se encontro la recarga a eliminar.')
    return redirect(url_for('index'))

@app.route('/movimientos_mes/<string:mes>', methods=['GET', 'POST'])
def movimientos_mes(mes):
    operaciones = dbmodel.session.query(Movimientos).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==mes).all()
    if operaciones:
        balance_mes = balance_cuenta_puntual(operaciones)
        return render_template('detalle_mes.html', operaciones=operaciones, balance_mes=balance_mes)

@app.route('/modificar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
def modificar_operacion(operacion_id):
    operacion = Movimientos.query.get(operacion_id)
    form = FormularioMovimientos()
    if operacion:
        if form.validate_on_submit():
            mes = operacion.fecha_operacion.strftime('%Y-%m') 
            if not mes: mes = datetime.now().strftime("%Y-%m")
            operacion.fecha_operacion = form.fecha_operacion.data # hay que preparar un datepicker
            operacion.descripcion = form.descripcion.data
            operacion.monto_operacion = form.monto_operacion.data
            operacion.id_tipo_movimiento = form.tipo_operacion.data
            db.session.commit()
            flash('Se modifico la operacion con exito.')
            return redirect(url_for('movimientos_mes', mes=mes))
        form.fecha_operacion.data = operacion.fecha_operacion # hay que preparar un datepicker
        form.descripcion.data = operacion.descripcion
        form.monto_operacion.data = operacion.monto_operacion
        form.tipo_operacion.data = operacion.tipo_movimiento.id
        return render_template('modificar_operacion.html', form=form, operacion_id=operacion_id)
    else:
        flash('No se encontro la operacion a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
def borrar_operacion(operacion_id):
    operacion = Movimientos.query.get(operacion_id)
    form = FormularioMovimientos()
    if operacion:
        form.fecha_operacion.data = operacion.fecha_operacion
        form.descripcion.data = operacion.descripcion
        form.monto_operacion.data = operacion.monto_operacion
        form.tipo_operacion.data = operacion.tipo_movimiento.id
        form.tipo_operacion_view.data = operacion.tipo_movimiento.tipo
        if form.validate_on_submit():
            mes = operacion.fecha_operacion.strftime('%Y-%m') 
            db.session.delete(operacion)
            db.session.commit()
            flash('Lista de movimientos actualizada.')
            return redirect(url_for('movimientos_mes', mes=mes))
        return render_template('borrar_operacion.html', form=form, operacion_id=operacion_id)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('index'))

@app.route('/nueva_operacion', methods=['GET', 'POST'])
def nueva_operacion():
    form = FormularioMovimientos()
    if form.validate_on_submit():
        carga = Movimientos(date=datetime.utcnow(),
                        fecha_operacion=form.fecha_operacion.data,
                        descripcion=form.descripcion.data, 
                        monto_operacion=form.monto_operacion.data,
                        id_tipo_movimiento=form.tipo_operacion.data)
        db.session.add(carga)
        db.session.commit()
        flash('Nueva operacion agregada con exito.') #esta bueno
        return redirect(url_for('index'))
    return render_template('nueva_operacion.html', form=form)

@app.route('/historial_operacion/<string:anno>/<string:anno_mes>', methods=['GET', 'POST'])
def historial_operacion(anno, anno_mes):
    movimientos_anno = dbmodel.session.query(func.strftime("%Y", Movimientos.fecha_operacion).label('anno'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y", Movimientos.fecha_operacion)).all()
    movimientos_anno_especifico = dbmodel.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion)).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).all() #datetime.now().strftime("%Y")
    movimientos_mes_especifico = dbmodel.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion)).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).all() #datetime.now().strftime("%Y")
    movimientos_mes_detalle = dbmodel.session.query(Movimientos).filter(func.strftime("%Y-%m", Movimientos.fecha_operacion)==anno_mes).all()
    
    return render_template('historial_operaciones.html', anno=anno, movimientos_anno=movimientos_anno, movimientos_anno_especifico=movimientos_anno_especifico, movimientos_mes_especifico=movimientos_mes_especifico, movimientos_mes_detalle=movimientos_mes_detalle)

@app.route('/parametrico', methods=['GET', 'POST'])
def parametrico():
    tipos_movimiento = TiposMovimiento.query.all()
    agrupador_gastos = AgrupadorGastos.query.all()
    return render_template('parametrico.html', tipos_movimiento=tipos_movimiento, agrupador_gastos=agrupador_gastos)

@app.route('/modificar_parametrico/<int:parametrico_id>/<string:origen>', methods=['GET', 'POST'])
def modificar_parametrico(parametrico_id, origen):
    form = FormularioParametricos()
    if origen == 'TIPOS':
        parametro = TiposMovimiento.query.get(parametrico_id)
    elif origen == 'AGRUPADORES':
        parametro = AgrupadorGastos.query.get(parametrico_id)
    if parametro:
        if form.validate_on_submit():
            if origen == 'TIPOS':
                parametro.tipo = form.descripcion.data
                # db.session.commit()
            elif origen == 'AGRUPADORES':
                parametro.agrupador = form.descripcion.data
            db.session.commit()
            flash('Lista de '+ origen +' actualizada.')
            return redirect(url_for('parametrico'))
        if origen == 'TIPOS':
            form.descripcion.data = parametro.tipo
        elif origen == 'AGRUPADORES':
            form.descripcion.data = parametro.agrupador
        return render_template('modificar_parametrico.html', form=form, parametrico_id=parametrico_id, origen=origen)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('parametrico'))

@app.route('/borrar_parametrico/<int:parametrico_id>/<string:origen>', methods=['GET', 'POST'])
def borrar_parametrico(parametrico_id, origen):
    form = FormularioParametricos()
    if origen == 'TIPOS':
        parametro = TiposMovimiento.query.get(parametrico_id)
    elif origen == 'AGRUPADORES':
        parametro = AgrupadorGastos.query.get(parametrico_id)
    if parametro:
        if origen == 'TIPOS':
            # parametro = TiposMovimiento(tipo=form.descripcion.data)
            form.descripcion.data = parametro.tipo
        elif origen == 'AGRUPADORES':
            # parametro = AgrupadorGastos(agrupador=form.descripcion.data)
            form.descripcion.data = parametro.agrupador
        if form.validate_on_submit():
            db.session.delete(parametro)
            db.session.commit()
            flash('Lista de '+ origen +' actualizada.')
            return redirect(url_for('parametrico'))
        return render_template('borrar_parametrico.html', form=form, parametrico_id=parametrico_id, origen=origen)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('parametrico'))

@app.route('/nuevo_parametrico/<string:origen>', methods=['GET', 'POST'])
def nuevo_parametrico(origen):
    form = FormularioParametricos()
    if form.validate_on_submit():
        if origen == 'TIPOS':
            parametro = TiposMovimiento(tipo=form.descripcion.data)
        elif origen == 'AGRUPADORES':
            parametro = AgrupadorGastos(agrupador=form.descripcion.data)
        db.session.add(parametro)
        db.session.commit()
        flash('Nuevo parametro: ' + origen + ' agregado con exito.')
        return redirect(url_for('parametrico'))
    return render_template('nuevo_parametrico.html', form=form, origen=origen)    

@app.route('/nuevo_gasto', methods=['GET', 'POST'])
def nuevo_gasto():
    form = FormularioGastos()
    if form.validate_on_submit():
        carga = GastosFijos(date=datetime.utcnow(),
                        fecha_pagar=form.fecha_pagar.data,
                        descripcion=form.descripcion.data, 
                        monto=form.monto.data,
                        operacion=form.operacion.data,
                        pagado=form.pagado.data,
                        id_agrupador_gastos=form.agrupador.data)
        db.session.add(carga)
        db.session.commit()
        flash('Nueva operacion agregada con exito.') #esta bueno
        return redirect(url_for('index'))
    return render_template('nuevo_gasto.html', form=form)

@app.route('/historico_gastos_detalle/<string:periodo>', methods=['GET', 'POST'])
def historico_gastos_detalle(periodo):
    gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).all()
    if not gastos:
        precarga_deudas(periodo)
        gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).all()
    deuda = deuda_total(gastos)
    disponibilidad = SALARIO_NETO - deuda
    return render_template('historico_gastos_detalle.html', gastos=gastos, deuda=deuda, disponibilidad=disponibilidad)

@app.route('/modificar_gasto/<int:gasto_id>', methods=['GET', 'POST'])
def modificar_gasto(gasto_id):
    gasto = GastosFijos.query.get(gasto_id)
    form = FormularioGastos()
    if gasto:
        if form.validate_on_submit():
            mes = gasto.fecha_pagar.strftime('%Y-%m') 
            gasto.fecha_pagar = form.fecha_pagar.data 
            gasto.descripcion = form.descripcion.data
            gasto.monto = form.monto.data
            gasto.id_agrupador_gastos = form.agrupador.data
            gasto.operacion = form.operacion.data
            gasto.pagado = form.pagado.data
            db.session.commit()
            flash('Se modifico el gasto con exito.')
            return redirect(url_for('historico_gastos_detalle', periodo=mes))

        form.fecha_pagar.data = gasto.fecha_pagar
        form.descripcion.data = gasto.descripcion
        form.monto.data = gasto.monto
        form.operacion.data = gasto.operacion 
        form.pagado.data = gasto.pagado
        form.agrupador.data = gasto.agrupador_gastos
        return render_template('modificar_gasto.html', form=form, gasto_id=gasto.id)
    else:
        flash('No se encontro el gasto a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_gasto/<int:gasto_id>', methods=['GET', 'POST'])
def borrar_gasto(gasto_id):
    gasto = GastosFijos.query.get(gasto_id)
    form = FormularioGastos()
    if gasto:
        form.fecha_pagar.data = gasto.fecha_pagar
        form.descripcion.data = gasto.descripcion
        form.monto.data = gasto.monto
        form.operacion.data = gasto.operacion 
        form.pagado.data = gasto.pagado
        form.agrupador.data = gasto.agrupador_gastos.id
        form.agrupador_view.data = gasto.agrupador_gastos.agrupador
        if form.validate_on_submit():
            mes = gasto.fecha_pagar.strftime('%Y-%m') 
            db.session.delete(gasto)
            db.session.commit()
            flash('Lista de gastos actualizada.')
            return redirect(url_for('historico_gastos_detalle', periodo=mes))
        return render_template('borrar_gasto.html', form=form, gasto_id=gasto_id)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('index'))   

@app.route('/historico_gastos', methods=['GET', 'POST'])
def historico_gastos():
    gastos = dbmodel.session.query(func.strftime("%Y-%m", GastosFijos.fecha_pagar).label('fecha'), AgrupadorGastos.agrupador.label('acreedor'), func.sum(GastosFijos.monto).label('total')).join(AgrupadorGastos).group_by(func.strftime("%Y-%m", GastosFijos.fecha_pagar), AgrupadorGastos.agrupador).all()
    return render_template('historico_gastos.html', gastos=gastos)