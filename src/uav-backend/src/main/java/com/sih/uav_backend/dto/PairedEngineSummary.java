package com.sih.uav_backend.dto;

public record PairedEngineSummary(
        Long engineId,
        String engineCode,
        Double healthScore,
        String healthStatus,
        Double anomalyScore
) {
}
