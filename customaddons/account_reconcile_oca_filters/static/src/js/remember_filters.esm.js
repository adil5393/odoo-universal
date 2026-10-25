/** @odoo-module **/
// Keeps the filters picked in the "Reconcile" list when moving to the next bank
// line. The list is rebuilt for every bank line, which used to reset them.
// Only menu filters and group-bys are kept; typed searches (names, amounts) are
// specific to one line and still reset.

import {AccountReconcileMatchWidget} from "@account_reconcile_oca/js/widgets/reconcile_move_line_widget.esm";
import {ReconcileMoveLineController} from "@account_reconcile_oca/js/reconcile_move_line/reconcile_move_line_controller.esm";
import {patch} from "@web/core/utils/patch";
import {useBus} from "@web/core/utils/hooks";

// Filters active until the user changes them (reset on page reload)
const DEFAULT_FILTERS = ["not_cash"];
let rememberedFilters = null;

patch(ReconcileMoveLineController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.props.parentRecord) {
            return;
        }
        const searchModel = this.env.searchModel;
        useBus(searchModel, "update", () => {
            const names = searchModel.query
                .map((queryElem) => searchModel.searchItems[queryElem.searchItemId])
                .filter((item) => item && ["filter", "groupBy"].includes(item.type) && item.name)
                .map((item) => item.name);
            rememberedFilters = [...new Set(names)];
        });
    },
});

patch(AccountReconcileMatchWidget.prototype, {
    get listViewProperties() {
        const props = super.listViewProperties;
        const context = {...props.context};
        for (const name of rememberedFilters || DEFAULT_FILTERS) {
            context[`search_default_${name}`] = 1;
        }
        return {...props, context};
    },
});
