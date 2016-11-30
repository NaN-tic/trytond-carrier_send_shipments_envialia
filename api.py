#This file is part carrier_send_shipments_envialia module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Not, Equal
import logging

try:
    from envialia.picking import *
except ImportError:
    logger = logging.getLogger(__name__)
    message = 'Install Envialia: pip install envialia'
    logger.error(message)
    raise Exception(message)

__all__ = ['CarrierApi']


class CarrierApi:
    __metaclass__ = PoolMeta
    __name__ = 'carrier.api'
    envialia_agency = fields.Char('Agency', states={
            'required': Eval('method') == 'envialia',
        }, help='Envialia Agency')

    @classmethod
    def get_carrier_app(cls):
        'Add Carrier Envialia APP'
        res = super(CarrierApi, cls).get_carrier_app()
        res.append(('envialia','Envialia'))
        return res

    @classmethod
    def view_attributes(cls):
        return super(CarrierApi, cls).view_attributes() + [
            ('//page[@id="envialia"]', 'states', {
                    'invisible': Not(Equal(Eval('method'), 'envialia')),
                    })]

    @classmethod
    def test_envialia(cls, api):
        'Test Envialia connection'
        with API(api.envialia_agency, api.username, api.password, api.debug) \
                as envialia_api:
            test = envialia_api.test_connection()
            if test.get('error'):
                cls.raise_user_error('connection_error')
            elif test.get('session'):
                cls.raise_user_error('connection_successfully')
            else:
                cls.raise_user_error('connection_error')
