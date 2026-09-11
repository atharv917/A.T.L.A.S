package com.sih.uav_backend.controller;

import com.sih.uav_backend.dto.HealthResponse;
import com.sih.uav_backend.service.HealthService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/health")
public class HealthController {

    private final HealthService healthService;

    public HealthController(HealthService healthService) {
        this.healthService = healthService;
    }

    @GetMapping("/{engineId}")
    public HealthResponse getHealth(
            @PathVariable Long engineId) {

        return healthService.calculate(engineId);
    }
}
