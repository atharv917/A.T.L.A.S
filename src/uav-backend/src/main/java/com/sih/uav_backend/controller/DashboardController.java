package com.sih.uav_backend.controller;

import com.sih.uav_backend.dto.DashboardResponse;
import com.sih.uav_backend.service.DashboardService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardController {

    private final DashboardService dashboardService;

    public DashboardController(
            DashboardService dashboardService) {

        this.dashboardService = dashboardService;
    }

    @GetMapping("/{engineId}")
    public DashboardResponse getDashboard(
            @PathVariable Long engineId) {

        return dashboardService.getDashboard(engineId);
    }
}