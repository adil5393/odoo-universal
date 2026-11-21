import hmac
import json
import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError

from ..signature import valid_signature

_logger = logging.getLogger(__name__)


class PosCallback(http.Controller):
    @http.route('/universal_pos_qr/callback', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def callback(self, **kwargs):
        raw = request.httprequest.get_data(cache=True)
        if len(raw) > 16384:
            return request.make_response('Invalid callback', status=400)
        try:
            data = json.loads(raw.decode('utf-8'))
            if not isinstance(data, dict) or not isinstance(data.get('request_reference'), str):
                raise ValueError('Invalid callback')
            record = request.env['universal.pos.request'].sudo().search([('reference', '=', data['request_reference'])], limit=1)
            signature = request.httprequest.headers.get('X-Terminal-Signature', '')
            event_header = request.httprequest.headers.get('X-Terminal-Event-Id', '')
            if not record or not record.api_key or not isinstance(data.get('event_id'), str):
                raise ValueError('Invalid callback')
            if not valid_signature(record.api_key, raw, signature) or not hmac.compare_digest(event_header, data['event_id']):
                raise ValueError('Invalid signature')
            with request.env.cr.savepoint():
                record._apply_capture(data)
        except (ValueError, UnicodeError, TypeError, UserError, ValidationError, AccessError):
            _logger.warning('Rejected POS callback')
            return request.make_response('Invalid callback', status=400)
        # Odoo commits the request transaction before returning the HTTP response.
        return request.make_response('OK', status=200)
