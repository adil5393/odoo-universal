from odoo import models
from collections import defaultdict
from odoo.tools import frozendict

class AccountMove(models.Model):
    _inherit = 'account.move'  # Inheriting account.move

    def _l10n_in_get_hsn_summary_table(self):
        self.ensure_one()
        display_uom = self.env.user.user_has_groups('uom.group_uom')
        tag_igst = self.env.ref('l10n_in.tax_tag_igst')
        tag_cgst = self.env.ref('l10n_in.tax_tag_cgst')
        tag_sgst = self.env.ref('l10n_in.tax_tag_sgst')
        tag_cess = self.env.ref('l10n_in.tax_tag_cess')

        def filter_invl_to_apply(invoice_line):
            return bool(invoice_line.product_id.l10n_in_hsn_code)

        def grouping_key_generator(base_line, _tax_values):
            if base_line['is_refund']:
                tax_rep_field = 'refund_repartition_line_ids'
            else:
                tax_rep_field = 'invoice_repartition_line_ids'

            gst_taxes = base_line['taxes'].flatten_taxes_hierarchy()[tax_rep_field]\
                .filtered(lambda tax_rep: (
                    tax_rep.repartition_type == 'tax'
                    and any(tag in tax_rep.tag_ids for tag in tag_sgst + tag_cgst + tag_igst)
                ))\
                .tax_id

            return {
                'l10n_in_hsn_code': base_line['record'].product_id.l10n_in_hsn_code,
                'rate': sum(gst_taxes.mapped('amount')),
                'uom': base_line['record'].product_uom_id,
            }

        aggregated_values = self._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=filter_invl_to_apply,
            grouping_key_generator=grouping_key_generator,
        )

        results_map = {}
        has_igst = False
        has_gst = False
        has_cess = False

        # Custom logic to get discount from sale order
        order = self.invoice_origin and self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
        total_discount = 0.0
        total_before_discount = 0.0
        if order:
            order_lines = self.env['sale.order.line'].search([('order_id', '=', order.id)])
            total_discount = sum(line.price_subtotal for line in order_lines if "discount" in line.name.lower())

        total_before_discount = sum(
            sum(line.price_subtotal for line in tax_details['records'])
            for tax_details in aggregated_values['tax_details'].values()
        )

        for grouping_key, tax_details in aggregated_values['tax_details'].items():
            group_taxable_amount = sum(line.price_subtotal for line in tax_details['records'])
            discount_for_group = (group_taxable_amount / total_before_discount) * total_discount if total_before_discount else 0

            values = results_map.setdefault(grouping_key, {
                'quantity': 0.0,
                'amount_untaxed': tax_details['base_amount_currency'] + discount_for_group,  # Custom discount logic
                'tax_amounts': defaultdict(lambda: 0.0),
            })

            # Quantity.
            invoice_line_ids = set()
            for invoice_line in tax_details['records']:
                if invoice_line.id not in invoice_line_ids:
                    values['quantity'] += invoice_line.quantity
                    invoice_line_ids.add(invoice_line.id)

            # Tax amounts.
            # for tax_details in tax_details['group_tax_details']:
            #     tax_rep = tax_details['tax_repartition_line']
            #     if tag_igst in tax_rep.tag_ids:
            #         has_igst = True
            #         values['tax_amounts'][tag_igst] += tax_details['tax_amount_currency']
            #     if tag_cgst in tax_rep.tag_ids:
            #         has_gst = True
            #         values['tax_amounts'][tag_cgst] += tax_details['tax_amount_currency']
            #     if tag_sgst in tax_rep.tag_ids:
            #         has_gst = True
            #         values['tax_amounts'][tag_sgst] += tax_details['tax_amount_currency']
            #     if tag_cess in tax_rep.tag_ids:
            #         has_cess = True
            #         values['tax_amounts'][tag_cess] += tax_details['tax_amount_currency']
            discounted_base = group_taxable_amount + discount_for_group
            rate = grouping_key['rate']

            # We'll assume equal CGST and SGST split if GST applies (not IGST)
            if rate and not has_igst:
                half_rate = rate / 2
                values['tax_amounts'][tag_cgst] += discounted_base * half_rate / 100
                values['tax_amounts'][tag_sgst] += discounted_base * half_rate / 100
                has_gst = True
            elif rate and not has_gst:
                values['tax_amounts'][tag_igst] += discounted_base * rate / 100
                has_igst = True
            

        for base_line, _to_update_vals, _tax_values_list in aggregated_values['to_process']:
            if base_line['taxes']:
                continue

            grouping_key = frozendict(grouping_key_generator(base_line, None))
            results = results_map.setdefault(grouping_key, {
                'quantity': 0.0,
                'amount_untaxed': 0.0,
                'tax_amounts': defaultdict(lambda: 0.0),
            })
            results['quantity'] += base_line['quantity']
            results['amount_untaxed'] += base_line['price_subtotal']

        nb_columns = 5
        if has_igst:
            nb_columns += 1
        if has_gst:
            nb_columns += 2
        if has_cess:
            nb_columns += 1

        items = []
        for grouping_key, values in results_map.items():
            items.append({
                'l10n_in_hsn_code': grouping_key['l10n_in_hsn_code'],
                'quantity': values['quantity'],
                'uom': grouping_key['uom'],
                'rate': grouping_key['rate'],
                'amount_untaxed': values['amount_untaxed'],
                'tax_amount_igst': values['tax_amounts'].get(tag_igst, 0.0),
                'tax_amount_cgst': values['tax_amounts'].get(tag_cgst, 0.0),
                'tax_amount_sgst': values['tax_amounts'].get(tag_sgst, 0.0),
                'tax_amount_cess': values['tax_amounts'].get(tag_cess, 0.0),
            })

        return {
            'has_igst': has_igst,
            'has_gst': has_gst,
            'has_cess': has_cess,
            'nb_columns': nb_columns,
            'display_uom': display_uom,
            'items': items,
        }
