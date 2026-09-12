# ATLAS — Aerospace Twin for Lifecycle Assessment & Surveillance

## 1. Project Information
- **Project Title:** ATLAS – Aerospace Twin for Lifecycle Assessment & Surveillance
- **PS ID:** SIH26054
- **PS Title:** AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs
- **Category:** Software
- **Theme:** Robotics and Drones
- **Organization:** DRDO

## 2. Problem Statement
MALE UAV engine monitoring today is threshold-based — it only alarms after a limit is exceeded, discarding hours of visible warning signs beforehand. With no crew on board and no aero-piston failure dataset publicly available anywhere, a single missed early warning can cost both the aircraft and the mission.

## 3. Proposed Solution
ATLAS is a hybrid physics-and-AI digital twin that mirrors each engine's real-time health. A physics model computes what sensor readings should be given current conditions, and the gap between measured and expected drives anomaly detection, fault diagnosis, and remaining-life estimation.

## 4. Key Features
Real-time state estimation via physics and Kalman filtering; twin-engine and per-cylinder fault localization with no fault database required; health scoring that reports the weakest system rather than an average; three-tier remaining-life estimates with honest uncertainty; mission simulation comparing outcomes like flying as planned versus at reduced power; every output labeled with its data source.

## 5. Technology Stack
Frontend: React, Vite, Recharts. Backend: Java 21, Spring Boot 3.3, Spring Data JPA, Hibernate. Twin service: Python 3.11, FastAPI, NumPy, SciPy, filterpy. Database: PostgreSQL 18. Deployment: Vercel (frontend).

## 6. Architecture
See [docs/architecture.md](docs/architecture.md).

## 7. Repository Structure
```text
ATLAS/
├── README.md
├── submission/
│   ├── Copy of SIH2026-IDEA-Presentation-Format.pptx.pdf
│   └── DEMO.md
├── src/
│   ├── uav-twin/
│   ├── uav-backend/
│   └── uav-frontend/
├── docs/
│   └── architecture.md
├── assets/screenshots/
├── requirements.txt
├── .gitignore
└── LICENSE
```

## 8. Final Presentation
See [submission/Copy of SIH2026-IDEA-Presentation-Format.pptx.pdf](submission/Copy of SIH2026-IDEA-Presentation-Format.pptx.pdf).

## 9. Demo Video
See [submission/DEMO.md](submission/DEMO.md).

## 10. Screenshots
See [assets/screenshots/](assets/screenshots/).

## 11. Installation
```bash
git clone <THIS_REPOSITORY_URL>
cd ATLAS
cd src/uav-twin && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cd ../..
cd src/uav-frontend && npm install && cd ../..
```

## 12. Run
```bash
cd src/uav-twin && source .venv/bin/activate && uvicorn app.main:app --port 8000
cd src/uav-backend && ./mvnw spring-boot:run
cd src/uav-frontend && npm run dev
```

## 13. Future Scope
Integration with DRDO-supplied engine bench data; vibration instrumentation for bearing prognostics; fleet-level differencing across multiple airframes.

## Important
All data in this repository is simulated. No real engine data or DRDO-supplied dataset was used, as none exists for this problem statement.
