/** @odoo-module **/
// import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Component, onMounted, useState, useRef, onWillStart  } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class LabDashboard extends Component {
    static template = "ekram_medical.LabDashboard";

    setup() {
        this.rpc    = useService("rpc");
        this.action = useService("action");
        this.state  = useState({ loading: true, kpis: {}, pending_requests: [], pending_results: [] });
        onWillStart(async () => { await this.loadData(); });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.rpc("/ekram_medical/lab_data", {});
            this.state.kpis             = data.kpis || {};
            this.state.pending_requests = data.pending_requests_list || [];
            this.state.pending_results  = data.pending_results_list  || [];
        } catch (e) {
            console.error("Lab dashboard error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    openLabRequest(id) {
        this.action.doAction({ type:"ir.actions.act_window", res_model:"medical.lab.request", res_id:id, view_mode:"form", views:[[false,"form"]] });
    }
    openLabResult(id) {
        this.action.doAction({ type:"ir.actions.act_window", res_model:"medical.lab.result", res_id:id, view_mode:"form", views:[[false,"form"]] });
    }
    openAllRequests() { this.action.doAction("ekram_medical.action_medical_lab_requests"); }
    openAllResults()  { this.action.doAction("ekram_medical.action_medical_lab_results"); }
    openNewRequest() {
        this.action.doAction({ type:"ir.actions.act_window", name:_t("New Lab Request"), res_model:"medical.lab.request", view_mode:"form", views:[[false,"form"]], target:"new" });
    }
    getStateBadgeClass(state) {
        return "badge " + ({ draft:"badge-info", processing:"badge-warning", completed:"badge-success", cancelled:"badge-danger" }[state] || "badge-secondary");
    }
}

registry.category("actions").add("ekram_medical.lab_dashboard", LabDashboard);