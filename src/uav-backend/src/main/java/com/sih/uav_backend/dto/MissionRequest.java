package com.sih.uav_backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;

public record MissionRequest(

        @NotNull
        Long engineId,

        @NotBlank
        String missionName,

        String missionType,

        String environment,

        LocalDateTime startTime,

        LocalDateTime endTime,

        String status
) {
}