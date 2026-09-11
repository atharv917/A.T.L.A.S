package com.sih.uav_backend.repository;

import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.Mission;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MissionRepository
        extends JpaRepository<Mission, Long> {

    List<Mission> findByEngineOrderByStartTimeDesc(
            Engine engine
    );
}
