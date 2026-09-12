package com.sih.uav_backend.dto;

public record HealthResponse(
        Long engineId,
        Double healthScore,
        String healthStatus,
        Double anomalyScore,
        String recommendation,
        PairedEngineSummary pairedEngine
) {
}