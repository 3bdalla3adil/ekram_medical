/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class ReceptionDashboard extends Component {
    static template = "ekram_medical.ReceptionDashboard";

    setup() {
        this.rpc    = useService("rpc");
        this.action = useService("action");
        this.state  = useState({ loading: true, kpis: {}, appointments: [] });
        onWillStart(async () => { await this.loadData(); });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.rpc("/ekram_medical/reception_data", {});
            this.state.kpis         = data.kpis        || {};
            this.state.appointments = data.appointments || [];
        } catch (e) {
            console.error("Reception dashboard error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    openNewPatient() {
        this.action.doAction({
            type: "ir.actions.act_window", name: _t("New Patient"),
            res_model: "res.partner", view_mode: "form",
            views: [[false, "form"]], target: "new",
            context: { default_is_patient: true },
        });
    }
    openNewAppointment() {
        this.action.doAction({
            type: "ir.actions.act_window", name: _t("New Appointment"),
            res_model: "medical.appointment", view_mode: "form",
            views: [[false, "form"]], target: "new",
        });
    }
    openNewInvoice() {
        this.action.doAction({
            type: "ir.actions.act_window", name: _t("New Invoice"),
            res_model: "account.move", view_mode: "form",
            views: [[false, "form"]], target: "new",
            context: { default_move_type: "out_invoice" },
        });
    }
    openPatientList()      { this.action.doAction("ekram_medical.action_medical_patients"); }
    openAppointmentList()  { this.action.doAction("ekram_medical.action_medical_appointments"); }
    openOutstanding() {
        this.action.doAction({
            type: "ir.actions.act_window", name: _t("Outstanding Invoices"),
            res_model: "account.move", view_mode: "list,form",
            domain: [["move_type","=","out_invoice"],["payment_state","in",["not_paid","partial"]],["state","=","posted"]],
        });
    }
    openAppointment(id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "medical.appointment",
            res_id: id, view_mode: "form", views: [[false, "form"]],
        });
    }
    getStateBadgeClass(state) {
        return "badge " + ({ draft:"badge-secondary", confirmed:"badge-info", in_progress:"badge-warning", done:"badge-success", cancelled:"badge-danger" }[state] || "badge-secondary");
    }
}

registry.category("actions").add("ekram_medical.reception_dashboard", ReceptionDashboard);