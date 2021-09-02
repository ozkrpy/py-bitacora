from main import app, db
from flask import render_template, redirect, url_for, flash, get_flashed_messages, request
from formularios import NuevaRecargaCombustible
from models import Cargas
from datetime import datetime
from utilitarios import referencias_vehiculo

@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
def index():
    form = NuevaRecargaCombustible()
    cargas = Cargas.query.all()
    referencias_principales=referencias_vehiculo(cargas)
    return render_template('home.html', **referencias_principales, form=form)

@app.route('/recargas', methods=['GET', 'POST'])
def recargas():
    #cargas = Cargas.query.order_by(Cargas.fecha_carga.desc()).all()
    cargas = Cargas.query.all()
    return render_template('combustible.html', cargas=cargas)

@app.route('/nueva_recarga', methods=['GET', 'POST'])
def nueva_recarga():
    form = NuevaRecargaCombustible()
    if form.validate_on_submit():
        carga = Cargas(date=datetime.utcnow(), 
                       fecha_carga=datetime.utcnow(),
                       odometro=form.odometro.data, 
                       emblema=form.emblema.data,
                       precio=form.precio.data,
                       monto_carga=form.monto.data
                      )
        db.session.add(carga)
        db.session.commit()
        flash('Nuevo recarga agregada con exito.') #esta bueno
        return redirect(url_for('index'))
    return render_template('recarga.html', form=form)

@app.route('/modificar_recarga/<int:recarga_id>', methods=['GET', 'POST'])
def modificar_recarga(recarga_id):
    recarga = Cargas.query.get(recarga_id)
    form = NuevaRecargaCombustible()
    if recarga:
        if form.validate_on_submit():
            recarga.fecha_carga = datetime.utcnow() # hay que preparar un datepicker
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
    form = NuevaRecargaCombustible()
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
