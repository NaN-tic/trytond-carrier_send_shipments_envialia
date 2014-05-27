#This file is part carrier_send_shipments_envialia module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from .api import *
from .shipment import *
from .manifest import *


def register():
    Pool.register(
        CarrierApi,
        ShipmentOut,
        module='carrier_send_shipments_envialia', type_='model')
    Pool.register(
        StockManifest,
        module='carrier_send_shipments_seurvalencia', type_='wizard')
