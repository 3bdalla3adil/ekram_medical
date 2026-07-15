# Part 1 — Chapters 1–4: Introduction, Overview, Installation & Configuration
`
# Ekram Medical Center Management System
## User Manual v1.0 — Part 1: Introduction, Overview, Installation & Configuration

> **Module:** `ekram_medical` | **Version:** 1.1 MVP | **Platform:** Odoo 18 Community

---

## 1. Introduction

### 1.1 Purpose
Complete operational guidance for the Ekram Medical Center Management System — a custom Odoo 18 Community module managing the full clinical and administrative lifecycle.

### 1.2 Intended Audience
| Audience | Relevant Chapters |
|---|---|
| System Administrator / IT | 3, 4, 8, 9 |
| Reception Staff | 5 |
| Doctors / Clinicians | 6 |
| Lab Technicians | 7 |
| Finance / Management | 8, 9 |

### 1.3 Version History
| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-01 | Initial release — MVP |
| 1.1 | — | Planned: SMS, insurance module |

---

## 2. System Overview

### 2.2 Core Models
| Model | Description |
|---|---|
| `res.partner` (extended) | Patients — MRN, gender, DOB, blood group, allergies |
| `medical.appointment` | Scheduling — patient, doctor, date, state |
| `medical.consultation` | Diagnosis, prescription, clinical notes |
| `medical.lab.template` | Investigation template with parameters |
| `medical.lab.request` | Lab request linked to consultation |
| `medical.lab.result` | Results with auto-flagging (Normal/High/Low/Critical) |

### 2.3 User Roles
- **Administrator** — Full access + financial reports
- **Reception** — Patients, appointments, invoicing
- **Doctor** — Own appointments, consultations, prescriptions
- **Lab Technician** — Lab requests, result entry, validation

### 2.4 Workflow

Reception: Register Patient → Book Appointment → Create Invoice Doctor: Open Appointment → Consultation → Lab Request → Print Prescription Lab: Process Request → Enter Results → Validate → Print Report Finance: Register Payment → Invoice Paid Admin: Dashboard → Revenue Charts → Outstanding Payments

---

## 3. Installation

### 3.1 Prerequisites
| Requirement | Version |
|---|---|
| Odoo | 18.0 Community |
| Python | 3.10+ |
| PostgreSQL | 14+ |

### 3.2 Steps
```bash
# 1. Place module
cp -r ekram_medical /opt/odoo/custom_addons/

# 2. Add to odoo.conf
addons_path = /opt/odoo/odoo/addons,/opt/odoo/custom_addons

# 3. Restart
sudo systemctl restart odoo

# 4. Upgrade
./odoo-bin -u ekram_medical -d your_database

3.3 Install in UI
Settings → Apps → Update Apps List
Search "Ekram Medical" → Install
Enable Developer Mode first to load demo data
4. Configuration
4.1 Company Setup
Settings → Companies → Your Company → fill Name, Address, Logo, Currency (OMR)

4.2 User Accounts
Reception: Settings → Users → New → Role: Reception
Doctor: Role: Doctor + link res.partner → Related User
Lab Tech: Role: Lab Technician
4.3 Investigation Products
Inventory → Products → New → Type: Service → link Income Account

Product	Price (OMR)
General Consultation	10.000
CBC	5.000
RFT	7.000
UA	3.000
4.4 Lab Templates
Medical → Configuration → Lab Templates → New → add parameter lines (name, unit, min, max)

Auto-flag logic:

Normal: value within [min, max]
High: value > max
Low: value < min
Critical: value > max×1.2 OR value < min×0.8
4.5 Accounting Journals
Accounting → Configuration → Journals — verify: Customer Invoices (Sale), Cash, Bank

4.6 Sequences (auto-created)
MRN: PT000001
Appointments: APT/2026/00001
Lab Requests: LAB/2026/00001
`


`---

### Part 2 — Chapters 5–7: Reception, Doctor & Lab Workflows

```markdown
# Ekram Medical Center Management System
## User Manual v1.0 — Part 2: Reception, Doctor & Laboratory Workflows

---

## 5. Reception Workflow

### 5.1 Register a New Patient
1. Medical → Reception → Patients → New
2. Fill: Name, Gender, Date of Birth, Blood Group
3. Add Emergency Contact (name + phone)
4. Add Known Allergies (free text)
5. Save → MRN auto-assigned (PT000001)

### 5.2 Book an Appointment
1. Medical → Appointments → New
2. Select Patient (MRN lookup)
3. Select Doctor
4. Set Date & Time
5. Set Type: Walk-in / Scheduled / Follow-up
6. Save → state: Draft
7. Click **Confirm** → state: Confirmed

### 5.3 Create an Invoice
1. Open the appointment → click **Create Invoice**
2. Add invoice lines (Consultation fee, lab tests)
3. Click **Confirm** → invoice state: Posted
4. Share with patient or proceed to payment

### 5.4 Register Payment
1. On the confirmed invoice → click **Register Payment**
2. Select Journal: Cash or Bank
3. Enter amount and date
4. Click **Validate** → invoice state: Paid

---

## 6. Doctor Workflow

### 6.1 Open the Doctor Dashboard
Dashboards → Doctor Dashboard
- Shows today's patient queue filtered to your appointments
- KPIs: Today's Patients, Pending Consultations, Lab Requests, Done Today

### 6.2 Start a Consultation
1. From the queue, click **Open** on a patient row
2. Appointment opens → click **Start Consultation**
3. Appointment state changes to: In Progress

### 6.3 Write the Consultation
1. Medical → Consultations → (auto-created from appointment)
2. Fill:
   - **Chief Complaint**
   - **Clinical Notes** (examination findings)
   - **Diagnosis** (ICD-style free text)
   - **Prescription** (free text — medications, dosage, duration)
   - **Follow-up Date** (optional)
3. Save

### 6.4 Request Lab Tests
1. On the consultation form → click **Request Lab Tests**
2. Select one or more Lab Templates (CBC, RFT, UA, etc.)
3. Click **Create Lab Request** → `medical.lab.request` created, state: Pending
4. Lab request appears in Lab Dashboard immediately

### 6.5 Print Prescription
1. On the consultation form → click **Print Prescription**
2. PDF opens with:
   - Patient info + allergy alert
   - Doctor info
   - Rx symbol + prescription text
   - 30-day validity notice
   - Follow-up instructions
   - Three-party signature block

### 6.6 Complete the Appointment
1. Back on the appointment → click **Mark Done**
2. Appointment state: Done

---

## 7. Laboratory Workflow

### 7.1 Open the Lab Dashboard
Dashboards → Lab Dashboard
- Pending Requests list (with priority dots — pulsing red for critical)
- Results to Enter list
- KPIs: Pending, In Progress, Completed Today, Critical Flags

### 7.2 Process a Lab Request
1. Medical → Laboratory → Lab Requests
2. Open a request in Pending state
3. Click **Process** → state: In Progress
4. System auto-creates one `medical.lab.result` per template
5. Each result record auto-loads all parameter lines from the template

### 7.3 Enter Results
1. Open a result record (or click from the request)
2. For each parameter line, enter the **Result Value**
3. Flag is computed automatically:
   - Green badge: Normal
   - Yellow badge: High or Low
   - Red badge: Critical
4. Save after each result

### 7.4 Validate Results
1. When all lines are filled → click **Validate**
2. Result state: Validated
3. When all results for a request are validated → request state: Completed

### 7.5 Print Lab Report
1. On the lab request or result → click **Print Lab Report**
2. PDF opens with:
   - Blue title bar per investigation
   - Color-coded results table (yellow = High/Low, red = Critical)
   - Flag legend
   - Validation info + QR placeholder
   - Three-party signature block
`
# Part 3 — Chapters 8–12: Admin, Invoice Cycle, Security, Troubleshooting & Glossary

# Ekram Medical Center Management System
## User Manual v1.0 — Part 3: Admin Dashboard, Invoice Cycle, Security & Troubleshooting

---

## 8. Admin Dashboard & Reports

### 8.1 Opening the Admin Dashboard
Dashboards → Admin Dashboard (requires Administrator role)

### 8.2 KPI Cards (top row)
| KPI | Source |
|---|---|
| Total Revenue (Month) | Posted invoices, current month |
| Outstanding Payments | Invoices in state: posted, not fully paid |
| Patients Today | res.partner is_patient, created today |
| Appointments Today | medical.appointment, today |
| Collection Rate | Paid / Total invoiced × 100% |
| Cash Balance | Cash journal balance |
| Bank Balance | Bank journal balance |
| Critical Lab Flags | medical.lab.result.line flag = Critical |

### 8.3 Revenue Bar Chart
- 6-month rolling bar chart (HTML Canvas, no external libraries)
- X-axis: month labels; Y-axis: OMR amount
- Data from `account.move` (type=out_invoice, state=posted)

### 8.4 Department Donut Chart
- Breakdown by product category (Medical Services vs Lab Tests)
- Rendered with HTML Canvas

### 8.5 Cash / Bank Journal Tables
- Shows each cash/bank journal with current balance
- Refreshes on dashboard load

### 8.6 Invoice Tables (tabbed)
- **Recent Invoices:** last 20 posted invoices
- **Outstanding:** all invoices with amount_residual > 0, color-coded red if overdue

---

## 9. Complete Invoice Cycle

### 9.1 Step-by-Step (12 Steps)

| Step | Actor | Action | Record Created/Updated |
|---|---|---|---|
| 1 | Reception | Register patient | `res.partner` (is_patient=True, MRN assigned) |
| 2 | Reception | Book appointment | `medical.appointment` (state: draft) |
| 3 | Reception | Confirm appointment | `medical.appointment` (state: confirmed) |
| 4 | Doctor | Start consultation | `medical.appointment` (state: in_progress) |
| 5 | Doctor | Write consultation | `medical.consultation` (diagnosis, prescription) |
| 6 | Doctor | Request lab tests | `medical.lab.request` (state: pending) |
| 7 | Lab Tech | Process request | `medical.lab.result` records auto-created |
| 8 | Lab Tech | Enter & validate results | `medical.lab.result` (state: validated) |
| 9 | Doctor | Mark appointment done | `medical.appointment` (state: done) |
| 10 | Reception | Create invoice | `account.move` (type: out_invoice, state: draft) |
| 11 | Reception | Confirm invoice | `account.move` (state: posted) |
| 12 | Reception | Register payment | `account.payment` → invoice (state: paid) |

### 9.2 Sample Invoice

Ekram Medical Center Invoice #: INV/2026/00042 Patient: Mohammed Al-Balushi (PT000001) Date: 2026-07-01

Lines: General Consultation 10.000 OMR CBC - Complete Blood Count 5.000 OMR RFT - Renal Function Test 7.000 OMR ---------- Total: 22.000 OMR

Payment: Cash — 2026-07-01 — PAID

---

## 10. Security & Access Control

### 10.1 Groups
| Group | XML ID |
|---|---|
| Administrator | `ekram_medical.group_medical_admin` |
| Reception | `ekram_medical.group_medical_reception` |
| Doctor | `ekram_medical.group_medical_doctor` |
| Lab Technician | `ekram_medical.group_medical_lab` |

### 10.2 Permissions Matrix
| Model | Admin | Reception | Doctor | Lab Tech |
|---|---|---|---|---|
| res.partner (patients) | CRUD | CRUD | R | R |
| medical.appointment | CRUD | CRUD | R (own) | R |
| medical.consultation | CRUD | R | CRUD (own) | R |
| medical.lab.request | CRUD | CR | CR | CRUD |
| medical.lab.result | CRUD | R | R | CRUD |
| account.move | CRUD | CRU | R | — |
| account.payment | CRUD | CRU | — | — |

### 10.3 Record Rules
- **Doctor — Own Appointments:** `appointment.doctor_id.user_id = uid`
- **Doctor — Own Consultations:** `consultation.appointment_id.doctor_id.user_id = uid`
- **Lab — All Requests:** Lab Technicians see all lab requests (no user filter)
- **Reception — All Records:** Reception sees all patients and appointments

### 10.4 Menu Visibility
| Menu Item | Admin | Reception | Doctor | Lab |
|---|---|---|---|---|
| Admin Dashboard | Yes | — | — | — |
| Doctor Dashboard | Yes | — | Yes | — |
| Lab Dashboard | Yes | — | — | Yes |
| Reception Dashboard | Yes | Yes | — | — |
| Configuration | Yes | — | — | — |
| Accounting | Yes | Yes | — | — |

---

## 11. Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| MRN not assigned | Sequence not installed | Upgrade module: `-u ekram_medical` |
| Doctor Dashboard shows no patients | Doctor partner not linked to user | Medical → Contacts → open doctor → set Related User |
| Lab request not appearing in Lab Dashboard | Request still in Draft | Doctor must click "Process" to move to Pending |
| Invoice not showing in Admin Dashboard | Invoice in Draft state | Confirm the invoice (state must be Posted) |
| PDF report missing logo | Company logo not uploaded | Settings → Companies → upload logo |
| Auto-flag not computing | Result value is text, not numeric | Ensure result_type = Numeric on template line |
| Demo data not loaded | Developer mode was off during install | Uninstall, enable dev mode, reinstall |
| Permission denied on consultation | Doctor not in Doctor group | Settings → Users → assign Doctor role |
| Cash balance shows 0 | Cash journal not configured | Accounting → Journals → create Cash journal |
| Module not found after file copy | Addons path not updated | Edit odoo.conf, restart service |

---

## 12. Glossary

| Term | Definition |
|---|---|
| MRN | Medical Record Number — unique patient identifier (format: PT000001) |
| Consultation | Clinical encounter record containing diagnosis, notes, and prescription |
| Lab Template | Predefined set of test parameters for an investigation type (e.g., CBC) |
| Lab Request | Order for one or more lab investigations linked to a consultation |
| Lab Result | Completed investigation with entered values and computed flags |
| Flag | Auto-computed result status: Normal, High, Low, or Critical |
| Critical | Result deviating >20% beyond normal range — triggers red alert |
| Invoice | `account.move` record of type out_invoice representing charges to patient |
| Payment | `account.payment` record registering cash or bank receipt |
| Collection Rate | Percentage of invoiced amount that has been collected |
| OWL 2 | Odoo Web Library v2 — JavaScript framework used for dashboards |
| QWeb | Odoo's XML-based templating engine used for PDF reports |
| ACL | Access Control List — defines model-level CRUD permissions per group |
| Record Rule | Domain-based filter restricting which records a user can see |
| Sequence | Auto-incrementing number generator (MRN, APT, LAB prefixes) |
| ir.actions.client | Odoo action type that loads a custom OWL component as a full page |
| account.move | Odoo's unified accounting document model (invoices, bills, journal entries) |


