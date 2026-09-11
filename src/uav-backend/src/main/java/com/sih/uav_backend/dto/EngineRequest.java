package com.sih.uav_backend.dto;

import jakarta.validation.constraints.NotBlank;

public record EngineRequest(

        @NotBlank(message = "Engine code is required")
        String engineCode,

        String manufacturer,

        String model,

        String engineType,

        Double ratedPower,

        Integer ratedRpm,

        Double totalOperatingHours,

        String status
) {
}
