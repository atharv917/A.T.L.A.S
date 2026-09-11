package com.sih.uav_backend.controller;

import com.sih.uav_backend.dto.EngineRequest;
import com.sih.uav_backend.entity.Engine;
import com.sih.uav_backend.service.EngineService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/engines")
public class EngineController {

    private final EngineService engineService;

    public EngineController(EngineService engineService) {
        this.engineService = engineService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Engine createEngine(
            @Valid @RequestBody EngineRequest request) {

        return engineService.createEngine(request);
    }

    @GetMapping
    public List<Engine> getAllEngines() {
        return engineService.getAllEngines();
    }

    @GetMapping("/{id}")
    public Engine getEngine(@PathVariable Long id) {
        return engineService.getEngine(id);
    }

    @PutMapping("/{id}")
    public Engine updateEngine(
            @PathVariable Long id,
            @Valid @RequestBody EngineRequest request) {

        return engineService.updateEngine(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteEngine(@PathVariable Long id) {
        engineService.deleteEngine(id);
    }
}