
## Project

SIH26054. Spring Boot + PostgreSQL backend. Java 21, Spring Data JPA. Package
`com.sih.uav_backend`. Runs on port 8080, DB `uav_engine` on `localhost:5432`.
Orchestration + persistence only — physics and ML are in the Python `uav-twin`
service, called over REST.

**Status in this tree:** fresh scaffold generated from the contracts (the
original repo + `backend-fix/` pack were not available here). See README.md
"This is a fresh scaffold, not your existing repo" before applying. Keep every
change incremental and keep `./mvnw clean compile` passing at each step.

## What exists here

- `db/migration/V2__twin_upgrade.sql` — Flyway migration (Postgres): engine,
  telemetry (+ scalar mirrors, unique `(engine_id, seq)`, `/series` indexes),
  twin_state, fault_alert, seeds two TAPAS-01 engines.
- Entities: `Engine`, `Telemetry` (with `syncScalarsFromArrays()`), `TwinState`,
  `FaultAlert`, enums `EngineType` / `DataSource` / `EnginePosition`,
  `DoubleListJsonConverter`.
- `TelemetryRepository` — paged history + downsampled `/series` + `findMaxSeq`
  + `existsByEngineIdAndSeq` + `countByEngineId` + `findPairedFrame`.
- `TwinClient` (`@Service`) — REST to the Python twin; never throws, never
  blocks ingest. `twin.service.url=http://localhost:8000` (default coded in).
- `TelemetryService` + `TelemetryWriter` — idempotent ingest, twin call AFTER
  the telemetry row commits, twin failure logged and swallowed.
- `DashboardService` + `TwinPayloadMapper` — one aggregated
  `GET /api/v1/dashboard/{engineId}`, `countByEngineId` (not `count()`), twin
  snapshot folded and re-keyed to the frontend contract.
- `SimulateController` — `POST /api/v1/engines/{engineId}/simulate` → twin.

## Do not

- Do not touch package names or "clean up" unrelated code under this deadline.
- Do not add auth / multi-tenancy / WebSocket / MQTT.
- Do not implement the twin's physics in Java — call it over HTTP.

## Verify frequently

`./mvnw clean compile` after each applied file. After ingestion changes: POST a
telemetry frame and confirm it lands in the DB with a `seq`, and that a
`twin_state` row appears when the Python service is up — and nothing breaks when
it is down.
