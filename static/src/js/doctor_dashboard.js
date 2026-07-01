/** @odoo-module **/
// import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Component, onMounted, useState, useRef, onWillStart  } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class DoctorDashboard extends Component {
    static template = "ekram_medical.DoctorDashboard";

    setup() {
        // this.rpc    = useService("rpc");
        this.action = useService("action");
        this.state  = useState({ loading: true, doctor_name: "", kpis: {}, today_patients: [], pending_consultations: [] });
        onWillStart(async () => { await this.loadData(); });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.rpc("/ekram_medical/doctor_data", {});
            this.state.doctor_name           = data.doctor_name || "";
            this.state.kpis                  = data.kpis || {};
            this.state.today_patients        = data.today_patients || [];
            this.state.pending_consultations = data.pending_consultations_list || [];
        } catch (e) {
            console.error("Doctor dashboard error:", e);
        } finally {
            this.state.loading = false;
        }
    }

    openConsultation(id) {
        this.action.doAction({ type:"ir.actions.act_window", res_model:"medical.consultation", res_id:id, view_mode:"form", views:[[false,"form"]] });
    }
    openAppointment(id) {
        this.action.doAction({ type:"ir.actions.act_window", res_model:"medical.appointment", res_id:id, view_mode:"form", views:[[false,"form"]] });
    }
    openAllConsultations() { this.action.doAction("ekram_medical.action_medical_consultations"); }
    openAllLabRequests()   { this.action.doAction("ekram_medical.action_medical_lab_requests"); }
    getStateBadgeClass(state) {
        return "badge " + ({ draft:"badge-secondary", in_progress:"badge-warning", done:"badge-success", confirmed:"badge-info", cancelled:"badge-danger" }[state] || "badge-secondary");
    }
}

registry.category("actions").add("ekram_medical.doctor_dashboard", DoctorDashboard);