from main import app, db
from flask import render_template, redirect, url_for, flash, get_flashed_messages, request
# import forms
from models import Cargas
from datetime import datetime
# import random
# import ast
# import pytz

# def recuperar_lista(equipos):
#     distribuidos  = []
#     for team in equipos:
#         plantel = []
#         for player in team:
#             jugador = Jugador.query.get(player)
#             plantel.append(jugador)
#         distribuidos.append(plantel)
#     return distribuidos

@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
def index():
    # jugadores = Jugador.query.all()
    # form = forms.SortearForm()
    cargas = Cargas.query.all()
    return render_template('home.html', cargas=cargas)

# @app.route('/add', methods=['GET', 'POST'])
# def add():
#     form = forms.AgregarJugadorForm()
#     if form.validate_on_submit():
#         j = Jugador(nombre=form.nombre.data, numero_camiseta=form.numero.data, date=datetime.utcnow())
#         db.session.add(j)
#         db.session.commit()
#         flash('Nuevo miembro registrado exitosamente.') #esta bueno
#         return redirect(url_for('index'))
#     return render_template('add.html', form=form)

# @app.route('/edit/<int:jugador_id>', methods=['GET', 'POST'])
# def edit(jugador_id):
#     jugador = Jugador.query.get(jugador_id)
#     form = forms.AgregarJugadorForm()
#     if jugador:
#         if form.validate_on_submit():
#             jugador.nombre = form.nombre.data
#             jugador.numero_camiseta = form.numero.data
#             jugador.date = datetime.utcnow()
#             db.session.commit()
#             flash('Se modifico la informacion del jugador.')
#             return  redirect(url_for('index'))
#         form.nombre.data = jugador.nombre
#         form.numero.data = jugador.numero_camiseta
#         return render_template('edit.html', form=form, jugador_id=jugador_id)
#     else:
#         flash('No se encontro el jugador a modificar.')
#     return redirect(url_for('index'))

# @app.route('/delete/<int:jugador_id>', methods=['GET', 'POST'])
# def delete(jugador_id):
#     jugador = Jugador.query.get(jugador_id)
#     form = forms.BorrarJugadorForm()
#     if jugador:
#         if form.validate_on_submit():
#             db.session.delete(jugador)
#             db.session.commit()
#             flash('Lista de miembros actualizada.')
#             return  redirect(url_for('index'))
#         return render_template('delete.html', form=form, jugador_id=jugador_id, nombre=jugador.nombre)
#     else:
#         flash('No se encontro el jugador a eliminar.')
#     return redirect(url_for('index'))

# @app.route('/sorteo', methods=['GET', 'POST'])
# def sorteo():
#     lista = []
#     equipos = []
#     lista = request.form.getlist('lista_presentes')
#     cantidad = request.form.get('tipo_juego')
#     if len(lista) > 0 and len(cantidad) > 0:
#         cantidad = int(cantidad)
#         while len(lista)>=cantidad:
#             equipo = random.sample(lista, cantidad)
#             for i in equipo:
#                 lista.remove(i)
#             equipos.append(equipo)
#         if len(lista)>0:
#             resto_del_mundo=lista
#             equipos.append(resto_del_mundo)
#             fecha = datetime.now(pytz.timezone('America/Asuncion'))
#             p = Equipos(nombre=fecha.strftime('%Y-%b-%d-%A_%H%M'), listado=str(equipos), date=fecha)
#             db.session.add(p)
#             db.session.commit()
#         presentes = recuperar_lista(equipos)
#         return  render_template('sorteo.html', tipo=cantidad, equipos=presentes)
#     else:
#         flash('Seleccione al menos un par de jugadores.')
#     return redirect(url_for('index'))

# @app.route('/update', methods=['GET', 'POST'])
# def update():
#     jugadores = Jugador.query.all()
#     return render_template('update.html', jugadores=jugadores)

# @app.route('/historico', methods=['GET', 'POST'])
# def historico():
#     equipos = Equipos.query.all()
#     return render_template('historico.html', equipos=equipos)

# @app.route('/detalles/<int:equipos_id>', methods=['GET', 'POST'])
# def detalles(equipos_id):
#     equipos = Equipos.query.get(equipos_id)
#     lista = equipos.listado  
#     presentes = recuperar_lista(ast.literal_eval(lista))
#     return render_template('detalle.html', equipos=presentes, nombre=equipos.nombre, equipos_id=equipos_id)
