package com.sih.uav_backend.service;

import com.sih.uav_backend.dto.HealthResponse;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.HealthSnapshot;
import com.sih.uav_backend.entity.Telemetry;
import com.sih.uav_backend.repository.EngineRepository;
import com.sih.uav_backend.repository.HealthSnapshotRepository;
import com.sih.uav_backend.repository.TelemetryRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class HealthService {

    private final EngineRepository engineRepository;
    private final TelemetryRepository telemetryRepository;
    private final HealthSnapshotRepository healthRepository;

    public HealthService(
            EngineRepository engineRepository,
            TelemetryRepository telemetryRepository,
            HealthSnapshotRepository healthRepository) {

        this.engineRepository = engineRepository;
        this.telemetryRepository = telemetryRepository;
        this.healthRepository = healthRepository;
    }

    public HealthResponse calculate(Long engineId) {

        Engine engine = engineRepository.findById(engineId)
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + engineId
                        )
                );

        Telemetry telemetry = telemetryRepository
                .findTop100ByEngineOrderByTimestampDesc(engine)
                .stream()
                .findFirst()
                .orElseThrow(() ->
                        new RuntimeException(
                                "No telemetry available"
                        )
                );

        double score = 100.0;
        String recommendation = "Engine operating normally.";

        if (telemetry.getCylinderHeadTemperature() != null &&
                telemetry.getCylinderHeadTemperature() > 220) {
            score -= 20;
            recommendation = "Check cylinder head temperature.";
        }

        if (telemetry.getExhaustGasTemperature() != null &&
                telemetry.getExhaustGasTemperature() > 900) {
            score -= 20;
            recommendation = "High EGT detected.";
        }

        if (telemetry.getOilPressure() != null &&
                telemetry.getOilPressure() < 2.0) {
            score -= 25;
            recommendation = "Inspect lubrication system.";
        }

        if (telemetry.getVibration() != null &&
                telemetry.getVibration() > 8.0) {
            score -= 20;
            recommendation = "Abnormal vibration detected.";
        }

        if (telemetry.getBatteryVoltage() != null &&
                telemetry.getBatteryVoltage() < 12.0) {
            score -= 10;
            recommendation = "Check battery/alternator system.";
        }

        score = Math.max(0, Math.min(100, score));

        String status;

        if (score >= 80) {
            status = "HEALTHY";
        } else if (score >= 60) {
            status = "WARNING";
        } else {
            status = "CRITICAL";
        }

        double anomalyScore = 1.0 - (score / 100.0);

        HealthSnapshot snapshot = new HealthSnapshot();

        snapshot.setEngine(engine);
        snapshot.setTimestamp(LocalDateTime.now());
        snapshot.setHealthScore(score);
        snapshot.setHealthStatus(status);
        snapshot.setAnomalyScore(anomalyScore);
        snapshot.setRecommendation(recommendation);

        healthRepository.save(snapshot);

        return new HealthResponse(
                engineId,
                score,
                status,
                anomalyScore,
                recommendation
        );
    }
}