import numpy as np
from collections import defaultdict


class EmissionModel:
    def __init__(self):
        self.emission_factors = {
            'passenger_car': {
                'CO': 2.3,
                'NOx': 0.15,
                'PM': 0.01,
                'HC': 0.2,
                'CO2': 210
            },
            'bus': {
                'CO': 6.5,
                'NOx': 1.2,
                'PM': 0.15,
                'HC': 0.5,
                'CO2': 800
            },
            'truck': {
                'CO': 5.0,
                'NOx': 1.8,
                'PM': 0.2,
                'HC': 0.4,
                'CO2': 650
            }
        }

        self.speed_correction_factors = {
            'low_speed': 1.5,
            'idle': 2.0,
            'cruise': 1.0,
            'accelerate': 1.3,
            'decelerate': 0.8
        }

        self.temperature_factor = 1.0
        self.humidity_factor = 1.0

    def calculate_vehicle_emission(self, vehicle, speed, distance, mode='cruise'):
        vehicle_type = getattr(vehicle, 'vehicle_type', 'passenger_car')
        factors = self.emission_factors.get(vehicle_type, self.emission_factors['passenger_car'])
        mode_factor = self.speed_correction_factors.get(mode, 1.0)

        emissions = {}
        for pollutant, base_factor in factors.items():
            if pollutant == 'CO2':
                emission = base_factor * distance / 1000 * mode_factor
            else:
                emission = base_factor * distance / 1000 * mode_factor
            emissions[pollutant] = emission * self.temperature_factor * self.humidity_factor

        return emissions

    def calculate_idle_emission(self, vehicle, idle_time_seconds):
        vehicle_type = getattr(vehicle, 'vehicle_type', 'passenger_car')
        factors = self.emission_factors.get(vehicle_type, self.emission_factors['passenger_car'])
        idle_factor = self.speed_correction_factors['idle']

        emissions = {}
        for pollutant, base_factor in factors.items():
            idle_rate = base_factor / 3600
            emissions[pollutant] = idle_rate * idle_time_seconds * idle_factor

        return emissions

    def calculate_road_emission(self, road, vehicles):
        total_emissions = defaultdict(float)

        for vehicle in vehicles:
            speed = vehicle.speed
            distance = max(0.01, speed)

            if speed == 0:
                mode = 'idle'
                emissions = self.calculate_idle_emission(vehicle, 1)
            elif speed < 5:
                mode = 'low_speed'
                emissions = self.calculate_vehicle_emission(vehicle, speed, distance, mode)
            elif speed < 10:
                mode = 'accelerate' if getattr(vehicle, '_prev_speed', 0) < speed else 'decelerate'
                emissions = self.calculate_vehicle_emission(vehicle, speed, distance, mode)
            else:
                mode = 'cruise'
                emissions = self.calculate_vehicle_emission(vehicle, speed, distance, mode)

            for pollutant, value in emissions.items():
                total_emissions[pollutant] += value

            vehicle._prev_speed = speed

        return dict(total_emissions)

    def calculate_network_emission(self, roads):
        network_emissions = defaultdict(float)
        road_emissions = {}

        for road_id, road in roads.items():
            vehicles = road.get("vehicles", [])
            emissions = self.calculate_road_emission(road, vehicles)
            road_emissions[road_id] = emissions

            for pollutant, value in emissions.items():
                network_emissions[pollutant] += value

        return {
            'road_emissions': road_emissions,
            'total_emissions': dict(network_emissions)
        }

    def calculate_emission_from_queue(self, road_id, queue_length, idle_time=1):
        total_emissions = defaultdict(float)
        car_factors = self.emission_factors['passenger_car']

        for _ in range(queue_length):
            emissions = self.calculate_idle_emission(
                type('DummyVehicle', (), {'vehicle_type': 'passenger_car'})(),
                idle_time
            )
            for pollutant, value in emissions.items():
                total_emissions[pollutant] += value

        return {
            'road_id': road_id,
            'queue_length': queue_length,
            'emissions': dict(total_emissions)
        }

    def estimate_fuel_consumption(self, vehicle, distance, speed):
        vehicle_type = getattr(vehicle, 'vehicle_type', 'passenger_car')

        base_consumption = {
            'passenger_car': 8.0,
            'bus': 35.0,
            'truck': 28.0
        }

        base = base_consumption.get(vehicle_type, 8.0)

        if speed == 0:
            consumption = base * 0.5 / 100
        elif speed < 20:
            consumption = base * 1.5 / 100
        elif speed < 50:
            consumption = base * 1.2 / 100
        elif speed < 90:
            consumption = base / 100
        else:
            consumption = base * 1.3 / 100

        return consumption * distance / 1000

    def get_emission_summary(self, roads, time_elapsed):
        emission_data = self.calculate_network_emission(roads)
        total = emission_data['total_emissions']

        summary = {
            'time_elapsed': time_elapsed,
            'total_emissions': total,
            'emission_rates': {k: v / max(1, time_elapsed) for k, v in total.items()},
            'road_contributions': {},
            'fuel_consumption': 0
        }

        for road_id, emissions in emission_data['road_emissions'].items():
            road_total = sum(emissions.values())
            summary['road_contributions'][road_id] = {
                'emissions': emissions,
                'percentage': (road_total / max(0.001, sum(total.values()))) * 100
            }

        for road_id, road in roads.items():
            for vehicle in road.get("vehicles", []):
                distance = max(0.01, vehicle.speed)
                fuel = self.estimate_fuel_consumption(vehicle, distance, vehicle.speed)
                summary['fuel_consumption'] += fuel

        return summary

    def get_emission_index(self, roads):
        emission_data = self.calculate_network_emission(roads)
        total = sum(emission_data['total_emissions'].values())
        num_vehicles = sum(len(r.get("vehicles", [])) for r in roads.values())

        if num_vehicles == 0:
            return 0.0

        base_emission_per_vehicle = 0.5
        emission_per_vehicle = total / num_vehicles

        index = min(1.0, emission_per_vehicle / base_emission_per_vehicle)
        return index


class BusEmissionModel(EmissionModel):
    def __init__(self):
        super().__init__()
        self.emission_factors['bus_electric'] = {
            'CO': 0.0,
            'NOx': 0.0,
            'PM': 0.0,
            'HC': 0.0,
            'CO2': 50
        }
        self.emission_factors['bus_hybrid'] = {
            'CO': 3.0,
            'NOx': 0.6,
            'PM': 0.08,
            'HC': 0.25,
            'CO2': 400
        }

    def calculate_bus_emission(self, bus, distance, speed, passenger_load=0.7):
        base_emissions = self.calculate_vehicle_emission(bus, speed, distance)

        load_factor = 0.8 + passenger_load * 0.4
        for pollutant in base_emissions:
            base_emissions[pollutant] *= load_factor

        return base_emissions
