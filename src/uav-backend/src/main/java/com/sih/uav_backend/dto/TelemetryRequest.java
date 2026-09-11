package com.sih.uav_backend.dto;

import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;

public record TelemetryRequest(

        @NotNull(message = "Engine ID is required")
        Long engineId,

        LocalDateTime timestamp,

        Double rpm,

        Double cylinderHeadTemperature,

        Double exhaustGasTemperature,

        Double oilPressure,

        Double oilTemperature,

        Double fuelFlow,

        Double vibration,

        Double batteryVoltage,

        Double alternatorCurrent,

        Double injectionTiming,

        Double manifoldPressure,

        Double engineLoad
) {
}