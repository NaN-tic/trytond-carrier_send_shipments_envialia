#This file is part carrier_send_shipments module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

import logging

try:
    from envialia.picking import *
except ImportError:
    message = 'Unable to import Envialia: pip install envialia'
    logging.getLogger('envialia').error(message)
    raise Exception(message)

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

    def test_envialia(self, api):
        '''
        Test Envialia connection
        :param api: obj
        '''
        with API(api.envialia_agency, api.username, api.password, api.debug) \
                as envialia_api:
            test = envialia_api.test_connection()
            if test.get('error'):
                self.raise_user_error('connection_error')
            elif test.get('session'):
                self.raise_user_error('connection_successfully')
            else:
                self.raise_user_error('connection_error')
