---

# StockWise

> An intelligent, human-in-loop inventory and predictive procurement automation product designed to help calculate available stock in order to eliminate stockouts, prevent costly overstocking, and automate supplier reordering.

---

## Team Information

| Field                  | Details                                         |
| ---------------------- | -------------------------------------------     |
| **Team Name**          | ERROR 303                                       |
| **Team Domain**        | Domain 2                                        |
| **SDG Track (1–17)**   | SDG 9 — Industry, Innovation and Infrastructure |
| **Team Leader**        | Timothy Lai Yong Fong                           |
| **University**         | Taylor's University                             |
| **Number of Members**  | 3                                               |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/timlai0402/ERROR-303.git    |
| Live Demo         | https://stock-wise.replit.app                  |
| Slide Deck        |    [SDC2026_ERROR 303_Slide_Desk.pdf](<submission/SDC2026_ERROR 303_Slide_Desk.pdf>) |
| Demo Video        |                 |
|Pitch Video        |    [https://youtu.be/PdYZQNNhst0](https://youtu.be/PdYZQNNhst0)          |
---

## Overview

### Problem

Malaysian micro, small, and medium enterprises (MSMEs) in manufacturing, retail, and F&B still rely heavily on paper logs, fragmented WhatsApp messages, and static spreadsheets to track inventory. Manual tracking cannot adapt dynamically to fluctuating customer demand, supplier lead times, or market price volatility, resulting in frequent stockouts (baseline 25%) and costly overstocking. Inefficient manual procurement consumes hours of owners' evenings and creates avoidable material and packaging waste.

### Solution

**StockWise AI** is an automation product built to sit within the Orbyte SME business hub. It maps incoming customer orders directly against bills of materials (BOM), current stock reserves, and supplier lead times. StockWise AI blends deterministic algorithms (for exact reorder quantities and safety stock calculations) with Generative AI (to interpret supplier risk and explain restocking justifications in plain language). Built on strict human-in-the-loop governance, no capital or purchase order is committed without manager sign-off, leaving an immutable audit trail.

### Key Features

 **Automated BOM & Shortage Detection** — Automatically extracts raw material needs from incoming orders and flags potential stock deficits before production stalls.
- **Deterministic Reorder Engine + AI Insights** — Computes exact Reorder Points (ROP) and Economic Order Quantities (EOQ) mathematically, paired with GenAI summaries highlighting price trends and lead-time risks.
- **5-Step Orbyte Journey with Human Approval** — Triggers work from order events, pulls connected inventory data, runs decision logic, enforces mandatory manager approval, and logs actions into an activity ledger.
- **Supplier & Lead-Time Coordinator** — Compares multi-vendor price catalogues and delivery lead times to recommend optimal restocking schedules.
- **PDPA & Role-Based Access Control (RBAC)** — Designed for Malaysian SMEs to protect supplier commercial terms and limit purchase approvals to authorized managers.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | HTML5                        |
| Hosting / Dev | Replit                       |

---

## Project Structure

```
├── src/
│   ├── stockwise-updated                      # html web application        
├── submission/              
│   ├── SDC2026_ERROR 303_Preliminary.pdf      # Preliminary submission
│   ├── SDC2026_ERROR 303_Replit_POU.pdf       # Replit proof of use
│   ├── SDC2026_ERROR 303_Slide_Desk.pdf       # Slide Desk pdf    
│   └── SDC2026_ERROR 303_TechDeclaration.pdf  # Technology declaration
|
├── LICENSE
|
└── README.md
```

### Architecture

```
                                  ORBYTE BUSINESS HUB
 ┌────────────────┐         ┌─────────────────────────────────────────────────────────┐
 │ Incoming Order │ ──────► │ 1. Trigger & Connected Data Ingestion                   │
 └────────────────┘         │    (Order Items ◄─► Bill of Materials ◄─► Stock Levels) │
                            └────────────────────────────┬────────────────────────────┘
                                                         │
                                                         ▼
                                    ┌────────────────────────────────────────┐
                                    │ 2. Dual Decision Engine                │
                                    │    • Deterministic: ROP & EOQ Formulas │
                                    │    • GenAI: Disruption & Risk Rationale│
                                    └────────────────────┬───────────────────┘
                                                         │
                                                         ▼
 ┌───────────────────────────┐      ┌────────────────────────────────────────┐
 │ Manager Review & Approval │ ◄─── │ 3. Human-in-the-Loop Gate              │
 └─────────────┬─────────────┘      │    (Restock Quantity, Cost, Vendor)    │
               │                    └────────────────────────────────────────┘
               ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ 4. Visible Outcome & Audit Log                                             │
 │    • Generated PO dispatched to supplier                                   │
 │    • Action and timestamp committed to immutable Activity Ledger           │
 └────────────────────────────────────────────────────────────────────────────┘
```


---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [StockWise Replit Project](https://stock-wise.replit.app)
2. Sign in using the email and password provided below

email : [error303xmun@gmail.com] 
password : [123qweasd]


### Option 2 — Run Locally
1. Clone the repository in Visual Studio Code
git clone [https://github.com/timlai0402/ERROR-303.git]

2. Open the folder

3. Click Run and start debugging


---

## How We Use Replit 

Replit served as the primary cloud-native development environment and staging platform for Team ERROR 303:

- **Collaborative Development:** Our team utilized Replit Multiplayer to co-develop the UI dashboard, integrate modular components, and debug live state across distributed devices.
- **Rapid Prototyping & Staging:** Replit's instant preview and web container hosted our functional interactive MVP during Phase 1 testing and judging review.

📄 Proof of use: [`submission/SDC2026_ERROR 303_Replit_POU.pdf`]([submission/REPLIT PROOF OF USE.pdf](<submission/SDC2026_ERROR 303_REPLIT PROOF OF USE.pdf>))

---

## Challenges & Learnings

- **Overcoming the Non-Technical Learning Curve with AI-Assisted Debugging:**

Challenge: Entering the hackathon with no prior coding background, interpreting cryptic browser console errors, syntax bugs, and broken layout alignments in Replit was initially overwhelming and stalled development.

Learning: We learned to treat AI tools (such as Replit AI and Gemini) not as automatic code generators, but as patient 24/7 technical mentors. By pasting raw error logs into the AI, asking it to explain why something broke, and iteratively testing small code changes, we built a working understanding of web structure, learned how to isolate bugs, and successfully brought the interactive dashboard to life from scratch.

- **Overcoming Git & Cloud Deployment WorkflowsChallenge:**
As beginners to software version control, managing concurrent branches, avoiding merge conflicts, and synchronizing code between Replit and GitHub created friction during fast-paced prototyping. 

Learning: We developed disciplined Git hygiene—committing small, testable updates, isolating features into separate files, and automating staging deployments directly through Replit’s environment. This transformed version control from an intimidating blocker into an essential safety net for experimentation. 


## Future Improvements

- [ ] Add WhatsApp notification webhooks so SME owners can approve pending stock orders directly from their phones.
- [ ] Connect directly to Orbyte's unified SME Hub APIs for automated supplier e-invoicing and purchase order syncing.

## Team

| Name                  | Role                           | GitHub                                             |
| --------------------- | ------------------------------ | -------------------------------------------------- |
| Timothy Lai Yong Fong | Team Leader / Idea pitching    | [@timlai0402](https://github.com/timlai0402)       |
| Zayn Koh Hao Xiang    | Frontend & UI/UX Design        | [@zayn0214](https://github.com/username)           |
| Chong Zhen Xi         | Documentation & Making slides  | [Ben-newbie@](https://github.com/Ben-newbie)       |

---

## Submission Checklist

- [x] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [x] Slide deck link added
- [ ] Demo video link added
- [x] Replit used, with proof of use in `submission/`
- [ ] RunPod used, with proof of use in `submission/`
- [x] Preliminary submission completed (`SDC2026_TeamName_Preliminary.pdf`)
- [x] Technology declaration completed (`SDC2026_TeamName_TechDeclaration.pdf`)
- [x] Submission files renamed with your team name (replace `TeamName`)
- [x] "How to Run" steps verified
- [x] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).