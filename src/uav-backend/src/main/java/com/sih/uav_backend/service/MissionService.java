package com.sih.uav_backend.service;

import com.sih.uav_backend.dto.MissionRequest;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.entity.Mission;
import com.sih.uav_backend.repository.EngineRepository;
import com.sih.uav_backend.repository.MissionRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class MissionService {

    private final MissionRepository missionRepository;
    private final EngineRepository engineRepository;

    public MissionService(
            MissionRepository missionRepository,
            EngineRepository engineRepository) {

        this.missionRepository = missionRepository;
        this.engineRepository = engineRepository;
    }

    public Mission create(MissionRequest request) {

        Engine engine = engineRepository.findById(request.engineId())
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + request.engineId()
                        )
                );

        Mission mission = new Mission();

        mission.setEngine(engine);
        mission.setMissionName(request.missionName());
        mission.setMissionType(request.missionType());
        mission.setEnvironment(request.environment());

        mission.setStartTime(
                request.startTime() != null
                        ? request.startTime()
                        : LocalDateTime.now()
        );

        mission.setEndTime(request.endTime());

        mission.setStatus(
                request.status() != null
                        ? request.status()
                        : "PLANNED"
        );

        return missionRepository.save(mission);
    }

    public List<Mission> getAll(Long engineId) {

        Engine engine = engineRepository.findById(engineId)
                .orElseThrow(() ->
                        new RuntimeException(
                                "Engine not found: " + engineId
                        )
                );

        return missionRepository
                .findByEngineOrderByStartTimeDesc(engine);
    }
}