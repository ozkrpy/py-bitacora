import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'textoDeSeguridad'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.db')+'?check_same_thread=False'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # app.config['SECRET_KEY'] = 'textoDeSeguridad'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db' 
    # app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False