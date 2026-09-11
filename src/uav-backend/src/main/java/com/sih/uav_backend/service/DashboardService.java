package com.sih.uav_backend.service;

import com.sih.uav_backend.dto.DashboardResponse;
import com.sih.uav_backend.dto.HealthResponse;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.FaultAlert;
import com.sih.uav_backend.repository.EngineRepository;
import com.sih.uav_backend.repository.FaultAlertRepository;
import com.sih.uav_backend.repository.TelemetryRepository;
import org.springframework.stereotype.Service;

@Service
public class DashboardService {

    private final EngineRepository engineRepository;
    private final TelemetryRepository telemetryRepository;
    private final FaultAlertRepository faultRepository;
    private final HealthService healthService;

    public DashboardService(
            EngineRepository engineRepository,
            TelemetryRepository telemetryRepository,
            FaultAlertRepository faultRepository,
            HealthService healthService) {

        this.engineRepository = engineRepository;
        this.telemetryRepository = telemetryRepository;
        this.faultRepository = faultRepository;
        this.healthService = healthService;
    }

    public DashboardResponse getDashboard(Long engineId) {

        Engine engine = engineRepository.findById(engineId)
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + engineId
                        )
                );

        HealthResponse health =
                healthService.calculate(engineId);

        long activeFaults =
                faultRepository
                        .findByEngineOrderByTimestampDesc(engine)
                        .stream()
                        .filter(alert -> Boolean.FALSE.equals(alert.getResolved()))
                        .count();

        long telemetryRecords =
                telemetryRepository.count();

        return new DashboardResponse(
                engine.getId(),
                engine.getEngineCode(),
                engine.getStatus(),
                health.healthScore(),
                health.healthStatus(),
                health.anomalyScore(),
                activeFaults,
                telemetryRecords,
                health.recommendation()
        );
    }
}