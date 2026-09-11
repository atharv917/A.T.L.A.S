package com.sih.uav_backend.service;

import com.sih.uav_backend.dto.TelemetryRequest;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.Telemetry;
import com.sih.uav_backend.repository.EngineRepository;
import com.sih.uav_backend.repository.TelemetryRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class TelemetryService {

    private final TelemetryRepository telemetryRepository;
    private final EngineRepository engineRepository;

    public TelemetryService(
            TelemetryRepository telemetryRepository,
            EngineRepository engineRepository) {

        this.telemetryRepository = telemetryRepository;
        this.engineRepository = engineRepository;
    }

    public Telemetry ingest(TelemetryRequest request) {

        Engine engine = engineRepository.findById(request.engineId())
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + request.engineId()
                        )
                );

        Telemetry telemetry = new Telemetry();

        telemetry.setEngine(engine);

        telemetry.setTimestamp(
                request.timestamp() != null
                        ? request.timestamp()
                        : LocalDateTime.now()
        );

        telemetry.setRpm(request.rpm());
        telemetry.setCylinderHeadTemperature(
                request.cylinderHeadTemperature()
        );
        telemetry.setExhaustGasTemperature(
                request.exhaustGasTemperature()
        );
        telemetry.setOilPressure(request.oilPressure());
        telemetry.setOilTemperature(request.oilTemperature());
        telemetry.setFuelFlow(request.fuelFlow());
        telemetry.setVibration(request.vibration());
        telemetry.setBatteryVoltage(request.batteryVoltage());
        telemetry.setAlternatorCurrent(request.alternatorCurrent());
        telemetry.setInjectionTiming(request.injectionTiming());
        telemetry.setManifoldPressure(request.manifoldPressure());
        telemetry.setEngineLoad(request.engineLoad());

        return telemetryRepository.save(telemetry);
    }

    public List<Telemetry> getLatest(Long engineId) {

        Engine engine = engineRepository.findById(engineId)
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + engineId
                        )
                );

        return telemetryRepository
                .findTop100ByEngineOrderByTimestampDesc(engine);
    }

    public List<Telemetry> getReplay(
            Long engineId,
            LocalDateTime start,
            LocalDateTime end) {

        Engine engine = engineRepository.findById(engineId)
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + engineId
                        )
                );

        return telemetryRepository
                .findByEngineAndTimestampBetweenOrderByTimestampAsc(
                        engine,
                        start,
                        end
                );
    }
}