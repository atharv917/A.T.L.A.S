package com.sih.uav_backend.dto;

public record DashboardResponse(

        Long engineId,

        String engineCode,

        String engineStatus,

        Double healthScore,

        String healthStatus,

        Double anomalyScore,

        long activeFaults,

        long telemetryRecords,

        String recommendation
) {
}
