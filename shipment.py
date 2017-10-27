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

logger = logging.getLogger(__name__)


class ShipmentOut:
    __name__ = 'stock.shipment.out'

    @classmethod
    def __setup__(cls):
        super(ShipmentOut, cls).__setup__()
        cls._error_messages.update({
            'envialia_add_services': 'Select a service or default service in Envialia API',
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
        Uom = pool.get('product.uom')
        Date = pool.get('ir.date')

        references = []
        labels = []
        errors = []

        agency = api.envialia_agency
        customer = api.username
        password = api.password
        timeout = api.timeout
        debug = api.debug

        default_service = CarrierApi.get_default_carrier_service(api)

        with Picking(agency, customer, password, timeout=timeout, debug=debug) as picking_api:
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

                notes = ''
                if shipment.carrier_notes:
                    notes = '%s\n' % shipment.carrier_notes

                packages = shipment.number_packages
                if not packages or packages == 0:
                    packages = 1

                data = {}
                data['agency_cargo'] = agency
                data['agency_origin'] = customer
                if not api.reference:
                    data['reference'] = code
                data['picking_date'] = Date.today().strftime("%Y-%m-%d")
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
                    price_ondelivery = shipment.carrier_cashondelivery_price
                    data['cash_ondelivery'] = str(price_ondelivery)
                data['ref'] = code
                data['notes'] = unaccent(notes)

                if api.weight and hasattr(shipment, 'weight_func'):
                    weight = shipment.weight_func
                    if weight == 0:
                        weight = 1
                    if api.weight_api_unit:
                        if shipment.weight_uom:
                            weight = Uom.compute_qty(
                                shipment.weight_uom, weight, api.weight_api_unit)
                        elif api.weight_unit:
                            weight = Uom.compute_qty(
                                api.weight_unit, weight, api.weight_api_unit)
                    data['weight'] = str(weight)

                # Send shipment data to carrier
                envialia = picking_api.create(data)

                vals2write = {}
                if not envialia:
                    logger.error('Not send shipment %s.' % (shipment.code))
                reference = envialia.get('reference')
                if envialia and reference:
                    vals2write['carrier_tracking_ref'] = reference
                    vals2write['carrier_service'] = service
                    vals2write['carrier_delivery'] = True
                    vals2write['carrier_send_date'] = ShipmentOut.get_carrier_date()
                    vals2write['carrier_send_employee'] = ShipmentOut.get_carrier_employee() or None
                    logger.info('Send shipment %s' % (shipment.code))
                    references.append(shipment.code)
                if envialia and envialia.get('error'):
                    error = envialia.get('error')
                    message = self.raise_user_error('envialia_not_send_error', {
                            'name': shipment.rec_name,
                            'error': error,
                            }, raise_exception=False)
                    logger.error(message)
                    errors.append(message)

                if reference:
                    labels += self.print_labels_envialia(api, [shipment], reference=reference)
                if labels:
                    vals2write['carrier_printed'] = True

                if vals2write:
                    self.write([shipment], vals2write)

        return references, labels, errors

    @classmethod
    def print_labels_envialia(self, api, shipments, reference=None):
        agency = api.envialia_agency
        username = api.username
        password = api.password
        timeout = api.timeout
        debug = api.debug

        labels = []
        dbname = Transaction().cursor.dbname

        with Picking(agency, username, password, timeout=timeout, debug=debug) as shipment_api:
            for shipment in shipments:
                if not reference:
                    if not shipment.carrier_tracking_ref:
                        logger.error(
                            'Shipment %s has not been sent by Envialia.'
                            % (shipment.code))
                        continue
                    reference = shipment.carrier_tracking_ref

                data = {}
                data['agency_origin'] = data['agency_cargo'] = agency

                label = shipment_api.label(reference, data)
                if not label:
                    logger.error(
                        'Label for shipment %s is not available from Envialia.'
                        % shipment.code)
                    continue
                with tempfile.NamedTemporaryFile(
                        prefix='%s-envialia-%s-' % (dbname, reference),
                        suffix='.pdf', delete=False) as temp:
                    temp.write(decodestring(label)) # Envialia PDF file
                logger.info(
                    'Generated tmp label %s' % (temp.name))
                temp.close()
                labels.append(temp.name)
            self.write(shipments, {'carrier_printed': True})

        return labels
