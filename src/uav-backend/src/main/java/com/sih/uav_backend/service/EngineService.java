package com.sih.uav_backend.service;

import com.sih.uav_backend.dto.EngineRequest;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.repository.EngineRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class EngineService {

    private final EngineRepository engineRepository;

    public EngineService(EngineRepository engineRepository) {
        this.engineRepository = engineRepository;
    }

    public Engine createEngine(EngineRequest request) {

        if (engineRepository.findByEngineCode(request.engineCode()).isPresent()) {
            throw new RuntimeException(
                    "Engine with code " + request.engineCode() + " already exists"
            );
        }

        Engine engine = new Engine();

        engine.setEngineCode(request.engineCode());
        engine.setManufacturer(request.manufacturer());
        engine.setModel(request.model());
        engine.setEngineType(request.engineType());
        engine.setRatedPower(request.ratedPower());
        engine.setRatedRpm(request.ratedRpm());

        engine.setTotalOperatingHours(
                request.totalOperatingHours() != null
                        ? request.totalOperatingHours()
                        : 0.0
        );

        engine.setStatus(
                request.status() != null
                        ? request.status()
                        : "ACTIVE"
        );

        engine.setPlatformId(request.platformId());
        engine.setPosition(request.position());

        engine.setCreatedAt(LocalDateTime.now());

        return engineRepository.save(engine);
    }

    public List<Engine> getAllEngines() {
        return engineRepository.findAll();
    }

    public Engine getEngine(Long id) {
        return engineRepository.findById(id)
                .orElseThrow(() ->
                        new RuntimeException("Engine not found with ID: " + id)
                );
    }

    public Engine updateEngine(Long id, EngineRequest request) {

        Engine engine = getEngine(id);

        engine.setManufacturer(request.manufacturer());
        engine.setModel(request.model());
        engine.setEngineType(request.engineType());
        engine.setRatedPower(request.ratedPower());
        engine.setRatedRpm(request.ratedRpm());
        engine.setPlatformId(request.platformId());
        engine.setPosition(request.position());

        if (request.totalOperatingHours() != null) {
            engine.setTotalOperatingHours(
                    request.totalOperatingHours()
            );
        }

        if (request.status() != null) {
            engine.setStatus(request.status());
        }

        return engineRepository.save(engine);
    }

    public void deleteEngine(Long id) {

        Engine engine = getEngine(id);

        engineRepository.delete(engine);
    }
}