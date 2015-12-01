# This file is part of the carrier_send_shipments_envialia module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class CarrierSendShipmentsEnvialiaTestCase(ModuleTestCase):
    'Test Carrier Send Shipments Envialia module'
    module = 'carrier_send_shipments_envialia'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        CarrierSendShipmentsEnvialiaTestCase))
    return suite