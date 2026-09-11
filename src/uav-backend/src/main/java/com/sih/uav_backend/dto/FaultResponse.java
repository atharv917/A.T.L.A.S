package com.sih.uav_backend.dto;

import java.time.LocalDateTime;

public record FaultResponse(
        Long id,
        Long engineId,
        LocalDateTime timestamp,
        String faultType,
        String severity,
        String message,
        Boolean resolved
) {
}