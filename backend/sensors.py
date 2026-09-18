import random
import time
from datetime import datetime
from typing import Dict, List

class SoilMoistureSensor:
    def _init_(self, sensor_id: str, location: str):
        self.sensor_id = sensor_id
        self.location = location
        self.readings: List[Dict] = []
        self.calibration_factor = 1.0
        self.base_moisture = 50

    def read_moisture(self) -> float:
        variation = random.uniform(-10, 10)
        moisture = self.base_moisture + variation
        noise = random.uniform(-2, 2)
        moisture += noise
        return max(0, min(100, round(moisture, 2)))

    def read_moisture_with_temperature_compensation(self, temperature: float) -> float:
        moisture = self.read_moisture()
        if temperature > 35:
            moisture -= 2
        elif temperature < 10:
            moisture += 3
        return max(0, min(100, round(moisture, 2)))

    def get_reading(self, temperature: float = 25) -> Dict:
        moisture = self.read_moisture_with_temperature_compensation(temperature)
        reading = {
            "sensor_id": self.sensor_id,
            "location": self.location,
            "soil_moisture": moisture,
            "temperature": temperature,
            "timestamp": time.time(),
            "timestamp_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "NORMAL" if 25 <= moisture <= 75 else "WARNING"
        }
        self.readings.append(reading)
        return reading

    def get_readings_history(self, limit: int = 100) -> List[Dict]:
        return self.readings[-limit:]

class WaterFlowSensor:
    def _init_(self, sensor_id: str, pipe_diameter: float):
        self.sensor_id = sensor_id
        self.pipe_diameter = pipe_diameter
        self.flow_rate = 0.0
        self.total_water_used = 0.0
        self.measurements: List[Dict] = []

    def measure_flow_rate(self) -> float:
        base_flow = random.uniform(1.5, 3.0)
        variation = random.uniform(-0.5, 0.5)
        self.flow_rate = round(base_flow + variation, 2)
        return self.flow_rate

    def measure_water_usage(self, duration_seconds: float) -> float:
        flow_rate = self.measure_flow_rate()
        usage = flow_rate * duration_seconds / 3600
        usage = round(usage, 2)
        self.total_water_used += usage
        
        measurement = {
            "sensor_id": self.sensor_id,
            "flow_rate": flow_rate,
            "duration": duration_seconds,
            "water_used_liters": usage,
            "total_water_used": self.total_water_used,
            "timestamp": time.time(),
            "timestamp_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.measurements.append(measurement)
        return usage

class IrrigationController:
    def _init_(self, controller_id: str, water_flow_sensor: WaterFlowSensor):
        self.controller_id = controller_id
        self.water_flow_sensor = water_flow_sensor
        self.is_running = False
        self.status_log: List[Dict] = []

    def start_irrigation(self) -> Dict:
        if self.is_running:
            return {"status": "ALREADY_RUNNING", "message": "Irrigation is already in progress"}
        
        self.is_running = True
        self.status_log.append({
            "action": "START",
            "timestamp": time.time(),
            "controller_id": self.controller_id
        })
        return {"status": "STARTED", "message": "Irrigation started successfully"}

    def stop_irrigation(self) -> Dict:
        if not self.is_running:
            return {"status": "ALREADY_STOPPED", "message": "Irrigation is not running"}
        
        duration = time.time() - self.status_log[-1]["timestamp"] if self.status_log else 0
        water_used = self.water_flow_sensor.measure_water_usage(duration)
        
        self.is_running = False
        self.status_log.append({
            "action": "STOP",
            "timestamp": time.time(),
            "duration_seconds": round(duration, 2),
            "water_used_liters": water_used
        })
        
        return {
            "status": "STOPPED",
            "duration_seconds": round(duration, 2),
            "water_used_liters": water_used,
            "message": "Irrigation stopped successfully"
        }

    def get_status(self) -> Dict:
        return {
            "controller_id": self.controller_id,
            "is_running": self.is_running,
            "total_water_used": self.water_flow_sensor.total_water_used,
            "last_action": self.status_log[-1] if self.status_log else None
        }

class SensorDataAggregator:
    def _init_(self):
        self.moisture_sensors: Dict[str, SoilMoistureSensor] = {}
        self.water_flow_sensors: Dict[str, WaterFlowSensor] = {}
        self.controllers: Dict[str, IrrigationController] = {}

    def register_moisture_sensor(self, sensor_id: str, location: str) -> SoilMoistureSensor:
        sensor = SoilMoistureSensor(sensor_id, location)
        self.moisture_sensors[sensor_id] = sensor
        return sensor

    def register_water_flow_sensor(self, sensor_id: str, pipe_diameter: float) -> WaterFlowSensor:
        sensor = WaterFlowSensor(sensor_id, pipe_diameter)
        self.water_flow_sensors[sensor_id] = sensor
        return sensor

    def register_controller(self, controller_id: str, flow_sensor_id: str) -> IrrigationController:
        if flow_sensor_id not in self.water_flow_sensors:
            raise ValueError(f"Water flow sensor {flow_sensor_id} not found")
        
        controller = IrrigationController(controller_id, self.water_flow_sensors[flow_sensor_id])
        self.controllers[controller_id] = controller
        return controller

    def get_all_sensor_data(self) -> Dict:
        data = {
            "moisture_sensors": {},
            "water_flow_sensors": {},
            "controllers": {},
            "timestamp": time.time()
        }
        
        for sensor_id, sensor in self.moisture_sensors.items():
            data["moisture_sensors"][sensor_id] = sensor.get_reading()
        
        for sensor_id, sensor in self.water_flow_sensors.items():
            data["water_flow_sensors"][sensor_id] = {
                "flow_rate": sensor.flow_rate,
                "total_water_used": sensor.total_water_used
            }
        
        for controller_id, controller in self.controllers.items():
            data["controllers"][controller_id] = controller.get_status()
        
        return data