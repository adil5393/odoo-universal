/** @odoo-module **/
// Keeps the page and scroll position of the "Reconcile" list when an item is
// picked. Picking an item updates the bank line, which reloads the list; Odoo
// then jumps back to page 1 while the panel keeps its scroll, so the user lands
// somewhere else. Position is only kept while the bank line and the search stay
// the same; a new search or another bank line still starts at the top.

import {onPatched, toRaw} from "@odoo/owl";
import {ReconcileMoveLineController} from "@account_reconcile_oca/js/reconcile_move_line/reconcile_move_line_controller.esm";
import {patch} from "@web/core/utils/patch";

function scrolledAncestors(el) {
    const result = [];
    for (let node = el && el.parentElement; node; node = node.parentElement) {
        if (node.scrollTop > 0) {
            result.push([node, node.scrollTop]);
        }
    }
    return result;
}

patch(ReconcileMoveLineController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.props.parentRecord) {
            return;
        }
        const model = toRaw(this.model);
        const searchModel = this.env.searchModel;
        const positionKey = () =>
            JSON.stringify([this.props.parentRecord.resId, searchModel.query]);
        let lastKey = null;
        let keepPosition = false;
        let pendingScroll = null;

        const getNextConfig = model._getNextConfig.bind(model);
        model._getNextConfig = (currentConfig, params) => {
            const config = getNextConfig(currentConfig, params);
            if (keepPosition && currentConfig.offset) {
                config.offset = currentConfig.offset;
            }
            return config;
        };

        const load = model.load.bind(model);
        model.load = async (...args) => {
            const key = positionKey();
            keepPosition = lastKey !== null && key === lastKey;
            lastKey = key;
            pendingScroll = keepPosition ? scrolledAncestors(this.rootRef.el) : null;
            try {
                await load(...args);
            } finally {
                keepPosition = false;
            }
            // Picked items can leave the kept page empty: go to the last page
            const root = model.root;
            if (root && !root.isGrouped && root.offset > 0 && root.count && !root.records.length) {
                const lastPage = Math.floor((root.count - 1) / root.limit) * root.limit;
                await root.load({offset: lastPage});
            }
        };

        onPatched(() => {
            if (!pendingScroll) {
                return;
            }
            const scroll = pendingScroll;
            pendingScroll = null;
            requestAnimationFrame(() => {
                for (const [node, top] of scroll) {
                    node.scrollTop = top;
                }
            });
        });
    },
});
