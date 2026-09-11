package com.sih.uav_backend.repository;

import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.FaultAlert;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface FaultAlertRepository
        extends JpaRepository<FaultAlert, Long> {

    List<FaultAlert> findByEngineOrderByTimestampDesc(
            Engine engine
    );
}