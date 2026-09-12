package com.sih.uav_backend.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "engines")
public class Engine {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String engineCode;

    private String manufacturer;

    private String model;

    private String engineType;

    private Double ratedPower;

    private Integer ratedRpm;

    private Double totalOperatingHours;

    private String status;

    private String platformId;

    private String position;

    private LocalDateTime createdAt;

    public Engine() {
    }

    public Long getId() {
        return id;
    }

    public String getEngineCode() {
        return engineCode;
    }

    public void setEngineCode(String engineCode) {
        this.engineCode = engineCode;
    }

    public String getManufacturer() {
        return manufacturer;
    }

    public void setManufacturer(String manufacturer) {
        this.manufacturer = manufacturer;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public String getEngineType() {
        return engineType;
    }

    public void setEngineType(String engineType) {
        this.engineType = engineType;
    }

    public Double getRatedPower() {
        return ratedPower;
    }

    public void setRatedPower(Double ratedPower) {
        this.ratedPower = ratedPower;
    }

    public Integer getRatedRpm() {
        return ratedRpm;
    }

    public void setRatedRpm(Integer ratedRpm) {
        this.ratedRpm = ratedRpm;
    }

    public Double getTotalOperatingHours() {
        return totalOperatingHours;
    }

    public void setTotalOperatingHours(Double totalOperatingHours) {
        this.totalOperatingHours = totalOperatingHours;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getPlatformId() {
        return platformId;
    }

    public void setPlatformId(String platformId) {
        this.platformId = platformId;
    }

    public String getPosition() {
        return position;
    }

    public void setPosition(String position) {
        this.position = position;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}