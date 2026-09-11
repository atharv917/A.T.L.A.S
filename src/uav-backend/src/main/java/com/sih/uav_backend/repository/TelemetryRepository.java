package com.sih.uav_backend.repository;

import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.Telemetry;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface TelemetryRepository
        extends JpaRepository<Telemetry, Long> {

    List<Telemetry> findTop100ByEngineOrderByTimestampDesc(
            Engine engine
    );

    List<Telemetry> findByEngineAndTimestampBetweenOrderByTimestampAsc(
            Engine engine,
            LocalDateTime start,
            LocalDateTime end
    );
}

