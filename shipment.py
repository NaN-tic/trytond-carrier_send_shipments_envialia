#This file is part carrier_send_shipments module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.wizard import Wizard
from trytond.pool import Pool, PoolMeta
from envialia.picking import *
from trytond.modules.carrier_send_shipments.tools import unaccent

import logging

__all__ = ['CarrierSendShipments']
__metaclass__ = PoolMeta


class CarrierSendShipments(Wizard):
    'Carrier Send Shipments'
    __name__ = "carrier.send.shipments"

    def send_envialia(self, api, shipments, service):
        '''
        Send shipments out to envialia
        :param api: obj
        :param shipments: list
        :param service: obj
        '''
        agency = api.envialia_agency
        customer = api.username
        password = api.password
        debug = api.debug

        Shipment = Pool().get('stock.shipment.out')

        with Picking(agency, customer, password, debug) as picking_api:

            for shipment in shipments:
                data = {}
                data['agency_cargo'] = agency
                data['agency_origin'] = customer
                if not api.reference:
                    data['reference'] = shipment.code
                data['service_code'] = service.code
                data['company_name'] = api.company.rec_name
                data['company_code'] = customer
                data['company_phone'] = api.phone
                data['customer_name'] = shipment.customer.name
                data['customer_contact_name'] = shipment.delivery_address.name \
                        or shipment.customer.name
                data['customer_street'] = unaccent(shipment.delivery_address.street)
                data['customer_city'] = unaccent(shipment.delivery_address.city)
                data['customer_zip'] = shipment.delivery_address.zip
                data['customer_phone'] = shipment.delivery_address.phone or ''
                data['document'] = shipment.number_packages
                if shipment.cash_ondelivery:
                    data['cash_ondelivery'] = shipment.cash_ondelivery
                data['ref'] = shipment.code
                data['notes'] = shipment.comment

                # Send shipment data to carrier
                envialia = picking_api.create(data)

                if not envialia:
                    logging.getLogger('envialia').error(
                        'Not send shipment %s.' % (shipment.code))
                if envialia and envialia.get('reference'):
                    reference = envialia.get('reference')
                    Shipment.write([shipment], {
                        'carrier_tracking_ref': reference,
                        'carrier_service': service
                        })
                    logging.getLogger('envialia').info(
                        'Send shipment %s' % (shipment.code))
                if envialia and envialia.get('error'):
                    error = envialia.get('error')
                    logging.getLogger('envialia').error(
                        'Not send shipment %s. %s' % (shipment.code, error))
