package com.sih.uav_backend.service;

import com.sih.uav_backend.dto.FaultResponse;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.FaultAlert;
import com.sih.uav_backend.entity.Telemetry;
import com.sih.uav_backend.repository.EngineRepository;
import com.sih.uav_backend.repository.FaultAlertRepository;
import com.sih.uav_backend.repository.TelemetryRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class FaultService {

    private final EngineRepository engineRepository;
    private final TelemetryRepository telemetryRepository;
    private final FaultAlertRepository faultRepository;

    public FaultService(
            EngineRepository engineRepository,
            TelemetryRepository telemetryRepository,
            FaultAlertRepository faultRepository) {

        this.engineRepository = engineRepository;
        this.telemetryRepository = telemetryRepository;
        this.faultRepository = faultRepository;
    }

    public List<FaultResponse> detect(Long engineId) {

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

        List<FaultResponse> responses = new ArrayList<>();

        check(
                engine,
                telemetry,
                responses,
                telemetry.getExhaustGasTemperature() != null &&
                        telemetry.getExhaustGasTemperature() > 900,
                "OVERHEATING",
                "HIGH",
                "Exhaust gas temperature is above the configured limit."
        );

        check(
                engine,
                telemetry,
                responses,
                telemetry.getOilPressure() != null &&
                        telemetry.getOilPressure() < 2.0,
                "LUBRICATION",
                "CRITICAL",
                "Oil pressure is below the configured safe limit."
        );

        check(
                engine,
                telemetry,
                responses,
                telemetry.getVibration() != null &&
                        telemetry.getVibration() > 8.0,
                "ABNORMAL_VIBRATION",
                "HIGH",
                "Abnormal vibration pattern detected."
        );

        check(
                engine,
                telemetry,
                responses,
                telemetry.getBatteryVoltage() != null &&
                        telemetry.getBatteryVoltage() < 12.0,
                "ALTERNATOR_BATTERY",
                "MEDIUM",
                "Battery/alternator health may require inspection."
        );

        return responses;
    }

    private void check(
            Engine engine,
            Telemetry telemetry,
            List<FaultResponse> responses,
            boolean condition,
            String faultType,
            String severity,
            String message) {

        if (!condition) {
            return;
        }

        FaultAlert alert = new FaultAlert();

        alert.setEngine(engine);
        alert.setTimestamp(LocalDateTime.now());
        alert.setFaultType(faultType);
        alert.setSeverity(severity);
        alert.setMessage(message);
        alert.setResolved(false);

        FaultAlert saved = faultRepository.save(alert);

        responses.add(
                new FaultResponse(
                        saved.getId(),
                        engine.getId(),
                        saved.getTimestamp(),
                        saved.getFaultType(),
                        saved.getSeverity(),
                        saved.getMessage(),
                        false
                )
        );
    }

    public List<FaultAlert> getAlerts(Long engineId) {

        Engine engine = engineRepository.findById(engineId)
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + engineId
                        )
                );

        return faultRepository
                .findByEngineOrderByTimestampDesc(engine);
    }
}
