import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class MedicalDashboard extends Component {
    static template = "ekram_medical.MedicalDashboardTemplate";

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        
        // Dynamic dashboard metrics state
        this.state = useState({
            total: 0,
            confirmed: 0,
            inProgress: 0,
            done: 0,
            cancelled: 0
        });

        onWillStart(async () => {
            await this.loadDashboardStatistics();
        });
    }

    // Dynamic counts straight from your medical.appointment schema
    async loadDashboardStatistics() {
        const counts = await this.orm.readGroup(
            "medical.appointment",
            [],
            ["state"],
            ["state"]
        );
        
        let totalCount = 0;
        counts.forEach(c => {
            totalCount += c.state_count;
            if (c.state === 'confirmed') this.state.confirmed = c.state_count;
            if (c.state === 'in_progress') this.state.inProgress = c.state_count;
            if (c.state === 'done') this.state.done = c.state_count;
            if (c.state === 'cancelled') this.state.cancelled = c.state_count;
        });
        this.state.total = totalCount;
    }

    // Quick Action 1: Book New Appointment Form Popup
    openNewAppointmentWizard() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Book Appointment",
            res_model: "medical.appointment",
            views: [[false, "form"]],
            target: "new", // "new" opens it inside an overlay modal
        });
    }

    // Quick Action 2: Register New Patient Form Popup
    openNewPatientWizard() {
        // Replace 'res.partner' with your specific patient model name if you have a custom one
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Register New Patient",
            res_model: "res.partner", 
            views: [[false, "form"]],
            target: "new",
        });
    }

    // Metrics Navigation Filters
    viewAppointmentsByState(stateValue = null) {
        const domain = stateValue ? [["state", "=", stateValue]] : [];
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: stateValue ? `${stateValue.toUpperCase()} Appointments` : "All Appointments",
            res_model: "medical.appointment",
            domain: domain,
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
    }
}

// Map JavaScript client class to backend tag name
registry.category("actions").add("ekram_medical.medical_dashboard", MedicalDashboard);
