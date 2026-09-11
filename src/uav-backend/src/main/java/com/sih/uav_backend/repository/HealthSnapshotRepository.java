package com.sih.uav_backend.repository;

import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.HealthSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface HealthSnapshotRepository
        extends JpaRepository<HealthSnapshot, Long> {

    Optional<HealthSnapshot>
    findTopByEngineOrderByTimestampDesc(Engine engine);
}