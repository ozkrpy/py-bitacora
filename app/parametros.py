# DISPONIBILIDAD
LIMITE_CREDITO_TJ = 8000000
SALARIO_BRUTO = 6825000

# SALIDAS
DESCUENTO_IPS = 614250
DESCUENTO_POR_SERVICIOS = 179500 
DESCUENTOS_VARIOS = 0
AHORRO_PROGRAMADO = 500000
CASA = 700000
CHECHY = 500000
SEGURO_AUTO = 385000
CONTADORA = 110000
PAGO_TARJETA = 500000
COMBUSTIBLE = 300000
SUPERMERCADO = 600000
CABLETV = 100500

# CALCULOS
SALARIO_NETO = SALARIO_BRUTO - DESCUENTO_IPS - DESCUENTO_POR_SERVICIOS

DEUDA_BASICA = {
    'CASA':CASA, 'CHECHY':CHECHY, 'PAGO_TARJETA': PAGO_TARJETA, 'COMBUSTIBLE': COMBUSTIBLE,
    'SEGURO_AUTO': SEGURO_AUTO, 'SUPERMERCADO': SUPERMERCADO, 'CONTADORA': CONTADORA,
    'BRUTO': SALARIO_BRUTO, 'CABLETV': CABLETV
}

