package com.sih.uav_backend.entity;

import jakarta.persistence.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "telemetry")
public class Telemetry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "engine_id", nullable = false)
    private Engine engine;

    @Column(nullable = false)
    private LocalDateTime timestamp;

    private Double rpm;

    private Double cylinderHeadTemperature;

    private Double exhaustGasTemperature;

    private Double oilPressure;

    private Double oilTemperature;

    private Double fuelFlow;

    private Double vibration;

    private Double batteryVoltage;

    private Double alternatorCurrent;

    private Double injectionTiming;

    private Double manifoldPressure;

    private Double engineLoad;

    public Telemetry() {
    }

    public Long getId() {
        return id;
    }

    public Engine getEngine() {
        return engine;
    }

    public void setEngine(Engine engine) {
        this.engine = engine;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(LocalDateTime timestamp) {
        this.timestamp = timestamp;
    }

    public Double getRpm() {
        return rpm;
    }

    public void setRpm(Double rpm) {
        this.rpm = rpm;
    }

    public Double getCylinderHeadTemperature() {
        return cylinderHeadTemperature;
    }

    public void setCylinderHeadTemperature(Double cylinderHeadTemperature) {
        this.cylinderHeadTemperature = cylinderHeadTemperature;
    }

    public Double getExhaustGasTemperature() {
        return exhaustGasTemperature;
    }

    public void setExhaustGasTemperature(Double exhaustGasTemperature) {
        this.exhaustGasTemperature = exhaustGasTemperature;
    }

    public Double getOilPressure() {
        return oilPressure;
    }

    public void setOilPressure(Double oilPressure) {
        this.oilPressure = oilPressure;
    }

    public Double getOilTemperature() {
        return oilTemperature;
    }

    public void setOilTemperature(Double oilTemperature) {
        this.oilTemperature = oilTemperature;
    }

    public Double getFuelFlow() {
        return fuelFlow;
    }

    public void setFuelFlow(Double fuelFlow) {
        this.fuelFlow = fuelFlow;
    }

    public Double getVibration() {
        return vibration;
    }

    public void setVibration(Double vibration) {
        this.vibration = vibration;
    }

    public Double getBatteryVoltage() {
        return batteryVoltage;
    }

    public void setBatteryVoltage(Double batteryVoltage) {
        this.batteryVoltage = batteryVoltage;
    }

    public Double getAlternatorCurrent() {
        return alternatorCurrent;
    }

    public void setAlternatorCurrent(Double alternatorCurrent) {
        this.alternatorCurrent = alternatorCurrent;
    }

    public Double getInjectionTiming() {
        return injectionTiming;
    }

    public void setInjectionTiming(Double injectionTiming) {
        this.injectionTiming = injectionTiming;
    }

    public Double getManifoldPressure() {
        return manifoldPressure;
    }

    public void setManifoldPressure(Double manifoldPressure) {
        this.manifoldPressure = manifoldPressure;
    }

    public Double getEngineLoad() {
        return engineLoad;
    }

    public void setEngineLoad(Double engineLoad) {
        this.engineLoad = engineLoad;
    }
}