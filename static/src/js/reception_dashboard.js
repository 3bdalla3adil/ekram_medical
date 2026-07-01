/** @odoo-module **/
// import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Component, onMounted, useState, useRef, onWillStart  } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class ReceptionDashboard extends Component {
    static template = "ekram_medical.ReceptionDashboard";

    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");
        this.state  = useState({ loading: true, kpis: {}, appointments: [] });
        onWillStart(async () => { await this.loadData(); });
        }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await rpc("/ekram_medical/reception_data", {});
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

    async savePatient(){
        var data = await this.fetch_patient_data()
        if( data['name']=="" || data['phone']==""){
            alert("Please fill the name and phone")
            return;
        }
        await this.orm.call('res.partner','create',[[data]]).then(function (){
           alert("the patient record has been created")
           window.location.reload()
        })
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
    openAppointmentList()  { this.action.doAction("ekram_medical.action_medical_appointments"); }
    openOutstanding() {
        this.action.doAction({
            type: "ir.actions.act_window", name: _t("Outstanding Invoices"),
            res_model: "account.move", view_mode: "list,form",
            domain: [["move_type","=","out_invoice"],["payment_state","in",["not_paid","partial"]],["state","=","posted"]],
        });
    }
    openAppointment(id) {
        const recordId = id;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name ? `${name.toUpperCase()} Appointments` : "All Appointments",
            res_model: "medical.appointment",
            domain: [["id","=",recordId],],
            // res_id: recordId,
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
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
    getStateBadgeClass(state) {
        return "badge " + ({ draft:"badge-secondary", confirmed:"badge-info", in_progress:"badge-warning", done:"badge-success", cancelled:"badge-danger" }[state] || "badge-secondary");
    }
}

registry.category("actions").add("ekram_medical_reception_dashboard", ReceptionDashboard);