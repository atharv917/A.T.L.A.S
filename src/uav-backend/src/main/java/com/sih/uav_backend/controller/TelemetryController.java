package com.sih.uav_backend.controller;

import com.sih.uav_backend.dto.TelemetryRequest;
import com.sih.uav_backend.entity.Telemetry;
import com.sih.uav_backend.service.TelemetryService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequestMapping("/api/v1/telemetry")
public class TelemetryController {

    private final TelemetryService telemetryService;

    public TelemetryController(TelemetryService telemetryService) {
        this.telemetryService = telemetryService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Telemetry ingest(
            @Valid @RequestBody TelemetryRequest request) {

        return telemetryService.ingest(request);
    }

    @GetMapping("/engine/{engineId}")
    public List<Telemetry> getLatest(
            @PathVariable Long engineId) {

        return telemetryService.getLatest(engineId);
    }

    @GetMapping("/replay/{engineId}")
    public List<Telemetry> replay(
            @PathVariable Long engineId,
            @RequestParam LocalDateTime start,
            @RequestParam LocalDateTime end) {

        return telemetryService.getReplay(
                engineId,
                start,
                end
        );
    }
}