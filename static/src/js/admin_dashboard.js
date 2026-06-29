/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class AdminDashboard extends Component {
    static template = "ekram_medical.AdminDashboard";

    setup() {
        // this.rpc          = useService("rpc");
        this.action       = useService("action");
        this.chartRef     = useRef("revenueChart");
        this.deptChartRef = useRef("deptChart");

        this.state = useState({
            loading: true,
            kpis: {},
            revenue_chart: [],
            dept_chart: [],
            cash_data: [],
            bank_data: [],
            invoice_summary: [],
            outstanding_list: [],
            active_tab: "invoices",
        });

        onWillStart(async () => { await this.loadData(); });
        onMounted(() => { if (!this.state.loading) this._drawCharts(); });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.rpc("/ekram_medical/admin_data", {});
            this.state.kpis             = data.kpis             || {};
            this.state.revenue_chart    = data.revenue_chart    || [];
            this.state.dept_chart       = data.dept_chart       || [];
            this.state.cash_data        = data.cash_data        || [];
            this.state.bank_data        = data.bank_data        || [];
            this.state.invoice_summary  = data.invoice_summary  || [];
            this.state.outstanding_list = data.outstanding_list || [];
        } catch (e) {
            console.error("Admin dashboard error:", e);
        } finally {
            this.state.loading = false;
            setTimeout(() => this._drawCharts(), 120);
        }
    }

    // ── Canvas Charts ─────────────────────────────────────────────────────

    _drawCharts() {
        this._drawRevenueChart();
        this._drawDeptChart();
    }

    _drawRevenueChart() {
        const canvas = this.chartRef.el;
        if (!canvas || !this.state.revenue_chart.length) return;
        const ctx  = canvas.getContext("2d");
        const data = this.state.revenue_chart;
        const W    = canvas.width  = canvas.offsetWidth  || 600;
        const H    = canvas.height = 240;

        const padL = 64, padR = 20, padT = 28, padB = 44;
        const chartW = W - padL - padR;
        const chartH = H - padT - padB;
        const maxVal = Math.max(...data.map(d => d.total), 1);
        const barW   = (chartW / data.length) * 0.38;
        const gap    = chartW / data.length;

        ctx.clearRect(0, 0, W, H);

        // Grid
        for (let i = 0; i <= 4; i++) {
            const y = padT + chartH - (chartH * i / 4);
            ctx.strokeStyle = "#e9ecef"; ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
            ctx.fillStyle = "#adb5bd"; ctx.font = "11px sans-serif"; ctx.textAlign = "right";
            ctx.fillText(this._fmt(maxVal * i / 4), padL - 8, y + 4);
        }

        // Bars
        data.forEach((d, i) => {
            const x      = padL + i * gap + gap * 0.12;
            const totalH = (d.total     / maxVal) * chartH;
            const collH  = (d.collected / maxVal) * chartH;

            ctx.fillStyle = "#cfe2ff";
            ctx.beginPath();
            ctx.roundRect(x, padT + chartH - totalH, barW, totalH, [4,4,0,0]);
            ctx.fill();

            ctx.fillStyle = "#0d6efd";
            ctx.beginPath();
            ctx.roundRect(x, padT + chartH - collH, barW, collH, [4,4,0,0]);
            ctx.fill();

            ctx.fillStyle = "#6c757d"; ctx.font = "11px sans-serif"; ctx.textAlign = "center";
            ctx.fillText(d.label, x + barW / 2, H - 10);
        });

        // Legend
        ctx.fillStyle = "#cfe2ff"; ctx.fillRect(padL, 6, 12, 10);
        ctx.fillStyle = "#495057"; ctx.font = "11px sans-serif"; ctx.textAlign = "left";
        ctx.fillText("Total Invoiced", padL + 16, 15);
        ctx.fillStyle = "#0d6efd"; ctx.fillRect(padL + 115, 6, 12, 10);
        ctx.fillStyle = "#495057"; ctx.fillText("Collected", padL + 131, 15);
    }

    _drawDeptChart() {
        const canvas = this.deptChartRef.el;
        if (!canvas || !this.state.dept_chart.length) return;
        const ctx    = canvas.getContext("2d");
        const W      = canvas.width  = canvas.offsetWidth  || 280;
        const H      = canvas.height = 240;
        const data   = this.state.dept_chart.slice(0, 6);
        const total  = data.reduce((s, d) => s + d.value, 0) || 1;
        const colors = ["#0d6efd","#198754","#ffc107","#dc3545","#0dcaf0","#6f42c1"];

        const cx = W / 2, cy = H / 2 - 14;
        const R  = Math.min(cx, cy) - 24;
        const r  = R * 0.54;

        ctx.clearRect(0, 0, W, H);

        let angle = -Math.PI / 2;
        data.forEach((d, i) => {
            const slice = (d.value / total) * 2 * Math.PI;
            ctx.beginPath(); ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, R, angle, angle + slice);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length]; ctx.fill();
            ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.stroke();
            angle += slice;
        });

        // Hole
        ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI);
        ctx.fillStyle = "#fff"; ctx.fill();

        // Center label
        ctx.fillStyle = "#212529"; ctx.font = "bold 12px sans-serif"; ctx.textAlign = "center";
        ctx.fillText(this._fmt(total), cx, cy + 5);

        // Legend
        const ly0 = cy + R + 14;
        data.forEach((d, i) => {
            const col = i % 2, row = Math.floor(i / 2);
            const lx  = col === 0 ? 8 : W / 2 + 4;
            const ly  = ly0 + row * 18;
            ctx.fillStyle = colors[i % colors.length]; ctx.fillRect(lx, ly, 10, 10);
            ctx.fillStyle = "#495057"; ctx.font = "10px sans-serif"; ctx.textAlign = "left";
            const lbl = d.label.length > 13 ? d.label.slice(0, 12) + "…" : d.label;
            ctx.fillText(lbl, lx + 14, ly + 9);
        });
    }

    _fmt(val) {
        if (val >= 1000000) return (val / 1000000).toFixed(1) + "M";
        if (val >= 1000)    return (val / 1000).toFixed(1) + "K";
        return val.toFixed(0);
    }

    // ── Actions ───────────────────────────────────────────────────────────

    setTab(tab) { this.state.active_tab = tab; }

    openInvoice(id) {
        this.action.doAction({ type:"ir.actions.act_window", res_model:"account.move", res_id:id, view_mode:"form", views:[[false,"form"]] });
    }
    openAllInvoices() {
        this.action.doAction({ type:"ir.actions.act_window", name:_t("All Invoices"), res_model:"account.move", view_mode:"list,form", domain:[["move_type","=","out_invoice"],["state","=","posted"]] });
    }
    openOutstandingAll() {
        this.action.doAction({ type:"ir.actions.act_window", name:_t("Outstanding Invoices"), res_model:"account.move", view_mode:"list,form", domain:[["move_type","=","out_invoice"],["state","=","posted"],["payment_state","in",["not_paid","partial"]]] });
    }
    openPatients()     { this.action.doAction("ekram_medical.action_medical_patients"); }
    openAppointments() { this.action.doAction("ekram_medical.action_medical_appointments"); }
    openLabRequests()  { this.action.doAction("ekram_medical.action_medical_lab_requests"); }

    // ── Helpers ───────────────────────────────────────────────────────────

    formatCurrency(val) {
        return (val || 0).toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
    }
    getPaymentBadgeClass(state) {
        return "badge " + ({ paid:"badge-success", partial:"badge-warning", not_paid:"badge-danger", in_payment:"badge-info", reversed:"badge-secondary" }[state] || "badge-secondary");
    }
    getOverdueBadgeClass(days) {
        if (days > 30) return "badge badge-danger";
        if (days > 7)  return "badge badge-warning";
        return "badge badge-secondary";
    }
    get collectionRate() {
        const t = this.state.kpis.revenue_this_month || 0;
        const p = this.state.kpis.revenue_paid_month || 0;
        return t ? Math.round((p / t) * 100) : 0;
    }
    get cashTotal() { return this.state.cash_data.reduce((s, j) => s + j.net, 0); }
    get bankTotal() { return this.state.bank_data.reduce((s, j) => s + j.net, 0); }
}

registry.category("actions").add("ekram_medical_admin_dashboard", AdminDashboard);