package com.sih.uav_backend.controller;

import com.sih.uav_backend.dto.FaultResponse;
import com.sih.uav_backend.entity.FaultAlert;
import com.sih.uav_backend.service.FaultService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/faults")
public class FaultController {

    private final FaultService faultService;

    public FaultController(FaultService faultService) {
        this.faultService = faultService;
    }

    @PostMapping("/detect/{engineId}")
    public List<FaultResponse> detect(
            @PathVariable Long engineId) {

        return faultService.detect(engineId);
    }

    @GetMapping("/{engineId}")
    public List<FaultAlert> getAlerts(
            @PathVariable Long engineId) {

        return faultService.getAlerts(engineId);
    }
}