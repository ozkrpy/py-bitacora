from main import app, db
from flask import render_template, redirect, url_for, flash, get_flashed_messages, request
from sqlalchemy import func
from formularios import FormularioMovimientos, FormularioCombustible
from models import db as dbmodel, Cargas, Movimientos, TiposMovimiento
from datetime import date, datetime
from utilitarios import referencias_vehiculo, listar_tipos

@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = FormularioCombustible()
    cargas = Cargas.query.all()
    anno = datetime.now().strftime("%Y")
    referencias_principales = referencias_vehiculo(cargas)
    movimientos = dbmodel.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), func.sum(Movimientos.monto_operacion).label('total')).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion)).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).all()
    return render_template('home.html', **referencias_principales, form=form, movimientos=movimientos, anno=anno) #usar ** permite que se manipule la variable directamente en el DOM

@app.route('/recargas', methods=['GET', 'POST'])
def recargas():
    #cargas = Cargas.query.order_by(Cargas.fecha_carga.desc()).all()
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
        return render_template('detalle_mes.html', operaciones=operaciones)

@app.route('/modificar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
def modificar_operacion(operacion_id):
    operacion = Movimientos.query.get(operacion_id)
    form = FormularioMovimientos()
    if operacion:
        if form.validate_on_submit():
            mes = operacion.fecha_operacion.strftime('%Y-%m') 
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
        form.tipo_operacion.data = operacion.tipo_movimiento.tipo
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

