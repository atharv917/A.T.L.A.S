package com.sih.uav_backend.repository;

import com.sih.uav_backend.entity.Engine;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface EngineRepository extends JpaRepository<Engine, Long> {

    Optional<Engine> findByEngineCode(String engineCode);
}