# This file is part of the carrier_send_shipments module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from envialia.picking import Picking
from trytond.modules.carrier_send_shipments.tools import unaccent
from base64 import decodestring
import logging
import tempfile

__all__ = ['ShipmentOut']
__metaclass__ = PoolMeta


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    @classmethod
    def send_envialia(self, api, shipments):
        '''
        Send shipments out to envialia
        :param api: obj
        :param shipments: list
        Return references, labels, errors
        '''
        pool = Pool()
        CarrierApi = pool.get('carrier.api')

        references = []
        labels = []
        errors = []

        agency = api.envialia_agency
        customer = api.username
        password = api.password
        debug = api.debug

        default_service = CarrierApi.get_default_carrier_service(api)

        with Picking(agency, customer, password, debug) as picking_api:
            for shipment in shipments:
                service = shipment.carrier_service or default_service

                notes = ''
                if shipment.carrier_notes:
                    notes = CarrierApi.carrier_unaccent(shipment.carrier_notes)

                packages = shipment.number_packages
                if packages == 0:
                    packages = 1

                data = {}
                data['agency_cargo'] = agency
                data['agency_origin'] = customer
                if not api.reference:
                    data['reference'] = shipment.code
                data['service_code'] = str(service.code)
                data['company_name'] = api.company.rec_name
                data['company_code'] = customer
                data['company_phone'] = api.phone
                data['customer_name'] = unaccent(shipment.customer.name)
                data['customer_contact_name'] = unaccent((shipment.delivery_address.name
                    or shipment.customer.name))
                data['customer_street'] = unaccent(shipment.delivery_address.street)
                data['customer_city'] = unaccent(shipment.delivery_address.city)
                data['customer_zip'] = shipment.delivery_address.zip
                data['customer_phone'] = shipment.delivery_address.phone or ''
                data['document'] = packages
                if shipment.carrier_cashondelivery:
                    data['cash_ondelivery'] = shipment.carrier_cashondelivery
                    data['total'] = str(self.get_carrier_price_total(shipment))
                data['ref'] = shipment.code
                data['notes'] = notes

                # Send shipment data to carrier
                envialia = picking_api.create(data)

                if not envialia:
                    logging.getLogger('envialia').error(
                        'Not send shipment %s.' % (shipment.code))
                if envialia and envialia.get('reference'):
                    reference = envialia.get('reference')
                    self.write([shipment], {
                        'carrier_tracking_ref': reference,
                        'carrier_service': service,
                        'carrier_delivery': True,
                        })
                    logging.getLogger('envialia').info(
                        'Send shipment %s' % (shipment.code))
                    references.append(shipment.code)
                if envialia and envialia.get('error'):
                    error = envialia.get('error')
                    logging.getLogger('envialia').error(
                        'Not send shipment %s. %s' % (shipment.code, error))
                    errors.append(shipment.code)

                labels += self.print_labels_envialia(api, shipments)

        return references, labels, errors

    @classmethod
    def print_labels_envialia(cls, api, shipments):
        agency = api.envialia_agency
        username = api.username
        password = api.password
        debug = api.debug

        labels = []
        dbname = Transaction().cursor.dbname

        with Picking(agency, username, password, debug) as shipment_api:
            for shipment in shipments:
                if not shipment.carrier_tracking_ref:
                    logging.getLogger('carrier_send_shipment_envialia').error(
                        'Shipment %s has not been sent by Envialia.'
                        % (shipment.code))
                    continue

                data = {}
                data['agency_origin'] = data['agency_cargo'] = agency
                reference = shipment.carrier_tracking_ref

                label = shipment_api.label(reference, data)
                if not label:
                    logging.getLogger('carrier_send_shipment_envialia').error(
                        'Label for shipment %s is not available from Envialia.'
                        % shipment.code)
                    continue
                with tempfile.NamedTemporaryFile(
                        prefix='%s-envialia-%s-' % (dbname, reference),
                        suffix='.pdf', delete=False) as temp:
                    temp.write(decodestring(label)) # Envialia PDF file
                logging.getLogger('envialia').info(
                    'Generated tmp label %s' % (temp.name))
                temp.close()
                labels.append(temp.name)
            cls.write(shipments, {'carrier_printed': True})

        return labels
