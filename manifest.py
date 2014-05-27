# This file is part of carrier_send_shipments_envialia module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from envialia import Picking
from trytond.pool import PoolMeta

__all__ = ['StockManifest']
__metaclass__ = PoolMeta


class StockManifest:
    __name__ = 'stock.manifest'

    def get_manifest_envialia(self, api, from_date, to_date):
        with Picking(api.envialia_agency, api.username, api.password,
                api.debug) as picking_api:
            return picking_api.list(from_date)
