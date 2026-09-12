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
Frontend: React, Vite, Recharts. Backend: Java 21, Spring Boot 3.3, Spring Data JPA, Hibernate. Twin service: Python 3.11, FastAPI, NumPy, SciPy, filterpy. Database: PostgreSQL 18. Deployment: Vercel (frontend, planned).

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
See [submission/Copy of SIH2026-IDEA-Presentation-Format.pptx.pdf](<submission/Copy of SIH2026-IDEA-Presentation-Format.pptx.pdf>).

## 9. Demo Video
See [submission/DEMO.md](submission/DEMO.md).

## 10. Screenshots
See [assets/screenshots/](assets/screenshots/).

## 11. Installation

**Prerequisites:** JDK 21, Python 3.11+, Node.js 18+/npm, PostgreSQL running locally. Maven is not installed separately — the backend uses the bundled `./mvnw` wrapper.

```bash
git clone <THIS_REPOSITORY_URL>
cd ATLAS

# --- Twin service (Python) ---
cd src/uav-twin
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ../..

# --- Backend (Java) ---
sudo -u postgres createdb uav_engine
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"
# application.properties is gitignored (it holds local DB credentials).
# If it does not already exist in your checkout, create
#   src/uav-backend/src/main/resources/application.properties
# with:
#   spring.datasource.url=jdbc:postgresql://localhost:5432/uav_engine
#   spring.datasource.username=postgres
#   spring.datasource.password=postgres
#   twin.service.url=http://localhost:8000

# --- Frontend (Node) ---
cd src/uav-frontend
npm install
cd ../..
```

## 12. Run

Start the three services in this order — the backend calls the twin, and the frontend calls the backend:

```bash
# Terminal 1 — twin service
cd src/uav-twin && source .venv/bin/activate && uvicorn app.main:app --port 8000

# Terminal 2 — backend
cd src/uav-backend && ./mvnw spring-boot:run

# Terminal 3 — frontend
cd src/uav-frontend && npm run dev
```

Open `http://localhost:5173`. The dashboard runs in mock mode by default (`VITE_USE_MOCK=true`) and renders a full scripted degradation scenario with no backend required. To view live data from the real backend and twin instead, set `VITE_USE_MOCK=false` in a `.env` file inside `src/uav-frontend` and restart the dev server.

The backend never fails to start or ingest telemetry if the twin service is unreachable — it degrades gracefully and reports `twinAvailable: false` instead.

## 13. Future Scope

The current prototype validates the core methodology under a hard constraint: no real engine and no DRDO-supplied dataset exist for this problem statement, so every capability here had to be built and proven on simulated data. The paths below are what closes that gap, in order of impact:

**Engine and physics validation.** The physics core currently runs against a generic open-source piston-engine model, not the target Austro E4 or indigenous VRDE/JAYEM turbocharged CRDi engine. With DRDO-supplied bench data — ideally with induced faults on a real or representative engine — the same architecture recalibrates directly: no redesign, only parameter tuning. This also supplies the missing damage-law constants (activation energy, valve thermal budget) that currently make Tier-1 RUL parametric rather than absolute.

**Vibration-based bearing and gearbox prognostics.** Bearing failure is the one fault mode this system cannot currently see early, because it requires high-rate vibration data that no accelerometer exists to provide yet. The edge feature-extraction interface (order analysis, envelope demodulation) is already specified in the architecture and is the natural next sensor to add.

**Full Unscented Kalman Filter with covariance propagation.** The prototype's parameter estimator uses windowed least-squares for speed and reliability under deadline. A full UKF is a drop-in upgrade to the same interface, and it adds calibrated per-parameter uncertainty that currently only exists at the top level.

**Fleet-level differencing.** Twin-engine and per-cylinder differencing solve the environment-vs-degradation problem for a single airframe. They cannot separate a duty-cycle effect (e.g. consistently flying hot, low-altitude sorties) from genuine accelerated wear on one aircraft — that requires comparing many airframes' histories, which becomes possible once more than two engines' worth of fleet data exists.

**Real FADEC integration.** The bus protocol and published parameter list for the actual UAV engine controller are unknown today. The system already isolates this dependency into a single swappable adapter module, so integrating the real interface is a contained addition rather than a redesign.

**Production-grade security.** The prototype implements TLS and basic request validation. A fielded system requires cryptographic frame authentication (to prevent spoofed or replayed telemetry), secure boot on the edge hardware, and accreditation for handling fleet health data as a classification-sensitive asset — since knowing which aircraft are near overhaul reveals operational readiness.

**Algorithmic benchmarking.** The RUL uncertainty machinery (trend extrapolation, calibration, prognostic horizon) is architected to be validated independently on public turbofan degradation datasets such as N-CMAPSS, where ground truth exists — separating "does the math work" from "does it work on this engine," which no current failure dataset can answer for any team on this problem.

## Important
All data in this repository is simulated. No real engine data or DRDO-supplied dataset was used, as none exists for this problem statement — this is disclosed on every dashboard panel via a persistent `DATA SOURCE: SIMULATED` badge.
