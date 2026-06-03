from datetime import date, datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from flask import jsonify, render_template, flash, redirect, url_for, request, send_from_directory
from app import app, db
from app.formularios import FormularioGastos, FormularioMovimientos, FormularioCombustible, FormularioParametricos, FormularioPendientes, FormularioTarjetas, FormularioBusqueda, LoginForm, RegistrationForm
from app.models import DeudasPendientes, Tarjetas, User, AgrupadorGastos, GastosFijos, Cargas, Movimientos, TiposMovimiento
from app.utilitarios import listar_agrupador, balance_cuenta, calcular_disponibilidad, movimientos_tarjeta, referencias_vehiculo, balance_cuenta_puntual, precarga_deudas, deuda_total, referencias_vehiculo_puntual, saldo_grupo, movimientos_agrupados, saldos_mes_tarjeta, balances_tarjetas, resumenes_tarjeta_macro, movimientos_anno_tarjeta_balance, movimiento_balances_mes_a_mes
# from app.parametros import SALARIO_NETO
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from sqlalchemy import and_, func, desc, case, cast, Float 
from sqlalchemy.exc import SQLAlchemyError
import calendar
from collections import defaultdict
from zoneinfo import ZoneInfo




@app.route('/favicon.ico')
def favicon():
    # Opción A: Si decides meterlo en tu carpeta static en el futuro
    # return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    # Opción B: Devolver una respuesta vacía exitosa (Silencia el error 404 al instante)
    return '', 204

@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = FormularioCombustible()
    cargas = Cargas.query.all()
    
    # --- LOGICA DE PESTAÑAS DINÁMICAS (MESES POBLADOS) ---
    hoy = datetime.now()
    # Capturamos el mes y año seleccionados desde la URL; por defecto usamos el mes/año actual
    mes_activo = request.args.get('mes', default=hoy.month, type=int)
    anno_activo = request.args.get('anno', default=hoy.year, type=int)
    
    # Creamos un objeto datetime basado en la selección para recalcular el diccionario de referencias
    fecha_seleccionada = datetime(anno_activo, mes_activo, 1)
    
    # Extraemos todos los periodos únicos (Mes y Año) que tienen registros en GastosFijos
    periodos_poblados = db.session.query(
        func.strftime('%Y', GastosFijos.fecha_pagar).label('anno'),
        func.strftime('%m', GastosFijos.fecha_pagar).label('mes')
    ).group_by(
        'anno', 'mes'
    ).order_by(
        desc('anno'), desc('mes')  # <--- Cambiado aquí (limpio y nativo)
    # ).all()
    ).limit(6).all()  # Limitar a los últimos 12 meses para evitar sobrecargar la interfaz con demasiadas pestañas

    meses_es = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    lista_meses_tabs = []
    for p in periodos_poblados:
        if p.mes and p.anno: # Asegurar que no vengan nulos
            m_int = int(p.mes)
            a_int = int(p.anno)
            lista_meses_tabs.append({
                'anno': a_int,
                'mes': m_int,
                'label': f"{meses_es[m_int]} {a_int}",
                'es_activo': (m_int == mes_activo and a_int == anno_activo)
            })

    # Si la base de datos está vacía, agregamos por lo menos el mes actual
    if not lista_meses_tabs:
        lista_meses_tabs.append({
            'anno': hoy.year, 'mes': hoy.month, 'label': f"{meses_es[hoy.month]} {hoy.year}", 'es_activo': True
        })
    # -----------------------------------------------------

    anno = fecha_seleccionada.strftime("%Y")
    
    # Modificamos las referencias relativas basadas en la pestaña activa
    fechas_referencia = {
        'mes_anterior_2': fecha_seleccionada - relativedelta(months=2), 
        'mes_anterior': fecha_seleccionada - relativedelta(months=1), 
        'fecha_actual': fecha_seleccionada,  
        'mes_siguiente': fecha_seleccionada + relativedelta(months=1), 
        'mes_siguiente_2': fecha_seleccionada + relativedelta(months=2)
    }
    
    referencias_principales = referencias_vehiculo(cargas)
    balance_movimientos, balance_mensual = balance_cuenta()
    
    # El filtro ahora utiliza dinámicamente el periodo seleccionado por la pestaña
    periodo_filtro = fecha_seleccionada.strftime('%Y-%m')
    
    gastos = db.session.query(
        AgrupadorGastos.id.label('id_agrupador_gastos'), 
        AgrupadorGastos.agrupador.label('acreedor'), 
        func.sum(GastosFijos.monto).label('total')
    ).join(AgrupadorGastos).group_by(AgrupadorGastos.id, AgrupadorGastos.agrupador).filter(
        func.strftime("%Y-%m", GastosFijos.fecha_pagar) == periodo_filtro
    ).all()
    
    credito, pendientes, pagadas = calcular_disponibilidad(periodo_filtro)
    disponibilidad = credito - pagadas
    balance = balances_tarjetas()
    
    id_tarjeta = db.session.query(Tarjetas.banco).filter(Tarjetas.estado == True).first()
    id_tarjeta_val = id_tarjeta[0] if id_tarjeta else None

    return render_template(
        'new_home.html',  
        form=form, 
        **referencias_principales, 
        movimientos=balance_mensual, 
        anno=anno, 
        fechas_referencia=fechas_referencia, 
        balance_movimientos=balance_movimientos, 
        gastos=gastos, 
        total_gasto=pendientes, 
        disponibilidad=disponibilidad, 
        balance=balance, 
        id_tarjeta=id_tarjeta_val,
        lista_meses_tabs=lista_meses_tabs, # Enviamos la lista de pestañas a la vista
        mes_activo=mes_activo,             # Enviamos el mes activo como entero
        anno_activo=anno_activo            # Enviamos el año activo como entero
    )

# @app.route('/')
# @app.route('/index', methods=['GET', 'POST'])
# @login_required
# def index():
#     form = FormularioCombustible()
#     cargas = Cargas.query.all()
#     anno = datetime.now().strftime("%Y")
#     fechas_referencia = {'mes_anterior_2':datetime.now()-relativedelta(months=2), 'mes_anterior':datetime.now()-relativedelta(months=1), 'fecha_actual':datetime.now(),  'mes_siguiente':datetime.now()+relativedelta(months=1), 'mes_siguiente_2':datetime.now()+relativedelta(months=2)}
#     referencias_principales = referencias_vehiculo(cargas)
#     balance_movimientos, balance_mensual = balance_cuenta()
#     gastos = db.session.query(AgrupadorGastos.id.label('id_agrupador_gastos'), AgrupadorGastos.agrupador.label('acreedor'), func.sum(GastosFijos.monto).label('total')).join(AgrupadorGastos).group_by(AgrupadorGastos.id, AgrupadorGastos.agrupador).filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==fechas_referencia['fecha_actual'].strftime('%Y-%m')).all()
#     credito, pendientes, pagadas = calcular_disponibilidad(fechas_referencia['fecha_actual'].strftime('%Y-%m'))
#     disponibilidad = credito - pagadas
#     balance=balances_tarjetas()
#     id_tarjeta = db.session.query(Tarjetas.banco).filter(Tarjetas.estado==True).first()
#     return render_template('new_home.html',  
#                            form=form, 
#                            **referencias_principales, #usar ** permite que se manipule la variable directamente en el DOM
#                            movimientos=balance_mensual, 
#                            anno=anno, 
#                            fechas_referencia=fechas_referencia, 
#                            balance_movimientos=balance_movimientos, 
#                            gastos=gastos, total_gasto=pendientes, 
#                            disponibilidad=disponibilidad, 
#                            balance=balance, 
#                            id_tarjeta=id_tarjeta[0]) 
    

@app.route('/old_index', methods=['GET'])
def old_index():
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
    # return render_template('new_home.html',  form=form, **referencias_principales, movimientos=balance_mensual, anno=anno, fechas_referencia=fechas_referencia, balance_movimientos=balance_movimientos, gastos=gastos, total_gasto=pendientes, disponibilidad=disponibilidad, balance=balance, id_tarjeta=id_tarjeta[0]) #usar ** permite que se manipule la variable directamente en el DOM
    # return render_template('home.html',  form=form, **referencias_principales, movimientos=balance_mensual, anno=anno, fechas_referencia=fechas_referencia, balance_movimientos=balance_movimientos, gastos=gastos, total_gasto=pendientes, saldo_atlas=saldo_atlas, saldo_basa=saldo_basa, saldo_interfisa=saldo_interfisa, disponibilidad=disponibilidad, balance=balance, id_tarjeta=id_tarjeta[0]) #usar ** permite que se manipule la variable directamente en el DOM
    # return render_template('home.html',  form=form, **referencias_principales, movimientos=balance_mensual, anno=anno, fechas_referencia=fechas_referencia, balance_movimientos=balance_movimientos, gastos=gastos, total_gasto=pendientes, disponibilidad=disponibilidad, balance=balance, id_tarjeta=id_tarjeta[0]) #usar ** permite que se manipule la variable directamente en el DOM
    


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user is None or not user.check_password(form.password.data):
#             flash('Invalid username or password')
#             return redirect(url_for('login'))
#         login_user(user, remember=form.remember_me.data)
#         next_page = request.args.get('next')
#         if not next_page or url_parse(next_page).netloc != '':
#             next_page = url_for('index')
#         return redirect(next_page)
#     return render_template('login.html', title='Sign In', form=form)

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
    return render_template('new_login.html', title='Iniciar Sesion', form=form)

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

# @app.route('/movimientos_mes/', defaults={'mes':datetime.now().strftime('%Y-%m')}, methods=['GET', 'POST'])
# @app.route('/movimientos_mes/<string:mes>', methods=['GET', 'POST'])
# @login_required
# def movimientos_mes(mes):
#     form = FormularioMovimientos()
#     # print(datetime.now().strftime('%Y-%m'), mes)
#     defaults={'mes':datetime.now().strftime('%Y-%m')}
#     meses = datetime.strptime(mes, '%Y-%m')
#     fechas={'mes_anterior':meses-relativedelta(months=1), 'mes_actual':meses, 'mes_siguiente':meses+relativedelta(months=1)}
#     operaciones_tj = movimientos_agrupados(mes)
#     balances=saldos_mes_tarjeta(mes)
#     # return render_template('detalle_mes.html', mes=mes, operaciones_tj=operaciones_tj, balances=balances, fechas=fechas)
#     return render_template('new_detalle_mes.html', mes=mes, operaciones_tj=operaciones_tj, balances=balances, fechas=fechas, form=form)

@app.route('/movimientos_mes/', defaults={'mes':datetime.now().strftime('%Y-%m')}, methods=['GET', 'POST'])
@app.route('/movimientos_mes/<string:mes>', methods=['GET'])
@login_required
def movimientos_mes(mes):
    # No form objects initialized here!
    # Just query your standard list metrics...
    meses = datetime.strptime(mes, '%Y-%m')
    fechas = {
        'mes_anterior': meses - relativedelta(months=1),
        'mes_actual': meses,
        'mes_siguiente': meses + relativedelta(months=1)
    }
    balances = saldos_mes_tarjeta(mes)
    operaciones_tj = movimientos_agrupados(mes)

    # for mov in Movimientos.query.all():
    #     print (mov)

    # m=Movimientos.query.filter(Movimientos.monto_operacion==1893).first()
    # if m:
    #     print(m.id, m.fecha_operacion, m.descripcion, m.monto_operacion, m.id_tipo_movimiento, m.id_tarjeta)
    #     db.session.delete(m)
    #     db.session.commit()

    return render_template('new_detalle_mes.html', 
                           fechas=fechas, 
                           balances=balances, 
                           operaciones_tj=operaciones_tj) # Form removed!

# @app.route('/modificar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
# @login_required
# def modificar_operacion(operacion_id):
#     operacion = Movimientos.query.get(operacion_id)
#     form = FormularioMovimientos()
#     if operacion:
#         if form.validate_on_submit():
#             mes = operacion.fecha_operacion.strftime('%Y-%m') 
#             if not mes: mes = datetime.now().strftime("%Y-%m")
#             operacion.fecha_operacion = form.fecha_operacion.data # hay que preparar un datepicker
#             operacion.descripcion = form.descripcion.data
#             operacion.monto_operacion = form.monto_operacion.data
#             operacion.id_tipo_movimiento = form.tipo_operacion.data
#             operacion.id_tarjeta = form.tarjeta.data
#             db.session.commit()
#             flash('Se modifico la operacion con exito.')
#             return redirect(url_for('movimientos_mes', mes=mes))
#         else:
#             for k, v in form.errors.items():
#                 flash('Error en: '+k)
#         form.fecha_operacion.data = operacion.fecha_operacion # hay que preparar un datepicker
#         form.descripcion.data = operacion.descripcion
#         form.monto_operacion.data = operacion.monto_operacion
#         form.tipo_operacion.data = operacion.tipo_movimiento.id
#         form.tarjeta.data = operacion.tarjeta.id
#         return render_template('modificar_operacion.html', form=form, operacion_id=operacion_id)
#     else:
#         flash('No se encontro la operacion a modificar.')
#     return redirect(url_for('index'))

@app.route('/modificar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
@login_required
def modificar_operacion(operacion_id):
    movimiento = Movimientos.query.get_or_404(operacion_id)
    
    # Assign row records straight from raw form fields
    movimiento.descripcion = request.form.get('descripcion')
    movimiento.monto_operacion = request.form.get('monto_operacion', type=int)
    movimiento.id_tipo_movimiento = request.form.get('id_tipo_movimiento', type=int)
    
    fecha_str = request.form.get('fecha_operacion')
    if fecha_str:
        movimiento.fecha_operacion = datetime.strptime(fecha_str, '%Y-%m-%d').date()

    db.session.commit()
    flash('Operación actualizada con éxito.', 'success')
    return redirect(url_for('movimientos_mes', mes=movimiento.fecha_operacion.strftime('%Y-%m')))

# @app.route('/borrar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
# @login_required
# def borrar_operacion(operacion_id):
#     operacion = Movimientos.query.get(operacion_id)
#     form = FormularioMovimientos()
#     if operacion:
#         form.fecha_operacion.data = operacion.fecha_operacion
#         form.descripcion.data = operacion.descripcion
#         form.monto_operacion.data = operacion.monto_operacion
#         form.tipo_operacion.data = operacion.tipo_movimiento.id
#         form.tipo_operacion_view.data = operacion.tipo_movimiento.tipo
#         form.tarjeta.data = operacion.tarjeta.id
#         form.tarjeta_view.data = operacion.tarjeta.banco
#         if form.validate_on_submit():
#             mes = operacion.fecha_operacion.strftime('%Y-%m') 
#             db.session.delete(operacion)
#             db.session.commit()
#             flash('Lista de movimientos actualizada.')
#             return redirect(url_for('movimientos_mes', mes=mes))
#         else:
#             for k, v in form.errors.items():
#                 flash('Error en: '+k)
#         return render_template('borrar_operacion.html', form=form, operacion_id=operacion_id)
#     else:
#         flash('No se encontro la operacion a eliminar.')
#     return redirect(url_for('index'))

@app.route('/borrar_operacion/<int:operacion_id>', methods=['GET', 'POST'])
@login_required
def borrar_operacion(operacion_id):
    movimiento = Movimientos.query.get_or_404(operacion_id)
    target_mes = movimiento.fecha_operacion.strftime('%Y-%m')
    
    db.session.delete(movimiento)
    db.session.commit()
    flash('Operación eliminada con éxito.', 'success')
    return redirect(url_for('movimientos_mes', mes=target_mes))

# @app.route('/nueva_operacion/<string:tarjeta>', methods=['GET', 'POST'])
# @login_required
# def nueva_operacion(tarjeta):
#     form = FormularioMovimientos()
#     if form.fecha_operacion.data is None:
#         form.fecha_operacion.data = datetime.today()
#     if tarjeta:
#         tj = db.session.query(Tarjetas).filter(Tarjetas.banco==tarjeta).first()
#         form.tarjeta.data=tj.id
#     else:
#         tj = db.session.query(Tarjetas).filter(Tarjetas.estado==True).first()
#     tarjeta = tj.banco
#     if form.validate_on_submit():
#         mes = form.fecha_operacion.data.strftime('%Y-%m') 
#         if not mes: mes = datetime.now().strftime("%Y-%m")
#         carga = Movimientos(date=datetime.utcnow(),
#                         fecha_operacion=form.fecha_operacion.data,
#                         descripcion=form.descripcion.data, 
#                         monto_operacion=form.monto_operacion.data,
#                         id_tipo_movimiento=form.tipo_operacion.data, 
#                         id_tarjeta=form.tarjeta.data)
#         db.session.add(carga)
#         db.session.commit()
#         if (form.tipo_operacion.data==10): # 10 es el id de pago
#             carga = GastosFijos(date=datetime.utcnow(),
#                             fecha_pagar=form.fecha_operacion.data,
#                             descripcion=form.descripcion.data, 
#                             monto=form.monto_operacion.data,
#                             operacion=False,
#                             pagado=True,
#                             id_agrupador_gastos=3)
#             db.session.add(carga)
#             db.session.commit()
#         flash('Nueva operacion agregada con exito.')
#         return redirect(url_for('movimientos_mes', mes=mes))
#     else:
#         for k, v in form.errors.items():
#             flash('Error en: '+k)
#     return render_template('nueva_operacion.html', form=form, id_tarjeta=tarjeta)

@app.route('/nueva_operacion/<string:tarjeta>', methods=['GET', 'POST'])
@login_required
def nueva_operacion(tarjeta):
    # 1. Look up target credit card ID via its text description name string
    tarjeta_obj = Tarjetas.query.filter_by(banco=tarjeta).first()
    if not tarjeta_obj:
        flash('Tarjeta no válida.', 'danger')
        return redirect(url_for('index'))

    # 2. Extract plain HTML input string fields directly from request body
    descripcion = request.form.get('descripcion')
    monto_operacion = request.form.get('monto_operacion', type=int)
    id_tipo_movimiento = request.form.get('id_tipo_movimiento', type=int)
    fecha_str = request.form.get('fecha_operacion')
    fecha_operacion = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else date.today()

    if id_tipo_movimiento == 10: # 10 es el id de pago
        gasto = GastosFijos(date=datetime.now(ZoneInfo("America/Asuncion")).replace(tzinfo=None),
                            fecha_pagar=datetime.strptime(request.form.get('fecha_operacion'), '%Y-%m-%d').date() if request.form.get('fecha_operacion') else date.today(),
                            descripcion=descripcion,            
                            monto=monto_operacion,
                            operacion=False,        
                            pagado=True,
                            id_agrupador_gastos=3)
        db.session.add(gasto)   
        # db.session.commit() # Commit deferred until after the main operation is added to ensure atomicity of related records
    # Safely convert HTML date string ('YYYY-MM-DD') into Python date object

    # 3. Instantiate database model row directly
    movimiento = Movimientos(
        date=datetime.now(ZoneInfo("America/Asuncion")).replace(tzinfo=None),
        fecha_operacion=fecha_operacion,
        descripcion=descripcion,
        monto_operacion=monto_operacion,
        id_tipo_movimiento=id_tipo_movimiento,
        id_tarjeta=tarjeta_obj.id  # Links item accurately to the container context
    )
    
    db.session.add(movimiento)
    db.session.commit()
    flash('Operación registrada con éxito.', 'success')
    
    # Redirect back to the view layer
    return redirect(url_for('movimientos_mes', mes=fecha_operacion.strftime('%Y-%m')))

@app.route('/aplicar_descuento/<int:operacion_id>', methods=['POST'])
@login_required
def aplicar_descuento(operacion_id):
    try:
        # Extract metadata from incoming HTML request form payload parameters
        porcentaje = float(request.form.get('porcentaje', 0))
        base_monto = float(request.form.get('base_monto', 0))
        base_fecha_str = request.form.get('base_fecha')
        base_tipo = request.form.get('base_tipo')
        base_descripcion = request.form.get('base_descripcion')
        id_tarjeta = request.form.get('id_tarjeta') # Capture original card assignment context

        if porcentaje <= 0 or porcentaje > 100:
            flash('Porcentaje de descuento inválido.', 'danger')
            return redirect(request.referrer or url_for('index'))

        # this must be a positive value to calculate the discount correctly, even if the original amount is negative (e.g., for expenses)
        monto_descuento = (abs(base_monto) * (porcentaje / 100.0))

        # Parse transaction execution date context
        fecha_operacion = datetime.strptime(base_fecha_str, '%Y-%m-%d').date() if base_fecha_str else date.today()

        # Custom descriptive indicator label
        nueva_descripcion = f"Descuento {int(porcentaje)}% - {base_descripcion}"

        # Instantiate dynamic model row entry binding card properties directly
        nuevo_movimiento = Movimientos(
            date=datetime.utcnow(),
            fecha_operacion=fecha_operacion,
            descripcion=nueva_descripcion,
            monto_operacion=int(round(monto_descuento)), # Store cleanly as integer units
            id_tipo_movimiento=18, #int(base_tipo) if base_tipo else None, fixed for type Descuento
            id_tarjeta=int(id_tarjeta) if id_tarjeta else None # Links directly to the same credit card card item
        )
        db.session.add(nuevo_movimiento)
        db.session.commit()
        
        flash(f'¡Descuento de {int(porcentaje)}% aplicado y restado del balance de la tarjeta!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar la inserción de descuento: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('index'))

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
    balance_mes = movimiento_balances_mes_a_mes(anno) # datos de movimientos agrupados por mes y banco
    months = sorted(list(set(item['mes'] for item in balance_mes))) # lista de meses en el balance
    banks = sorted(list(set(item['banco'] for item in balance_mes))) # lista de bancos en el balance
    restructured_data = {bank: {} for bank in banks} # reestructura los datos en un diccionario para facilitar el acceso
    for item in balance_mes:
        restructured_data[item['banco']][item['mes']] = item['saldo'] # agrupar banco y mes, y asignar el saldo
    monthly_totals = {month: 0 for month in months}
    for item in balance_mes:
        monthly_totals[item['mes']] += item['saldo'] # calcula el total mensual sumando los saldos de todos los bancos
    return render_template('historial_operaciones_anno.html', gastos=operaciones, data=restructured_data, months=months, monthly_totals=monthly_totals)

@app.route('/parametrico', methods=['GET', 'POST'])
@login_required
def parametrico():
    tipos_movimiento = TiposMovimiento.query.all()
    agrupador_gastos = AgrupadorGastos.query.all()
    gastos_fijos = DeudasPendientes.query.all()
    tarjetas = resumenes_tarjeta_macro() # Tarjetas.query.all()
    return render_template('new_parametrico.html', #'parametrico.html', 
                           tipos_movimiento=tipos_movimiento, 
                           agrupador_gastos=agrupador_gastos, 
                           gastos_fijos=gastos_fijos, 
                           tarjetas=tarjetas)

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
    # gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).order_by(GastosFijos.fecha_pagar).order_by(GastosFijos.id_agrupador_gastos).all()
    # gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).order_by(GastosFijos.fecha_pagar).order_by(GastosFijos.id).all()
    # gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).order_by(GastosFijos.fecha_pagar,GastosFijos.id_agrupador_gastos).all()
    gastos = GastosFijos.query.filter(func.strftime("%Y-%m", GastosFijos.fecha_pagar)==periodo).order_by(GastosFijos.fecha_pagar, GastosFijos.id).all()
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

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#     form = RegistrationForm()
#     if form.validate_on_submit():
#         user = User(username=form.username.data, email=form.email.data)
#         user.set_password(form.password.data)
#         db.session.add(user)
#         db.session.commit()
#         flash('Congratulations, you are now a registered user!')
#         return redirect(url_for('login'))
#     else:
#         for k, v in form.errors.items():
#             flash('Error en: '+k)
#     return render_template('register.html', title='Register', form=form)

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
        flash('Felicidades, el usuario ha sido creado existosamente!')
        return redirect(url_for('login'))
    else:
        for k, v in form.errors.items():
            flash('Error en: '+k)
    return render_template('new_register.html', title='Registrarse', form=form)


# @app.route('/modificar_pendiente/<int:pendiente_id>', methods=['GET', 'POST'])
# @login_required
# def modificar_pendiente(pendiente_id):
#     operacion = DeudasPendientes.query.get(pendiente_id)
#     form = FormularioPendientes()
#     if operacion:
#         if form.validate_on_submit():
#             operacion.descripcion = form.descripcion.data
#             operacion.monto = form.monto.data
#             operacion.estado = form.estado.data
#             operacion.cuotas = form.cuotas.data
#             operacion.cuotas_pagadas = form.cuotas_pagadas.data
#             operacion.id_agrupador = form.tipo.data
#             db.session.commit()
#             flash('Se modifico la operacion con exito.')
#             return redirect(url_for('parametrico'))
#         else:
#             for k, v in form.errors.items():
#                 flash('Error en: '+k)
#         form.descripcion.data = operacion.descripcion
#         form.monto.data = operacion.monto
#         form.estado.data = operacion.estado
#         form.cuotas.data = operacion.cuotas
#         form.cuotas_pagadas.data = operacion.cuotas_pagadas
#         form.tipo.data = operacion.id_agrupador
#         return render_template('modificar_pendientes.html', form=form, pendiente_id=pendiente_id)
#     else:
#         flash('No se encontro la operacion a modificar.')
#     return redirect(url_for('index'))

# @app.route('/borrar_pendiente/<int:pendiente_id>', methods=['GET', 'POST'])
# @login_required
# def borrar_pendiente(pendiente_id):
#     operacion = DeudasPendientes.query.get(pendiente_id)
#     form = FormularioPendientes()
#     if operacion:
#         form.descripcion.data = operacion.descripcion
#         form.monto.data = operacion.monto
#         form.estado.data = operacion.estado
#         form.cuotas.data = operacion.cuotas
#         form.cuotas_pagadas.data = operacion.cuotas_pagadas
#         form.tipo.data = operacion.id_agrupador
#         if form.validate_on_submit():
#             db.session.delete(operacion)
#             db.session.commit()
#             flash('Operacion pendiente eliminada.')
#             return redirect(url_for('parametrico'))
#         else:
#             for k, v in form.errors.items():
#                 flash('Error en: '+k)
#         return render_template('borrar_pendientes.html', form=form, pendiente_id=pendiente_id)
#     else:
#         flash('No se encontro la operacion a eliminar.')
#     return redirect(url_for('index'))   

# @app.route('/nuevo_pendiente', methods=['GET', 'POST'])
# @login_required
# def nuevo_pendiente():
#     form = FormularioPendientes()
#     if form.validate_on_submit():
#         operacion = DeudasPendientes(descripcion=form.descripcion.data,
#                         monto=form.monto.data, 
#                         estado=form.estado.data,
#                         cuotas=form.cuotas.data,
#                         cuotas_pagadas=form.cuotas_pagadas.data,
#                         id_agrupador=form.tipo.data)
#         db.session.add(operacion)
#         db.session.commit()
#         flash('Nuevo gasto pendiente agregado con exito.') 
#         return redirect(url_for('parametrico'))
#     else:
#         for k, v in form.errors.items():
#             flash('Error en: '+k)
#     return render_template('nuevo_pendiente.html', form=form)

# @app.route('/nueva_tarjeta', methods=['GET', 'POST'])
# @login_required
# def nueva_tarjeta():
#     form = FormularioTarjetas()
#     if form.validate_on_submit():
#         tarjeta = Tarjetas(
#                         banco=form.banco.data, 
#                         numero=form.numero.data, 
#                         vencimiento=form.vencimiento.data,
#                         estado=form.estado.data)
#         db.session.add(tarjeta)
#         db.session.commit()
#         flash('Nueva tarjeta agregada con exito.') 
#         return redirect(url_for('parametrico'))
#     else:
#         for k, v in form.errors.items():
#             flash('Error en: '+k)
#     return render_template('nueva_tarjeta.html', form=form)

# @app.route('/modificar_tarjeta/<int:tarjeta_id>', methods=['GET', 'POST'])
# @login_required
# def modificar_tarjeta(tarjeta_id):
#     operacion = Tarjetas.query.get(tarjeta_id)
#     form = FormularioTarjetas()
#     if operacion:
#         if form.validate_on_submit():
#             operacion.banco = form.banco.data
#             operacion.numero = form.numero.data
#             operacion.vencimiento = form.vencimiento.data
#             operacion.estado = form.estado.data
#             db.session.commit()
#             flash('Se modifico la tarjeta con exito.')
#             return redirect(url_for('parametrico'))
#         else:
#             for k, v in form.errors.items():
#                 flash('Error en: '+k)
#         form.banco.data = operacion.banco
#         form.numero.data = operacion.numero
#         form.vencimiento.data = operacion.vencimiento
#         form.estado.data = operacion.estado
#         return render_template('modificar_tarjeta.html', form=form, tarjeta_id=tarjeta_id)
#     else:
#         flash('No se encontro la tarjeta a modificar.')
#     return redirect(url_for('index'))

# @app.route('/borrar_tarjeta/<int:tarjeta_id>', methods=['GET', 'POST'])
# @login_required
# def borrar_tarjeta(tarjeta_id):
#     operacion = Tarjetas.query.get(tarjeta_id)
#     form = FormularioTarjetas()
#     if operacion:
#         form.banco.data = operacion.banco
#         form.numero.data = operacion.numero
#         form.vencimiento.data = operacion.vencimiento
#         form.estado.data = operacion.estado
#         if form.validate_on_submit():
#             db.session.delete(operacion)
#             db.session.commit()
#             flash('Tarjeta de credito eliminada.')
#             return redirect(url_for('parametrico'))
#         else:
#             for k, v in form.errors.items():
#                 flash('Error en: '+k)
#         return render_template('borrar_tarjeta.html', form=form, tarjeta_id=tarjeta_id)
#     else:
#         flash('No se encontro la tarjeta a eliminar.')
#     return redirect(url_for('index'))

# @app.route('/busqueda', methods=['GET', 'POST'])
# @login_required
# def busqueda():
#     debito = []
#     credito = []
#     form = FormularioBusqueda()
#     texto = request.args.get('q')
#     if texto:
#         debito = GastosFijos.query.filter(GastosFijos.descripcion.contains(texto)).order_by(GastosFijos.fecha_pagar.desc())
#         credito = Movimientos.query.filter(Movimientos.descripcion.contains(texto)).order_by(Movimientos.fecha_operacion.desc())
#     return render_template('busqueda.html', form=form, debito=debito, credito=credito)

# @app.route('/operaciones_tipo/<string:deudor>/<string:fecha>', methods=['GET', 'POST'])
# @login_required
# def operaciones_tipo(deudor, fecha): 
#     form = FormularioMovimientos()
#     operaciones = db.session.query(Movimientos).filter(Movimientos.id_tipo_movimiento==deudor).filter(Movimientos.id_tipo_movimiento==TiposMovimiento.id).filter(func.strftime("%Y", Movimientos.fecha_operacion)==fecha).order_by(Movimientos.id_tipo_movimiento).all()
#     return render_template('historico_operaciones_tipo.html', form=form, fecha=fecha, operaciones=operaciones)

# @app.route('/movimientos_anno_balance/', defaults={'anno':datetime.now().strftime('%Y')}, methods=['GET', 'POST'])
# @login_required
# def movimientos_anno_balance(anno):
#     # defaults={'anno':datetime.now().strftime('%Y')}
#     # meses = datetime.strptime(mes, '%Y-%m')
#     # fechas={'mes_anterior':meses-relativedelta(months=1), 'mes_actual':meses, 'mes_siguiente':meses+relativedelta(months=1)}
#     # operaciones_tj = movimientos_agrupados(mes)
#     # balances=saldos_mes_tarjeta(mes)
#     balance_anno = movimientos_anno_tarjeta_balance(anno)
#     # for balance in balance_anno:
#     #     for registro in balance:
#     #         print (registro)
#     return render_template('balance_anno_tarjeta.html', balance_anno=balance_anno)

#  DOCS: MODULO - CUENTAS => Vista histórica de gastos fijos agrupados por año y mes, con detalle de cada gasto, y métricas de deuda, crédito y disponibilidad para cada periodo 
@app.route('/gastos_fijos')
@app.route('/gastos_fijos/<int:anno>/<string:mes>')
def historico_gastos_fijos(anno=None, mes=None):
    hoy = datetime.now()
    if anno is None:
        anno = hoy.year
    if mes is None:
        mes = f"{hoy.month:02d}" # Formato string '05'

    periodo_activo = f"{anno}-{mes}"

    # 2. Obtener TODOS los gastos fijos de la base de datos ordenados por fecha
    # todos_los_gastos = GastosFijos.query.order_by(GastosFijos.id_agrupador_gastos, GastosFijos.id_agrupador_gastos.asc(), GastosFijos.fecha_pagar.desc()).all()

    # todos_los_gastos = GastosFijos.query.join(AgrupadorGastos, GastosFijos.id_agrupador_gastos == AgrupadorGastos.id).order_by(AgrupadorGastos.agrupador.asc(), GastosFijos.fecha_pagar.desc(), GastosFijos.id.desc()).all()
    todos_los_gastos = GastosFijos.query.outerjoin(AgrupadorGastos, GastosFijos.id_agrupador_gastos == AgrupadorGastos.id).order_by(AgrupadorGastos.agrupador.asc(), GastosFijos.fecha_pagar.desc(), GastosFijos.id.desc()).all()

    desglose_query = db.session.query(
        func.strftime('%m', Movimientos.date).label('mes'),
        TiposMovimiento.tipo.label('tipo_nombre'),
        func.sum(Movimientos.monto_operacion).label('subtotal')
    ).join(
        TiposMovimiento, Movimientos.id_tipo_movimiento == TiposMovimiento.id
    ).filter(
        func.strftime('%Y', Movimientos.date) == str(anno)
        # , condicion_deuda # Filtramos para que liste estrictamente gastos/deudas
    ).group_by(
        func.strftime('%m', Movimientos.date),
        TiposMovimiento.tipo
    ).all()
    
    # 3. Construir un árbol limpio de Años y Meses disponibles en la Base de Datos
    # Estructura resultante esperada: { 2026: ['01', '02', '05'], 2025: ['11', '12'] }
    menu_cronologico = {}
    for gasto in todos_los_gastos:
        g_anno = gasto.fecha_pagar.year
        g_mes = f"{gasto.fecha_pagar.month:02d}"
        
        if g_anno not in menu_cronologico:
            menu_cronologico[g_anno] = set()
        menu_cronologico[g_anno].add(g_mes)

    # Convertimos los sets internos a listas ordenadas
    for a in menu_cronologico:
        menu_cronologico[a] = sorted(list(menu_cronologico[a]))

    # 4. Filtrar los gastos específicos que corresponden SOLO al Año y Mes seleccionado
    gastos_del_mes = [
        g for g in todos_los_gastos 
        if g.fecha_pagar.year == anno and f"{g.fecha_pagar.month:02d}" == mes
    ]

    # Diccionario auxiliar de traducción para el Front-End
    meses_nombres = {
        '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
        '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
        '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
    }

    # Construir el string del periodo actual de forma segura (ej: "2026-05")
    # periodo_actual = f"{anno_activo}-{mes_activo:02d}"
    
    # Calcular las métricas para el mes en vista
    credito, deudas_impagas, deudas_pagadas = calcular_disponibilidad(periodo_activo)
    
    # Calcular un "Saldo Disponible" neto sugerido para mejorar el análisis
    saldo_disponible = credito - deudas_pagadas #- deudas_impagas
    
    lista_de_grupos = listar_agrupador()

    return render_template(
        'new_historico_gastos_fijos.html',
        menu_cronologico=menu_cronologico,
        gastos_del_mes=gastos_del_mes,
        anno_activo=anno,
        mes_activo=mes,
        agrupadores=lista_de_grupos,
        periodo_activo=periodo_activo,
        meses_nombres=meses_nombres,
        credito=credito,
        deudas_impagas=deudas_impagas,
        deudas_pagadas=deudas_pagadas,
        saldo_disponible=saldo_disponible
    )

#  DOCS: MODULO - TARJETAS => Movimientos de la tarjeta agrupados por año, con totales de deuda, pagos y descuentos, y calculo de deuda neta real
@app.route('/reporte/anual')
@login_required
def reporte_anual():
    # Extraemos el año de la columna 'date' usando strftime
    anno_extract = func.strftime('%Y', Movimientos.fecha_operacion)
    
    # Construimos las condiciones basadas en tus requerimientos:
    # Deuda: Todos excepto 10 y 18
        # 2. Reparación de las condiciones lógicas usando and_()
    condicion_deuda = and_(
        Movimientos.id_tipo_movimiento != 10, 
        Movimientos.id_tipo_movimiento != 18
    )
    condicion_pago = (Movimientos.id_tipo_movimiento == 10)
    condicion_descuento = (Movimientos.id_tipo_movimiento == 18)

    # 3. La query corregida (envolviendo las condiciones en una lista [] para evitar ambigüedades en case)
    reporte_query = db.session.query(
        func.strftime('%Y', Movimientos.date).label('anno'),
        func.sum(case([(condicion_deuda, Movimientos.monto_operacion)], else_=0)).label('total_deuda'),
        func.sum(case([(condicion_pago, Movimientos.monto_operacion)], else_=0)).label('total_pagos'),
        func.sum(case([(condicion_descuento, Movimientos.monto_operacion)], else_=0)).label('total_descuentos')
    ).group_by(func.strftime('%Y', Movimientos.date)).order_by(func.strftime('%Y', Movimientos.date).desc()).all()

    # Formateamos los resultados en una lista de diccionarios para Jinja2
    datos_anuales = []
    for r in reporte_query:
        # Deuda Neta Real = Deuda - Pagos - Descuentos
        deuda_neta = (r.total_deuda or 0) - (r.total_pagos or 0) - (r.total_descuentos or 0)
        
        datos_anuales.append({
            'anno': r.anno,
            'deuda': r.total_deuda or 0,
            'pagos': r.total_pagos or 0,
            'descuentos': r.total_descuentos or 0,
            'neto': deuda_neta
        })

    return render_template('new_reporte_anual_tarjeta.html', datos_anuales=datos_anuales)

#  DOCS: MODULO - TARJETAS => Reporte mensual de tarjeta con desglose de tarjeta por tipo de movimiento, y calculo de deuda neta real mes a mes
@app.route('/reporte_mensual/<int:anno>')
@login_required
def reporte_mensual(anno):
    # 1. Definimos las mismas condiciones exactas que blindamos en el reporte anual
    condicion_deuda = and_(
        Movimientos.id_tipo_movimiento != 10, 
        Movimientos.id_tipo_movimiento != 18
    )
    condicion_pago = (Movimientos.id_tipo_movimiento == 10)
    condicion_descuento = (Movimientos.id_tipo_movimiento == 18)

    # Query macro mensual (Totales globales por mes)
    reporte_query = db.session.query(
        func.strftime('%m', Movimientos.fecha_operacion).label('mes'),
        func.sum(case([(condicion_deuda, Movimientos.monto_operacion)], else_=0)).label('total_deuda'),
        func.sum(case([(condicion_pago, Movimientos.monto_operacion)], else_=0)).label('total_pagos'),
        func.sum(case([(condicion_descuento, Movimientos.monto_operacion)], else_=0)).label('total_descuentos')
    ).filter(
        func.strftime('%Y', Movimientos.fecha_operacion) == str(anno)
    ).group_by(
        func.strftime('%m', Movimientos.fecha_operacion)
    ).order_by(
        func.strftime('%m', Movimientos.fecha_operacion).asc()
    ).all()

    # 2. NUEVA QUERY OPTIMIZADA: Trae el desglose de gastos agrupados por mes y tipo de movimiento
    desglose_query = db.session.query(
        func.strftime('%m', Movimientos.fecha_operacion).label('mes'),
        TiposMovimiento.tipo.label('tipo_nombre'),
        func.sum(Movimientos.monto_operacion).label('subtotal')
    ).join(
        TiposMovimiento, Movimientos.id_tipo_movimiento == TiposMovimiento.id
    ).filter(
        func.strftime('%Y', Movimientos.fecha_operacion) == str(anno)
        # , condicion_deuda # Filtramos para que liste estrictamente gastos/deudas
    ).group_by(
        func.strftime('%m', Movimientos.fecha_operacion),
        TiposMovimiento.tipo
    ).all()

    # Organizar los desgloses en un diccionario indexado por mes {'01': [...], '02': [...]}
    desglose_por_mes = {}
    for d in desglose_query:
        if d.mes not in desglose_por_mes:
            desglose_por_mes[d.mes] = []
        desglose_por_mes[d.mes].append({
            'tipo_nombre': d.tipo_nombre,
            'subtotal': d.subtotal
        })

    # Mapeo para mostrar nombres de meses legibles
    meses_nombre = {
        '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
        '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
        '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
    }

    # 3. CONSTRUCCIÓN DE LA ESTRUCTURA FINAL PARA JINJA2
    # Procesamos los datos calculando el neto y adjuntando su desglose correspondiente
    reporte_procesado = []
    for registro in reporte_query:
        t_deuda = registro.total_deuda or 0
        t_pagos = registro.total_pagos or 0
        t_descuentos = registro.total_descuentos or 0
        neto = t_deuda - t_pagos - t_descuentos

        reporte_procesado.append({
            'mes_id': registro.mes,  # Ej: '01'
            'mes_nombre': meses_nombre.get(registro.mes, registro.mes),
            'total_deuda': t_deuda,
            'total_pagos': t_pagos,
            'total_descuentos': t_descuentos,
            'neto': neto,
            'desglose': desglose_por_mes.get(registro.mes, []) # Lista de gastos de este mes
        })

    return render_template(
        'new_reporte_mensual_tarjeta.html', 
        reporte=reporte_procesado, 
        anno=anno,
        meses_nombre=meses_nombre
    )

# DOCS: MODULO - COMBUSTIBLE => Reporte anual de combustible con cálculo de litros, rendimiento y duración entre cargas
@app.route('/combustible/reporte-anual')
def reporte_anual_combustible():
    # 1. Traer todas las cargas ordenadas por fecha de manera descendente
    cargas_raw = Cargas.query.order_by(Cargas.fecha_carga.desc()).all()
    
    # Mapeo de meses en español
    meses_nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    
    # Estructura de agrupación intermedia: { año: { mes_num: [ lista_de_recargas ] } }
    datos_agrupados = {}
    
    # Procesar de forma cronológica inversa para armar la estructura anidada
    for idx, c in enumerate(cargas_raw):
        if not c.fecha_carga:
            continue
            
        anno = c.fecha_carga.year
        mes_num = c.fecha_carga.month
        
        if anno not in datos_agrupados:
            datos_agrupados[anno] = {}
        if mes_num not in datos_agrupados[anno]:
            datos_agrupados[anno][mes_num] = []
            
        # Calcular los Litros dinámicamente: monto_carga / precio
        litros = (c.monto_carga / c.precio) if (c.precio and c.precio > 0) else 0.0
        
        # --- CÁLCULO DE MÉTRICAS COMPLEMENTARIAS ENTRE CARGAS ---
        # Buscamos la carga cronológicamente anterior (que estará más adelante en nuestra lista 'cargas_raw' por el .desc())
        carga_anterior = None
        if idx + 1 < len(cargas_raw):
            carga_anterior = cargas_raw[idx + 1]
            
        # Duración en días
        duracion_dias = (c.fecha_carga - carga_anterior.fecha_carga).days if carga_anterior else 0
        
        # Rendimiento Consumo por cada 100Km
        recorrido_100km = 0.0
        if carga_anterior and c.odometro and carga_anterior.odometro:
            kms_recorridos = c.odometro - carga_anterior.odometro
            if kms_recorridos > 0:
                # Fórmula estándar: (Litros consumidos / Kilómetros recorridos) * 100
                recorrido_100km = (litros / kms_recorridos) * 100

        # Si el cálculo da 0 o no hay historial anterior, dejamos un promedio base estimado (ej: 8.5 L/100Km)
        if recorrido_100km <= 0:
            recorrido_100km = 8.5
            
        datos_agrupados[anno][mes_num].append({
            "id": c.id,
            "fecha": c.fecha_carga,
            "emblema": c.emblema if c.emblema else "Sin Emblema",
            "precio": c.precio if c.precio else 0,
            "odometro": c.odometro if c.odometro else 0,
            "monto": c.monto_carga if c.monto_carga else 0,
            "litros": litros,
            "recorrido_100km": recorrido_100km,
            "duracion_dias": duracion_dias if duracion_dias > 0 else 7  # Fallback si es el primer registro
        })

    # 2. Compilar la lista estructurada final ("items") requerida por la vista Jinja
    items = []
    
    for anno in sorted(datos_agrupados.keys(), reverse=True):
        total_inversion = 0
        total_litros = 0.0
        total_recargas = 0
        suma_recorrido_100km = 0.0
        
        lista_meses_items = []
        
        # Ordenar meses de Diciembre a Enero
        for mes_num in sorted(datos_agrupados[anno].keys(), reverse=True):
            recargas_del_mes = datos_agrupados[anno][mes_num]
            
            for rec in recargas_del_mes:
                total_inversion += rec["monto"]
                total_litros += rec["litros"]
                total_recargas += 1
                suma_recorrido_100km += rec["recorrido_100km"]
                
            lista_meses_items.append({
                "nombre_mes": meses_nombres[mes_num],
                "recargas": recargas_del_mes
            })
            
        # Calcular los promedios globales anuales para las tarjetas principales del año
        promedio_litros_recarga = (total_litros / total_recargas) if total_recargas > 0 else 0.0
        consumo_100_km = (suma_recorrido_100km / total_recargas) if total_recargas > 0 else 0.0
        
        # Autonomía estimada del tanque basado en el consumo anual (Ej: con un tanque promedio lleno de 50L)
        distancia_por_tanque = (50 / consumo_100_km * 100) if consumo_100_km > 0 else 0.0

        # Mapear los datos a un contenedor estructurado por atributos independientes
        class AñoResumen:
            pass
            
        item = AñoResumen()
        item.anno = anno
        item.total_inversion = total_inversion
        item.total_litros = total_litros
        item.promedio_litros_recarga = promedio_litros_recarga
        item.distancia_por_tanque = distancia_por_tanque
        item.consumo_100_km = consumo_100_km
        item.total_recargas = total_recargas
        item.meses = lista_meses_items
        
        items.append(item)

    return render_template('new_reporte_anual_combustible.html', items=items)

# DOCS: MODULO - COMBUSTIBLE => Reporte mensual de combustible con cálculo de litros, rendimiento y duración entre cargas, agrupado por mes dentro del año seleccionado
@app.route('/reporte_combustible_mensual/<int:anno>')
@login_required
def reporte_combustible_mensual(anno):
    # Agrupamos por mes utilizando 'fecha_carga' (o 'date', según prefieras)
    return render_template(
        'new_reporte_mensual_combustible.html'
    )

@app.route('/buscar', methods=['GET'])
def buscar_movimientos():
    query = request.args.get('q', '').strip()
    
    resultados_gastos = []
    resultados_tarjetas = []
    
    if query:
        # Búsqueda adaptativa en Gastos Fijos (Expenses)
        resultados_gastos = GastosFijos.query.filter(
            GastosFijos.descripcion.ilike(f"%{query}%")
        ).order_by(GastosFijos.fecha_pagar.desc()).all()
        
        # Búsqueda adaptativa en Movimientos (Credit Card)
        resultados_tarjetas = Movimientos.query.filter(
            Movimientos.descripcion.ilike(f"%{query}%")
        ).order_by(Movimientos.fecha_operacion.desc()).all()
        
    return render_template(
        'new_buscar.html', 
        query=query, 
        resultados_gastos=resultados_gastos, 
        resultados_tarjetas=resultados_tarjetas
    )

# DOCS: MODULO - CUENTAS => Gráfica histórica de gastos fijos agrupados por categoría, mostrando la evolución del monto total por categoría a lo largo del tiempo
@app.route('/reporte/historico-categorias')
@login_required
def grafica_historica_categorias():
    # Extraer todos los años únicos que existen en tus gastos para llenar el `<select>`
    anios_db = db.session.query(func.extract('year', GastosFijos.fecha_pagar)).distinct().order_by(desc(func.extract('year', GastosFijos.fecha_pagar))).all()
    anios_disponibles = [int(a[0]) for a in anios_db if a[0] is not None]
    
    return render_template('new_grafico_historico.html', anios=anios_disponibles)

# DOCS: MODULO - COMBUSTIBLE => Gráfica de tendencia de consumo de combustible a lo largo del tiempo, mostrando la evolución del rendimiento (litros por cada 100km) y la duración entre cargas
@app.route('/reporte/tendencia-combustible')
@login_required
def grafica_tendencia_combustible():
    # Solo renderiza la vista HTML base
    return render_template('new_grafico_cargas.html')


# DOCS: MODULO - TARJETAS => Endpoint para renderizar la vista de la gráfica de Composición de Deuda
@app.route('/reporte/composicion-deuda')
@login_required
def grafica_composicion_deuda():
    # Extraer todos los años distintos que tienen movimientos registrados
    años_raw = db.session.query(func.strftime('%Y', Movimientos.fecha_operacion))\
                         .filter(Movimientos.fecha_operacion.isnot(None))\
                         .distinct()\
                         .order_by(func.strftime('%Y', Movimientos.fecha_operacion).desc())\
                         .all()
    anios = [a[0] for a in años_raw if a[0]]
    print("Años disponibles para la gráfica de composición de deuda:", anios)  # Debug: Verificar los años extraídos
    return render_template('new_grafico_movimientos.html', anios=anios)



# API ENDPOINTS
# DOCS: MODULO - CUENTAS => Actualiza un gasto fijo específico con datos enviados desde un formulario modal en la interfaz de usuario.
@app.route('/api/gastos/editar/<int:id>', methods=['POST'])
@login_required
def api_editar_gasto(id):


    try:
        gasto = GastosFijos.query.get_or_404(id)
        # 1. Capturar datos modificados del formulario
        fecha_str = request.form.get('fecha_pagar')
        gasto.descripcion = request.form.get('descripcion')
        gasto.monto = float(request.form.get('monto'))
        gasto.id_agrupador_gastos = int(request.form.get('agrupador')) if request.form.get('agrupador') else None
        
        # Procesar los switches booleanos
        gasto.operacion = 'operacion' in request.form  # True si está marcado, False si no
        gasto.pagado = 'pagado' in request.form        # True si está marcado, False si no

        if fecha_str:
            gasto.fecha_pagar = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        db.session.commit()
        flash('Registro actualizado correctamente.', 'success')

        # 2. ASEGURAR QUE EL MES TENGA RELLENO DE CERO A LA IZQUIERDA (:02d)
        anno_destino = gasto.fecha_pagar.year
        mes_destino = f"{gasto.fecha_pagar.month:02d}"  # Convierte 5 -> "05", 11 -> "11"

        # Redirección consistente a la visualización del histórico objetivo
        return redirect(url_for('historico_gastos_fijos', anno=anno_destino, mes=mes_destino))

    except Exception as e:
        db.session.rollback()
        flash(f"Error al modificar el registro: {str(e)}", "danger")
        return redirect(request.referrer or url_for('historico_gastos_fijos'))    
      
# DOCS: MODULO - CUENTAS => Borrar un gasto fijo específico con una solicitud POST desde un formulario modal en la interfaz de usuario.
@app.route('/api/gastos/borrar/<int:id>', methods=['POST'])
def api_borrar_gasto(id):
    gasto = GastosFijos.query.get_or_404(id)
    
    try:
        # Eliminar el registro de forma segura
        db.session.delete(gasto)
        db.session.commit()
        
        # Redireccionar de vuelta a la misma vista histórica donde estaba el usuario
        return redirect(request.referrer or url_for('historico_gastos_fijos'))
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# DOCS: MODULO - CUENTAS => Cambiar el estado de pago de un gasto fijo específico (pagado/no pagado) con una solicitud POST desde un formulario modal en la interfaz de usuario.
@app.route('/api/gastos/cambiar-estado/<int:id>', methods=['POST'])
def api_cambiar_estado_gasto(id):
    gasto = GastosFijos.query.get_or_404(id)
    
    try:
        # Obtener los datos JSON enviados por el cliente
        data = request.get_json() or {}
        
        # Soportamos tanto la clave 'pagado' como 'estado' por consistencia
        nuevo_estado = data.get('pagado', data.get('estado'))
        
        if nuevo_estado is None:
            return jsonify({'success': False, 'error': 'Falta el parámetro de estado'}), 400
            
        # Forzar conversión explícita a Booleano en Python (True/False)
        gasto.pagado = bool(nuevo_estado)
        
        # Confirmar en la base de datos
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'id': gasto.id, 
            'nuevo_estado': gasto.pagado
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
#  DOCS: MODULO - CUENTAS => Precargar automáticamente los gastos fijos para un mes específico basado en las deudas pendientes activas, con una solicitud POST desde un formulario en la interfaz de usuario.
@app.route('/api/gastos/generar-siguiente-mes', methods=['POST'])
def api_generar_siguiente_mes():
    try:
        # 1. Encontrar el último gasto cargado en el sistema para saber el "último mes"
        ultimo_gasto = GastosFijos.query.order_by(GastosFijos.fecha_pagar.desc()).first()
        
        if ultimo_gasto:
            # Si hay gastos, nos basamos en el año y mes de ese último registro
            ultimo_periodo = ultimo_gasto.fecha_pagar
            # Avanzamos al primer día del mes siguiente de forma matemática simple
            if ultimo_periodo.month == 12:
                fecha_objetivo = datetime(ultimo_periodo.year + 1, 1, 1).date()
            else:
                fecha_objetivo = datetime(ultimo_periodo.year, ultimo_periodo.month + 1, 1).date()
        else:
            # Si la base de datos está totalmente vacía, inicializamos con el mes actual
            fecha_objetivo = datetime.utcnow().date().replace(day=1)

        anno_destino = fecha_objetivo.year
        mes_destino = f"{fecha_objetivo.month:02d}"

        # 2. Traer las deudas activas para clonarlas en el nuevo mes
        deudas = DeudasPendientes.query.filter(DeudasPendientes.estado == True).all()
        
        for deuda in deudas:
            descontado = False
            operacion = False 
            
            # Control e incremento de cuotas
            if deuda.cuotas > 0:
                deuda.cuotas_pagadas += 1
                db.session.add(deuda)
                
            # Regla de auto-pagado para ciertos servicios fijos
            if deuda.descripcion in ['DESCUENTO IPS', 'SERVICIOS TELEFONIA', 'INTERNET & TV', 'S24']: 
                descontado = True
                operacion = False 
            if deuda.descripcion in ['REFERENCIA']:
                descontado = True
                operacion = True
            # Formatear el texto de cuotas si corresponde
            string_cuotas = f" (Cuota {deuda.cuotas_pagadas} de {deuda.cuotas}, monto cuota: Gs. {deuda.monto:,.0f})" if deuda.cuotas > 0 else ""

            
            nueva_descripcion = f"{deuda.descripcion}{string_cuotas}"  # Formateo con puntos como separadores de miles
            

            # Crear registro en GastosFijos
            nuevo_gasto = GastosFijos(
                date=datetime.utcnow(),
                fecha_pagar=fecha_objetivo, # Cae el 1 de ese mes
                descripcion=nueva_descripcion,
                monto=deuda.monto,
                operacion=operacion,
                pagado=descontado,
                id_agrupador_gastos=deuda.id_agrupador
            )

            db.session.add(nuevo_gasto)
            
        db.session.commit()
        
        flash(f"¡Éxito! Se generó el periodo {fecha_objetivo.strftime('%B %Y')} correctamente.", "success")
        
        # Redireccionamos al usuario directo a ver el nuevo mes creado
        return redirect(url_for('historico_gastos_fijos', anno=anno_destino, mes=mes_destino))
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
#  DOCS: MODULO - CUENTAS => Crear un nuevo gasto fijo con los datos enviados desde un formulario modal en la interfaz de usuario.
@app.route('/api/gastos/crear', methods=['POST'])
def api_crear_gasto():
    try:
        # 1. Capturar datos crudos del formulario del Modal
        fecha_str = request.form.get('fecha_pagar')
        descripcion = request.form.get('descripcion')
        monto_raw = request.form.get('monto')
        id_agrupador = request.form.get('id_agrupador_gastos')
        
        # Checkboxes (si no se marcan, el navegador no los envía, por eso validamos con 'in request.form')
        operacion = 'operacion' in request.form 
        pagado = 'pagado' in request.form

        # 2. Validaciones básicas obligatorias
        if not fecha_str or not descripcion or not monto_raw:
            flash("Error: Todos los campos obligatorios deben completarse.", "danger")
            return redirect(request.referrer or url_for('historico_gastos_fijos'))

        # Conversiones de tipos seguros
        fecha_pagar = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        # Extraemos año y mes asegurando que el mes tenga 2 dígitos (relleno con cero)
        anno_destino = fecha_pagar.year
        mes_destino = f"{fecha_pagar.month:02d}"
        monto = float(monto_raw)

        # 3. Instanciar y guardar en la Base de Datos
        nuevo_gasto = GastosFijos(
            date=datetime.utcnow(),
            fecha_pagar=fecha_pagar,
            descripcion=descripcion,
            monto=monto,
            operacion=operacion,
            pagado=pagado,
            id_agrupador_gastos=int(id_agrupador) if id_agrupador else None
        )
        
        db.session.add(nuevo_gasto)
        db.session.commit()
        
        flash('Nueva operación agregada con éxito.', 'success')
        
        # Redireccionar de forma inteligente al Año y Mes del elemento recién creado
        return redirect(url_for('historico_gastos_fijos', anno=anno_destino, mes=mes_destino))

    except Exception as e:
        db.session.rollback()
        flash(f"Error al guardar el registro: {str(e)}", "danger")
        return redirect(request.referrer or url_for('historico_gastos_fijos'))
    
# DOCS: MODULO - CUENTAS => Obtener el desglose detallado de gastos fijos para un agrupador específico y un periodo de pago determinado, con una solicitud GET desde la interfaz de usuario utilizando jQuery para actualizar dinámicamente la información mostrada.
@app.route('/api/gastos/desglose-agrupador', methods=['GET'])
@login_required
def api_desglose_agrupador():
    try:
        # 1. Extraer variables de consulta enviados por jQuery
        id_agrupador = request.args.get('id_agrupador')
        anno = request.args.get('anno', type=int)
        mes = request.args.get('mes', type=int)
        
        if not id_agrupador or not anno or not mes:
            return jsonify({'success': False, 'error': 'Parámetros incompletos.'}), 400

        # Formatear el periodo clave (Ej: "2026-05")
        periodo_objetivo = f"{anno}-{mes:02d}"

        # 2. Query filtrada por agrupador de gastos y periodo específico de pago
        registros = GastosFijos.query.filter(
            GastosFijos.id_agrupador_gastos == id_agrupador,
            func.strftime("%Y-%m", GastosFijos.fecha_pagar) == periodo_objetivo
        ).order_by(GastosFijos.fecha_pagar.asc()).all()

        # 3. Serializar los objetos del modelo a diccionarios planos
        datos_json = []
        for g in registros:
            datos_json.append({
                'id': g.id,
                'descripcion': g.descripcion,
                'monto': float(g.monto),
                'fecha_pagar': g.fecha_pagar.strftime('%d/%m/%Y'), # Formato de lectura amigable para PY
                'pagado': g.pagado,
                'operacion': g.operacion
            })

        return jsonify({'success': True, 'data': datos_json}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# DOCS: MODULO - COMBUSTIBLE => Modificar una carga de combustible específica con datos enviados desde un formulario modal en la interfaz de usuario.
@app.route('/api/combustible/modificar/<int:id>', methods=['POST'])
@login_required  # Descomenta si usas Flask-Login
def api_modificar_combustible(id):
    print(f"Recibida solicitud de modificación para Carga ID: {id}")
    try:
        # 1. Buscar el registro exacto usando get_or_404 por seguridad
        carga = Cargas.query.get_or_404(id)
        
        # 2. Extraer y procesar la fecha del formulario (viene como 'YYYY-MM-DD')
        fecha_str = request.form.get('fecha_carga')
        if fecha_str:
            carga.fecha_carga = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
        # 3. Extraer y convertir los valores numéricos y de texto
        carga.odometro = int(request.form.get('odometro', carga.odometro))
        carga.emblema = request.form.get('emblema', carga.emblema).strip()
        carga.precio = int(request.form.get('precio', carga.precio))
        carga.monto_carga = int(request.form.get('monto_carga', carga.monto_carga))
        
        # 4. Guardar los cambios en la base de datos de forma segura
        db.session.commit()
        flash('Recarga de combustible actualizada correctamente.', 'success')
        
    except ValueError as ve:
        # Captura errores si los números o la fecha vienen con un formato incorrecto
        db.session.rollback()
        flash('Error en el formato de los datos ingresados.', 'danger')
        
    except SQLAlchemyError  as e:
        # Captura cualquier error nativo de la base de datos
        db.session.rollback()
        flash('Error al actualizar la base de datos.', 'danger')
        
    # 5. Redirigir siempre de regreso al historial anual
    return redirect(url_for('reporte_anual_combustible'))

#  DOCS: MODULO - AJUSTES => Endpoint unificado para crear y editar registros paramétricos (Tipos, Agrupadores, Tarjetas, Fijos) con una sola ruta y lógica compartida. Reemplaza las acciones POST tradicionales de cada entidad y simplifica el mantenimiento del código.
@app.route('/api/parametrico/guardar', methods=['POST'])
@login_required
def api_guardar_parametrico():
    """
    Endpoint unificado para crear y editar registros paramétricos (Tipos, Agrupadores, Tarjetas, Fijos).
    Reemplaza la acción POST tradicional.
    """
    try:
        origen = request.form.get('origen')
        accion = request.form.get('accion') # 'nuevo' o 'editar'
        id_registro = request.form.get('id')

        if not origen or not accion:
            return jsonify({'success': False, 'error': 'Parámetros origen o acción faltantes.'}), 400

        # --- Manejo de TIPOS DE MOVIMIENTOS ---
        if origen == 'TIPOS':
            tipo_nombre = request.form.get('tipo')
            if not tipo_nombre:
                return jsonify({'success': False, 'error': 'Falta el nombre del tipo.'}), 400
            
            if accion == 'nuevo':
                nuevo_tipo = TiposMovimiento(tipo=tipo_nombre)
                db.session.add(nuevo_tipo)
            elif accion == 'editar':
                reg = TiposMovimiento.query.get(id_registro)
                if reg: reg.tipo = tipo_nombre

        # --- Manejo de AGRUPADORES DE GASTOS ---
        elif origen == 'AGRUPADORES':
            agrupador_nombre = request.form.get('agrupador')
            if not agrupador_nombre:
                return jsonify({'success': False, 'error': 'Falta el nombre del agrupador.'}), 400
            
            if accion == 'nuevo':
                nuevo_agrupador = AgrupadorGastos(agrupador=agrupador_nombre)
                db.session.add(nuevo_agrupador)
            elif accion == 'editar':
                reg = AgrupadorGastos.query.get(id_registro)
                if reg: reg.agrupador = agrupador_nombre

        # --- Manejo de TARJETAS DE CRÉDITO ---
        elif origen == 'TARJETAS':
            banco = request.form.get('banco')
            numero = request.form.get('numero')
            vencimiento = request.form.get('vencimiento')
            estado = request.form.get('estado') == 'true' # Evaluación booleana

            if not banco or not numero:
                return jsonify({'success': False, 'error': 'Datos de tarjeta incompletos.'}), 400

            if accion == 'nuevo':
                nueva_tarjeta = Tarjetas(banco=banco, numero=numero, vencimiento=vencimiento, estado=estado)
                db.session.add(nueva_tarjeta)
            elif accion == 'editar':
                reg = Tarjetas.query.get(id_registro)
                if reg:
                    reg.banco = banco
                    reg.numero = numero
                    reg.vencimiento = vencimiento
                    reg.estado = estado

        # --- Manejo de GASTOS FIJOS / PENDIENTES ---
        elif origen == 'FIJOS':
            descripcion = request.form.get('descripcion')
            monto = request.form.get('monto', type=float)
            cuotas = request.form.get('cuotas', type=int)
            cuotas_pagadas = request.form.get('cuotas_pagadas', type=int)
            estado = request.form.get('estado') == 'true'


            if not descripcion or monto is None:
                return jsonify({'success': False, 'error': 'Datos de compromiso financiero incompletos.'}), 400

            if accion == 'nuevo':
                nuevo_fijo = DeudasPendientes(
                    descripcion=descripcion, monto=monto, cuotas=cuotas, 
                    cuotas_pagadas=cuotas_pagadas, estado=estado
                )
                db.session.add(nuevo_fijo)
            elif accion == 'editar':
                reg = DeudasPendientes.query.get(id_registro)
                if reg:
                    reg.descripcion = descripcion
                    reg.monto = monto
                    reg.cuotas = cuotas
                    reg.cuotas_pagadas = cuotas_pagadas
                    reg.estado = estado


        db.session.commit()
        return jsonify({'success': True, 'msg': 'Registro procesado correctamente.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

#  DOCS: MODULO - AJUSTES => Endpoint unificado para eliminar registros paramétricos (Tipos, Agrupadores, Tarjetas, Fijos) con una sola ruta y lógica compartida. Reemplaza las acciones POST tradicionales de eliminación de cada entidad y simplifica el mantenimiento del código.
@app.route('/api/parametrico/eliminar', methods=['POST'])
@login_required
def api_eliminar_parametrico():
    """
    Endpoint único para la eliminación de registros por AJAX.
    Reemplaza rutas como borrar_tarjeta, borrar_pendiente, etc.
    """
    try:
        origen = request.json.get('origen') # Pasado vía JSON body
        id_registro = request.json.get('id')

        if not origen or not id_registro:
            return jsonify({'success': False, 'error': 'Parámetros insuficientes para la eliminación.'}), 400

        if origen == 'TIPOS':
            reg = TiposMovimiento.query.get(id_registro)
        elif origen == 'AGRUPADORES':
            reg = AgrupadorGastos.query.get(id_registro)
        elif origen == 'TARJETAS':
            reg = Tarjetas.query.get(id_registro)
        elif origen == 'FIJOS':
            reg = DeudasPendientes.query.get(id_registro)
        else:
            return jsonify({'success': False, 'error': 'Origen de datos no válido.'}), 400

        if not reg:
            return jsonify({'success': False, 'error': 'El registro no existe o ya fue eliminado.'}), 404

        db.session.delete(reg)
        db.session.commit()
        return jsonify({'success': True, 'msg': 'Registro eliminado exitosamente.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    
#  DOCS: MODULO - CUENTAS => Endpoint para obtener los datos necesarios para construir una gráfica histórica de gastos fijos por categoría, con la capacidad de filtrar por año específico o mostrar el histórico completo, utilizando una solicitud GET desde la interfaz de usuario y devolviendo los datos en formato JSON para su consumo dinámico con JavaScript.
@app.route('/api/reporte/grafica-categorias')
@login_required
def api_grafica_categorias():
    anno_filtro = request.args.get('anno', 'all')
    
    # Consulta base: Solo egresos (operacion == False)
    query = db.session.query(
        AgrupadorGastos.agrupador,
        func.sum(GastosFijos.monto).label('total_historico')
    ).join(
        GastosFijos, GastosFijos.id_agrupador_gastos == AgrupadorGastos.id
    ).filter(
        GastosFijos.operacion == False 
    )
    
    # Aplicar el filtro de año si el usuario no seleccionó "Histórico Completo"
    if anno_filtro and anno_filtro != 'all':
        query = query.filter(func.extract('year', GastosFijos.fecha_pagar) == int(anno_filtro))
        
    resultados = query.group_by(AgrupadorGastos.agrupador).order_by(func.sum(GastosFijos.monto).desc()).all()
    
    # Empaquetar para JSON
    etiquetas = [fila.agrupador for fila in resultados]
    valores = [float(fila.total_historico) for fila in resultados]
    
    return jsonify({'success': True, 'etiquetas': etiquetas, 'valores': valores})

# DOCS: MODULO - COMBUSTIBLE => Endpoint para obtener los datos necesarios para construir una gráfica de consumo de combustible a lo largo del tiempo, calculando el rendimiento en litros por cada 100 km entre cargas sucesivas, utilizando una solicitud GET desde la interfaz de usuario y devolviendo los datos en formato JSON para su consumo dinámico con JavaScript.
@app.route('/api/reporte/grafica-cargas')
@login_required
def api_grafica_cargas():
    # 1. Obtener todas las cargas en orden cronológico ascendente (de más vieja a más nueva)
    cargas_raw = Cargas.query.order_by(Cargas.fecha_carga.asc()).all()
    
    etiquetas_fechas = []
    valores_consumo = []
    detalles_emblemas = []
    
    odometro_anterior = None
    
    for c in cargas_raw:
        if not c.fecha_carga or not c.precio or c.precio <= 0:
            continue
            
        # Calcular los litros cargados
        litros = c.monto_carga / c.precio
        
        # Solo podemos calcular el consumo si existe un kilometraje anterior válido
        if odometro_anterior and c.odometro and c.odometro > odometro_anterior:
            distancia_recorrida = c.odometro - odometro_anterior
            
            if distancia_recorrida > 0:
                consumo_100km = (litros / distancia_recorrida) * 100
                
                # Ignorar consumos irreales (ej. errores de tipeo en el odómetro > 30L/100km)
                if 0 < consumo_100km < 30: 
                    etiquetas_fechas.append(c.fecha_carga.strftime('%d/%m/%Y'))
                    valores_consumo.append(round(consumo_100km, 2))
                    detalles_emblemas.append(c.emblema if c.emblema else 'Sin Emblema')
        
        # Actualizar el odómetro para la siguiente iteración del bucle
        if c.odometro:
            odometro_anterior = c.odometro

    return jsonify({
        'success': True,
        'fechas': etiquetas_fechas,
        'consumos': valores_consumo,
        'emblemas': detalles_emblemas
    })

# DOCS: MODULO - MOVIMIENTOS => API para obtener los datos agregados por mes (Consumos vs Pagos/Descuentos)
@app.route('/api/reporte/grafica-composicion-deuda')
@login_required
def api_grafica_composicion_deuda():
    # Capturamos el año enviado por el frontend (por defecto el actual)
    anno_filtro = request.args.get('anno', str(datetime.now().year))
    
    query = Movimientos.query
    
    # Aplicar el filtro a menos que el usuario seleccione "Histórico Completo" ('all')
    if anno_filtro != 'all':
        query = query.filter(func.strftime('%Y', Movimientos.fecha_operacion) == str(anno_filtro))
        
    movimientos_raw = query.order_by(Movimientos.fecha_operacion.asc()).all()
    print(f"Movimientos obtenidos para el año {anno_filtro}: {len(movimientos_raw)} registros")  # Debug: Verificar la cantidad de movimientos obtenidos    
    
    etiquetas_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    valores_consumos = [0] * 12
    valores_pagos = [0] * 12
    valores_descuentos = [0] * 12
    
    for mov in movimientos_raw:
        if not mov.fecha_operacion or not mov.monto_operacion:
            continue
            
        mes_index = mov.fecha_operacion.month - 1
        monto = float(mov.monto_operacion)
        
        if mov.id_tipo_movimiento == 10:
            valores_pagos[mes_index] += monto
        elif mov.id_tipo_movimiento == 18:
            valores_descuentos[mes_index] += monto
        else:
            valores_consumos[mes_index] += monto

    return jsonify({
        'success': True,
        'labels': etiquetas_meses,
        'consumos': valores_consumos,
        'pagos': valores_pagos,
        'descuentos': valores_descuentos
    })