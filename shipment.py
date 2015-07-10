# This file is part of the carrier_send_shipments module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from envialia.picking import Picking
from trytond.modules.carrier_send_shipments.tools import unaccent, unspaces
from base64 import decodestring
import logging
import tempfile

__all__ = ['ShipmentOut']
__metaclass__ = PoolMeta


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        cls._error_messages.update({
            'envialia_add_services': 'Select a service or default service in Envialia API',
            'envialia_not_price': 'Shipment "%(name)s" not have price and send '
                'cashondelivery',
            'envialia_not_send': 'Not send shipment %(name)s',
            'envialia_not_send_error': 'Not send shipment %(name)s. %(error)s',
            })

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
        ShipmentOut = pool.get('stock.shipment.out')

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
                service = shipment.carrier_service or shipment.carrier.service or default_service
                if not service:
                    message = self.raise_user_error('envialia_add_services', {},
                        raise_exception=False)
                    errors.append(message)
                    continue

                if api.reference_origin and hasattr(shipment, 'origin'):
                    code = shipment.origin and shipment.origin.rec_name or shipment.code
                else:
                    code = shipment.code

                if code != shipment.code:
                    notes = '%s - %s\n' % (code, shipment.code)
                else:
                    notes = '%s\n' % (shipment.code)
                if shipment.carrier_notes:
                    notes += '%s\n' % shipment.carrier_notes

                packages = shipment.number_packages
                if not packages or packages == 0:
                    packages = 1

                data = {}
                data['agency_cargo'] = agency
                data['agency_origin'] = customer
                if not api.reference:
                    data['reference'] = code
                data['service_code'] = str(service.code)
                data['company_name'] = unaccent(api.company.rec_name)
                data['company_code'] = customer
                data['company_phone'] = api.phone
                data['customer_name'] = unaccent(shipment.customer.name)
                data['customer_contact_name'] = unaccent((shipment.delivery_address.name
                    or shipment.customer.name))
                data['customer_street'] = unaccent(shipment.delivery_address.street)
                data['customer_city'] = unaccent(shipment.delivery_address.city)
                data['customer_zip'] = shipment.delivery_address.zip
                data['customer_phone'] = unspaces(ShipmentOut.get_phone_shipment_out(shipment))
                data['document'] = packages
                if shipment.carrier_cashondelivery:
                    price_ondelivery = ShipmentOut.get_price_ondelivery_shipment_out(shipment)
                    if not price_ondelivery:
                        message = self.raise_user_error('envialia_not_price', {
                                'name': shipment.rec_name,
                                }, raise_exception=False)
                        errors.append(message)
                        continue
                    data['cash_ondelivery'] = str(price_ondelivery)
                data['ref'] = code
                data['notes'] = unaccent(notes)
                if api.weight and hasattr(shipment, 'weight_func'):
                    weight = str(shipment.weight_func)
                    if weight == '0.0':
                        weight = '1'
                    data['weight'] = str(weight)

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
                        'carrier_send_date': ShipmentOut.get_carrier_date(),
                        'carrier_send_employee': ShipmentOut.get_carrier_employee() or None,
                        })
                    logging.getLogger('envialia').info(
                        'Send shipment %s' % (shipment.code))
                    references.append(shipment.code)
                if envialia and envialia.get('error'):
                    error = envialia.get('error')
                    message = self.raise_user_error('envialia_not_send_error', {
                            'name': shipment.rec_name,
                            'error': error,
                            }, raise_exception=False)
                    logging.getLogger('envialia').error(message)
                    errors.append(message)

                labels += self.print_labels_envialia(api, shipments)

        return references, labels, errors

    @classmethod
    def print_labels_envialia(self, api, shipments):
        agency = api.envialia_agency
        username = api.username
        password = api.password
        debug = api.debug

        labels = []
        dbname = Transaction().cursor.dbname

        with Picking(agency, username, password, debug) as shipment_api:
            for shipment in shipments:
                if not shipment.carrier_tracking_ref:
                    logging.getLogger('envialia').error(
                        'Shipment %s has not been sent by Envialia.'
                        % (shipment.code))
                    continue

                data = {}
                data['agency_origin'] = data['agency_cargo'] = agency
                reference = shipment.carrier_tracking_ref

                label = shipment_api.label(reference, data)
                if not label:
                    logging.getLogger('envialia').error(
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
            self.write(shipments, {'carrier_printed': True})

        return labels
