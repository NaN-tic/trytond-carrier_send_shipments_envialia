#This file is part carrier_send_shipments module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['CarrierApi']
__metaclass__ = PoolMeta


class CarrierApi:
    'Carrier API'
    __name__ = 'carrier.api'
    envialia_agency = fields.Char('Agency', states={
            'required': Eval('method') == 'envialia',
            }, help='Envialia Agency')

    @classmethod
    def get_carrier_app(cls):
        '''
        Add Carrier Envialia APP
        '''
        res = super(CarrierApi, cls).get_carrier_app()
        res.append(('envialia','Envialia'))
        return res
