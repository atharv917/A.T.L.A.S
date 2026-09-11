package com.sih.uav_backend.controller;

import com.sih.uav_backend.dto.MissionRequest;
import com.sih.uav_backend.entity.Mission;
import com.sih.uav_backend.service.MissionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/missions")
public class MissionController {

    private final MissionService missionService;

    public MissionController(MissionService missionService) {
        this.missionService = missionService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mission create(
            @Valid @RequestBody MissionRequest request) {

        return missionService.create(request);
    }

    @GetMapping("/engine/{engineId}")
    public List<Mission> getAll(
            @PathVariable Long engineId) {

        return missionService.getAll(engineId);
    }
}