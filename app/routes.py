from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.formularios import FormularioGastos, FormularioMovimientos, FormularioCombustible, FormularioParametricos, FormularioPendientes, FormularioTarjetas, FormularioBusqueda, LoginForm, RegistrationForm
from app.models import DeudasPendientes, Tarjetas, User, AgrupadorGastos, GastosFijos, Cargas, Movimientos, TiposMovimiento
from app.utilitarios import balance_cuenta, calcular_disponibilidad, movimientos_tarjeta, referencias_vehiculo, balance_cuenta_puntual, precarga_deudas, deuda_total, referencias_vehiculo_puntual, saldo_grupo, movimientos_agrupados, saldos_mes_tarjeta, balances_tarjetas, resumenes_tarjeta_macro
# from app.parametros import SALARIO_NETO
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import func
from werkzeug.urls import url_parse

@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = FormularioCombustible()
    cargas = Cargas.query.all()
    anno = datetime.now().strftime("%Y")
    fechas_referencia = {'mes_anterior_2':datetime.now()-relativedelta(months=2), 'mes_anterior':datetime.now()-relativedelta(months=1), 'fecha_actual':datetime.now(),  'mes_siguiente':datetime.now()+relativedelta(months=1), 'mes_siguiente_2':datetime.now()+relativedelta(months=2)}
    referencias_principales = referencias_vehiculo(cargas)
    balance_movimientos, balance_mensual = balance_cuenta()
    # saldo_atlas = balance_cuenta_puntual(movimientos_tarjeta(1))
    # saldo_basa = balance_cuenta_puntual(movimientos_tarjeta(2))
    # saldo_interfisa = balance_cuenta_puntual(movimientos_tarjeta(3))
    gastos = db.session.query(AgrupadorGastos.agrupador.label('acreedor'), func.sum(GastosFijos.monto).label('total')).join(AgrupadorGastos).group_by(AgrupadorGastos.agrupador).filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==fechas_referencia['fecha_actual'].strftime('%Y-%m')).all()
    # total_gasto = saldo_grupo(gastos)
    credito, pendientes, pagadas = calcular_disponibilidad(fechas_referencia['fecha_actual'].strftime('%Y-%m'))
    disponibilidad = credito - pagadas
    balance=balances_tarjetas()
    id_tarjeta = db.session.query(Tarjetas.banco).filter(Tarjetas.estado==True).first()
    # return render_template('home.html',  form=form, **referencias_principales, movimientos=balance_mensual, anno=anno, fechas_referencia=fechas_referencia, balance_movimientos=balance_movimientos, gastos=gastos, total_gasto=pendientes, saldo_atlas=saldo_atlas, saldo_basa=saldo_basa, saldo_interfisa=saldo_interfisa, disponibilidad=disponibilidad, balance=balance, id_tarjeta=id_tarjeta[0]) #usar ** permite que se manipule la variable directamente en el DOM
    return render_template('home.html',  form=form, **referencias_principales, movimientos=balance_mensual, anno=anno, fechas_referencia=fechas_referencia, balance_movimientos=balance_movimientos, gastos=gastos, total_gasto=pendientes, disponibilidad=disponibilidad, balance=balance, id_tarjeta=id_tarjeta[0]) #usar ** permite que se manipule la variable directamente en el DOM

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/recargas', methods=['GET', 'POST'])
@login_required
def recargas():
    cargas_anuales = []
    annos = db.session.query(func.strftime("%Y", Cargas.fecha_carga).label('anno')).distinct().all()
    for anno in annos:
        referencias = referencias_vehiculo_puntual(anno[0])
        cargas_anuales.append(referencias)
    return render_template('combustible.html', cargas_anuales=cargas_anuales)

@app.route('/recargas_detalle/<anno>', methods=['GET', 'POST'])
@login_required
def recargas_detalle(anno):
    cargas = Cargas.query.filter(func.strftime("%Y", Cargas.fecha_carga)==anno).order_by(Cargas.fecha_carga).all()
    return render_template('detalles_anno_combus.html', cargas=cargas, anno=anno)

@app.route('/nueva_recarga', methods=['GET', 'POST'])
@login_required
def nueva_recarga():
    form = FormularioCombustible()
    if form.fecha_carga.data is None:
        form.fecha_carga.data = datetime.today()
        
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
        carga = Movimientos(date=datetime.utcnow(),
                        fecha_operacion=form.fecha_carga.data,
                        descripcion=form.emblema.data, 
                        monto_operacion=form.monto.data,
                        id_tipo_movimiento=3,
                        id_tarjeta=form.tarjeta.data)
        db.session.add(carga)
        db.session.commit()
        flash('Nueva recarga agregada con exito.') 
        return redirect(url_for('index'))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('recarga.html', form=form)

@app.route('/modificar_recarga/<int:recarga_id>', methods=['GET', 'POST'])
@login_required
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
            #recarga.ta
            db.session.commit()
            flash('Se modifico la recarga con exito.')
            return  redirect(url_for('recargas'))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
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
@login_required
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
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        return render_template('borrar_recarga.html', form=form, recarga_id=recarga_id)
    else:
        flash('No se encontro la recarga a eliminar.')
    return redirect(url_for('index'))

@app.route('/movimientos_mes/', defaults={'mes':datetime.now().strftime('%Y-%m')}, methods=['GET', 'POST'])
@app.route('/movimientos_mes/<string:mes>', methods=['GET', 'POST'])
@login_required
def movimientos_mes(mes):
    defaults={'mes':datetime.now().strftime('%Y-%m')}
    meses = datetime.strptime(mes, '%Y-%m')
    fechas={'mes_anterior':meses-relativedelta(months=1), 'mes_actual':meses, 'mes_siguiente':meses+relativedelta(months=1)}
    operaciones_tj = movimientos_agrupados(mes)
    balances=saldos_mes_tarjeta(mes)

    return render_template('detalle_mes.html', mes=mes, operaciones_tj=operaciones_tj, balances=balances, fechas=fechas)

@app.route('/modificar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
@login_required
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
            operacion.id_tarjeta = form.tarjeta.data
            db.session.commit()
            flash('Se modifico la operacion con exito.')
            return redirect(url_for('movimientos_mes', mes=mes))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        form.fecha_operacion.data = operacion.fecha_operacion # hay que preparar un datepicker
        form.descripcion.data = operacion.descripcion
        form.monto_operacion.data = operacion.monto_operacion
        form.tipo_operacion.data = operacion.tipo_movimiento.id
        form.tarjeta.data = operacion.tarjeta.id
        return render_template('modificar_operacion.html', form=form, operacion_id=operacion_id)
    else:
        flash('No se encontro la operacion a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
@login_required
def borrar_operacion(operacion_id):
    operacion = Movimientos.query.get(operacion_id)
    form = FormularioMovimientos()
    if operacion:
        form.fecha_operacion.data = operacion.fecha_operacion
        form.descripcion.data = operacion.descripcion
        form.monto_operacion.data = operacion.monto_operacion
        form.tipo_operacion.data = operacion.tipo_movimiento.id
        form.tipo_operacion_view.data = operacion.tipo_movimiento.tipo
        form.tarjeta.data = operacion.tarjeta.id
        form.tarjeta_view.data = operacion.tarjeta.banco
        if form.validate_on_submit():
            mes = operacion.fecha_operacion.strftime('%Y-%m') 
            db.session.delete(operacion)
            db.session.commit()
            flash('Lista de movimientos actualizada.')
            return redirect(url_for('movimientos_mes', mes=mes))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        return render_template('borrar_operacion.html', form=form, operacion_id=operacion_id)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('index'))

@app.route('/nueva_operacion/<string:tarjeta>', methods=['GET', 'POST'])
@login_required
def nueva_operacion(tarjeta):
    form = FormularioMovimientos()
    if form.fecha_operacion.data is None:
        form.fecha_operacion.data = datetime.today()
    if tarjeta:
        tj = db.session.query(Tarjetas).filter(Tarjetas.banco==tarjeta).first()
        form.tarjeta.data=tj.id
    else:
        tj = db.session.query(Tarjetas).filter(Tarjetas.estado==True).first()
    tarjeta = tj.banco
    if form.validate_on_submit():
        mes = form.fecha_operacion.data.strftime('%Y-%m') 
        if not mes: mes = datetime.now().strftime("%Y-%m")
        carga = Movimientos(date=datetime.utcnow(),
                        fecha_operacion=form.fecha_operacion.data,
                        descripcion=form.descripcion.data, 
                        monto_operacion=form.monto_operacion.data,
                        id_tipo_movimiento=form.tipo_operacion.data, 
                        id_tarjeta=form.tarjeta.data)
        db.session.add(carga)
        db.session.commit()
        if (form.tipo_operacion.data==10): # 10 es el id de pago
            carga = GastosFijos(date=datetime.utcnow(),
                            fecha_pagar=form.fecha_operacion.data,
                            descripcion=form.descripcion.data, 
                            monto=form.monto_operacion.data,
                            operacion=False,
                            pagado=True,
                            id_agrupador_gastos=3)
            db.session.add(carga) 
            db.session.commit()
        flash('Nueva operacion agregada con exito.')
        return redirect(url_for('movimientos_mes', mes=mes))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('nueva_operacion.html', form=form, id_tarjeta=tarjeta)

@app.route('/historial_operacion', methods=['GET', 'POST'])
@login_required
def historial_operacion():
    operaciones=[]
    for movimiento in db.session.query(func.strftime("%Y", Movimientos.fecha_operacion).label('fecha_operacion'), Movimientos.id_tipo_movimiento.label('id_tipo_movimiento'), TiposMovimiento.tipo.label('acreedor'), func.sum(Movimientos.monto_operacion).label('total')).join(TiposMovimiento).filter(Movimientos.id_tipo_movimiento==TiposMovimiento.id).group_by(func.strftime("%Y", Movimientos.fecha_operacion), Movimientos.id_tipo_movimiento, TiposMovimiento.tipo).order_by(TiposMovimiento.tipo).all():
        operaciones.append({'fecha_operacion':movimiento.fecha_operacion, 'id_tipo_movimiento': movimiento.id_tipo_movimiento, 'acreedor': movimiento.acreedor, 'total': movimiento.total})
    return render_template('historial_operaciones.html', operaciones=operaciones)

@app.route('/historial_operacion_anno/<string:anno>', methods=['GET', 'POST'])
@login_required
def historial_operacion_messanno(anno):
    operaciones = db.session.query(func.strftime("%Y-%m", Movimientos.fecha_operacion).label('fecha'), TiposMovimiento.tipo.label('acreedor'), func.sum(Movimientos.monto_operacion).label('total')).join(TiposMovimiento).filter(func.strftime("%Y", Movimientos.fecha_operacion)==anno).group_by(func.strftime("%Y-%m", Movimientos.fecha_operacion), TiposMovimiento.tipo).all()
    return render_template('historial_operaciones_anno.html', gastos=operaciones)#, anno=anno, movimientos_anno=movimientos_anno, movimientos_anno_especifico=movimientos_anno_especifico, movimientos_mes_especifico=movimientos_mes_especifico, movimientos_mes_detalle=movimientos_mes_detalle)

@app.route('/parametrico', methods=['GET', 'POST'])
@login_required
def parametrico():
    tipos_movimiento = TiposMovimiento.query.all()
    agrupador_gastos = AgrupadorGastos.query.all()
    gastos_fijos = DeudasPendientes.query.all()
    tarjetas = resumenes_tarjeta_macro() # Tarjetas.query.all()
    return render_template('parametrico.html', tipos_movimiento=tipos_movimiento, agrupador_gastos=agrupador_gastos, gastos_fijos=gastos_fijos, tarjetas=tarjetas)

@app.route('/modificar_parametrico/<int:parametrico_id>/<string:origen>', methods=['GET', 'POST'])
@login_required
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
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        if origen == 'TIPOS':
            form.descripcion.data = parametro.tipo
        elif origen == 'AGRUPADORES':
            form.descripcion.data = parametro.agrupador
        return render_template('modificar_parametrico.html', form=form, parametrico_id=parametrico_id, origen=origen)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('parametrico'))

@app.route('/borrar_parametrico/<int:parametrico_id>/<string:origen>', methods=['GET', 'POST'])
@login_required
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
@login_required
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
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('nuevo_parametrico.html', form=form, origen=origen)    

@app.route('/nuevo_gasto', methods=['GET', 'POST'])
@login_required
def nuevo_gasto():
    form = FormularioGastos()
    if form.fecha_pagar.data is None:
        form.fecha_pagar.data = datetime.today()
    if form.validate_on_submit():
        mes = form.fecha_pagar.data.strftime('%Y-%m') 
        if not mes: mes = datetime.now().strftime("%Y-%m")
        carga = GastosFijos(date=datetime.utcnow(),
                        fecha_pagar=form.fecha_pagar.data,
                        descripcion=form.descripcion.data, 
                        monto=form.monto.data,
                        operacion=form.operacion.data,
                        pagado=form.pagado.data,
                        id_agrupador_gastos=form.agrupador.data)
        db.session.add(carga)
        db.session.commit()
        flash('Nueva operacion agregada con exito.') 
        return redirect(url_for('historico_gastos_detalle', periodo=mes))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('nuevo_gasto.html', form=form)

@app.route('/historico_gastos_detalle/', defaults={'periodo':datetime.now().strftime('%Y-%m')}, methods=['GET', 'POST'])
@app.route('/historico_gastos_detalle/<string:periodo>', methods=['GET', 'POST'])
@login_required
def historico_gastos_detalle(periodo):
    date_obj = datetime.strptime(periodo, '%Y-%m')
    fechas={'mes_anterior':date_obj-relativedelta(months=1), 'mes_actual':date_obj, 'mes_siguiente':date_obj+relativedelta(months=1)}
    gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).order_by(GastosFijos.fecha_pagar).order_by(GastosFijos.id_agrupador_gastos).all()
    if not gastos:
        precarga_deudas(periodo)
        gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).all()
    deuda = deuda_total(gastos)
    credito, pendientes, pagados = calcular_disponibilidad(periodo)#SALARIO_NETO -  deuda
    disponibilidad = credito - pagados
    balance_movimientos, balance_mensual = balance_cuenta()
    return render_template('historico_gastos_detalle.html', periodo=periodo, gastos=gastos, deuda=pagados, disponibilidad=disponibilidad, pendientes=pendientes, fechas=fechas, balance_movimientos=balance_movimientos)

@app.route('/modificar_gasto/<int:gasto_id>', methods=['GET', 'POST'])
@login_required
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
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        form.fecha_pagar.data = gasto.fecha_pagar
        form.descripcion.data = gasto.descripcion
        form.monto.data = gasto.monto
        form.operacion.data = gasto.operacion 
        form.pagado.data = gasto.pagado
        form.agrupador.data = gasto.agrupador_gastos.id
        return render_template('modificar_gasto.html', form=form, gasto_id=gasto.id)
    else:
        flash('No se encontro el gasto a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_gasto/<int:gasto_id>', methods=['GET', 'POST'])
@login_required
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
            #gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==mes).filter(GastosFijos.descripcion!='REFERENCIA').all()
            gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==mes).all()
            if not gastos:
                return redirect(url_for('index'))
            return redirect(url_for('historico_gastos_detalle', periodo=mes))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        return render_template('borrar_gasto.html', form=form, gasto_id=gasto_id)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('index'))   

@app.route('/historico_gastos', methods=['GET', 'POST'])
@login_required
def historico_gastos():
    gastos = db.session.query(func.strftime("%Y", GastosFijos.fecha_pagar).label('fecha'), AgrupadorGastos.agrupador.label('acreedor'), func.sum(GastosFijos.monto).label('total')).join(AgrupadorGastos).group_by(func.strftime("%Y", GastosFijos.fecha_pagar), AgrupadorGastos.agrupador).all()
    return render_template('historico_gastos.html', gastos=gastos)

@app.route('/historico_gastos_mesanno/<string:anno>', methods=['GET', 'POST'])
@login_required
def historico_gastos_mesanno(anno):
    gastos = db.session.query(func.strftime("%Y-%m", GastosFijos.fecha_pagar).label('fecha'), AgrupadorGastos.agrupador.label('acreedor'), func.sum(GastosFijos.monto).label('total')).join(AgrupadorGastos).filter(func.strftime("%Y", GastosFijos.fecha_pagar)==anno).group_by(func.strftime("%Y-%m", GastosFijos.fecha_pagar), AgrupadorGastos.agrupador).all()
    return render_template('historico_gastos_mesanno.html', gastos=gastos)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('register.html', title='Register', form=form)

@app.route('/modificar_pendiente/<int:pendiente_id>', methods=['GET', 'POST'])
@login_required
def modificar_pendiente(pendiente_id):
    operacion = DeudasPendientes.query.get(pendiente_id)
    form = FormularioPendientes()
    if operacion:
        if form.validate_on_submit():
            operacion.descripcion = form.descripcion.data
            operacion.monto = form.monto.data
            operacion.estado = form.estado.data
            operacion.cuotas = form.cuotas.data
            operacion.cuotas_pagadas = form.cuotas_pagadas.data
            operacion.id_agrupador = form.tipo.data
            db.session.commit()
            flash('Se modifico la operacion con exito.')
            return redirect(url_for('parametrico'))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        form.descripcion.data = operacion.descripcion
        form.monto.data = operacion.monto
        form.estado.data = operacion.estado
        form.cuotas.data = operacion.cuotas
        form.cuotas_pagadas.data = operacion.cuotas_pagadas
        form.tipo.data = operacion.id_agrupador
        return render_template('modificar_pendientes.html', form=form, pendiente_id=pendiente_id)
    else:
        flash('No se encontro la operacion a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_pendiente/<int:pendiente_id>', methods=['GET', 'POST'])
@login_required
def borrar_pendiente(pendiente_id):
    operacion = DeudasPendientes.query.get(pendiente_id)
    form = FormularioPendientes()
    if operacion:
        form.descripcion.data = operacion.descripcion
        form.monto.data = operacion.monto
        form.estado.data = operacion.estado
        form.cuotas.data = operacion.cuotas
        form.cuotas_pagadas.data = operacion.cuotas_pagadas
        form.tipo.data = operacion.id_agrupador
        if form.validate_on_submit():
            db.session.delete(operacion)
            db.session.commit()
            flash('Operacion pendiente eliminada.')
            return redirect(url_for('parametrico'))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        return render_template('borrar_pendientes.html', form=form, pendiente_id=pendiente_id)
    else:
        flash('No se encontro la operacion a eliminar.')
    return redirect(url_for('index'))   

@app.route('/nuevo_pendiente', methods=['GET', 'POST'])
@login_required
def nuevo_pendiente():
    form = FormularioPendientes()
    if form.validate_on_submit():
        operacion = DeudasPendientes(descripcion=form.descripcion.data,
                        monto=form.monto.data, 
                        estado=form.estado.data,
                        cuotas=form.cuotas.data,
                        cuotas_pagadas=form.cuotas_pagadas.data,
                        id_agrupador=form.tipo.data)
        db.session.add(operacion)
        db.session.commit()
        flash('Nuevo gasto pendiente agregado con exito.') 
        return redirect(url_for('parametrico'))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('nuevo_pendiente.html', form=form)

@app.route('/nueva_tarjeta', methods=['GET', 'POST'])
@login_required
def nueva_tarjeta():
    form = FormularioTarjetas()
    if form.validate_on_submit():
        tarjeta = Tarjetas(
                        banco=form.banco.data, 
                        numero=form.numero.data, 
                        vencimiento=form.vencimiento.data,
                        estado=form.estado.data)
        db.session.add(tarjeta)
        db.session.commit()
        flash('Nueva tarjeta agregada con exito.') 
        return redirect(url_for('parametrico'))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('nueva_tarjeta.html', form=form)

@app.route('/modificar_tarjeta/<int:tarjeta_id>', methods=['GET', 'POST'])
@login_required
def modificar_tarjeta(tarjeta_id):
    operacion = Tarjetas.query.get(tarjeta_id)
    form = FormularioTarjetas()
    if operacion:
        if form.validate_on_submit():
            operacion.banco = form.banco.data
            operacion.numero = form.numero.data
            operacion.vencimiento = form.vencimiento.data
            operacion.estado = form.estado.data
            db.session.commit()
            flash('Se modifico la tarjeta con exito.')
            return redirect(url_for('parametrico'))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        form.banco.data = operacion.banco
        form.numero.data = operacion.numero
        form.vencimiento.data = operacion.vencimiento
        form.estado.data = operacion.estado
        return render_template('modificar_tarjeta.html', form=form, tarjeta_id=tarjeta_id)
    else:
        flash('No se encontro la tarjeta a modificar.')
    return redirect(url_for('index'))

@app.route('/borrar_tarjeta/<int:tarjeta_id>', methods=['GET', 'POST'])
@login_required
def borrar_tarjeta(tarjeta_id):
    operacion = Tarjetas.query.get(tarjeta_id)
    form = FormularioTarjetas()
    if operacion:
        form.banco.data = operacion.banco
        form.numero.data = operacion.numero
        form.vencimiento.data = operacion.vencimiento
        form.estado.data = operacion.estado
        if form.validate_on_submit():
            db.session.delete(operacion)
            db.session.commit()
            flash('Tarjeta de credito eliminada.')
            return redirect(url_for('parametrico'))
        else:
            for k, v in form.errors.items():
                flash('Error en: '+k)
        return render_template('borrar_tarjeta.html', form=form, tarjeta_id=tarjeta_id)
    else:
        flash('No se encontro la tarjeta a eliminar.')
    return redirect(url_for('index'))

@app.route('/busqueda', methods=['GET', 'POST'])
@login_required
def busqueda():
    debito = []
    credito = []
    form = FormularioBusqueda()
    texto = request.args.get('q')
    if texto:
        debito = GastosFijos.query.filter(GastosFijos.descripcion.contains(texto)).order_by(GastosFijos.fecha_pagar.desc())
        credito = Movimientos.query.filter(Movimientos.descripcion.contains(texto)).order_by(Movimientos.fecha_operacion.desc())
    return render_template('busqueda.html', form=form, debito=debito, credito=credito)

@app.route('/operaciones_tipo/<string:deudor>/<string:fecha>', methods=['GET', 'POST'])
@login_required
def operaciones_tipo(deudor, fecha):
    form = FormularioMovimientos()
    operaciones = db.session.query(Movimientos).filter(Movimientos.id_tipo_movimiento==deudor).filter(Movimientos.id_tipo_movimiento==TiposMovimiento.id).filter(func.strftime("%Y", Movimientos.fecha_operacion)==fecha).order_by(Movimientos.id_tipo_movimiento).all()
    return render_template('historico_operaciones_tipo.html', form=form, fecha=fecha, operaciones=operaciones)