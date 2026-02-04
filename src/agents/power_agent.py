"""
DroneForge AI - Power System Agent
Designs battery, power distribution, and BEC systems.
"""

import json
import logging
import math
from typing import Dict, Any, Optional, List
from dataclasses import asdict

logger = logging.getLogger(__name__)

POWER_AGENT_PROMPT = """You are an expert drone power systems engineer. Design the complete power system including battery selection, power distribution, and voltage regulation.

## Mission Requirements:
{mission_requirements}

## Propulsion Design:
{propulsion_design}

## Available Batteries:
{batteries_db}

## Design Requirements:
1. Flight time must meet or exceed {endurance_min} minutes
2. Battery must handle max current draw with margin
3. Voltage appropriate for selected motors
4. Weight within budget for desired T/W ratio

## Power Budget Calculation:
1. Propulsion power at hover: {hover_power_w}W
2. Propulsion power at max: {max_power_w}W
3. Electronics power budget: ~20-50W
4. Payload power: {payload_power_w}W
5. Total continuous power requirement

## Battery Sizing:
- Required energy (Wh) = (Total_power × Endurance_min / 60) / 0.8 (80% usable)
- Required capacity (mAh) = Energy (Wh) / Voltage × 1000
- Required C-rating = Max_current / Capacity (Ah)

## Output Format (JSON):
{{
    "battery_selection": {{
        "id": "battery_id",
        "brand": "...",
        "model": "...",
        "chemistry": "LiPo",
        "cell_count": 6,
        "capacity_mah": 10000,
        "c_rating": 25,
        "weight_g": 1200,
        "price": 150
    }},
    "battery_count": 1,
    "configuration": "single",
    "total_voltage_v": 22.2,
    "total_capacity_mah": 10000,
    "total_energy_wh": 222,
    "power_budget": {{
        "propulsion_hover_w": 400,
        "propulsion_max_w": 1200,
        "flight_controller_w": 3,
        "gps_w": 0.5,
        "receiver_w": 0.3,
        "telemetry_w": 2,
        "payload_w": 20,
        "total_hover_w": 426,
        "total_max_w": 1226
    }},
    "flight_time_analysis": {{
        "calculated_hover_time_min": 31.3,
        "calculated_cruise_time_min": 28.5,
        "reserve_time_min": 5,
        "usable_flight_time_min": 26.3
    }},
    "bec_requirements": [
        {{"voltage_v": 5, "current_a": 3, "purpose": "Flight controller, receiver"}},
        {{"voltage_v": 12, "current_a": 2, "purpose": "Video transmitter"}}
    ],
    "safety_features": {{
        "low_voltage_cutoff_v": 19.8,
        "low_voltage_warning_v": 21.0,
        "current_limit_a": 100
    }},
    "calculations": {{
        "step_by_step": ["...", "..."]
    }},
    "justifications": ["...", "..."],
    "total_power_weight_g": 1200,
    "total_power_cost": 150
}}
"""


class PowerAgent:
    """Agent for power system design"""
    
    # Battery chemistry properties
    BATTERY_CHEMISTRY = {
        'lipo': {
            'cell_voltage_nominal': 3.7,
            'cell_voltage_full': 4.2,
            'cell_voltage_empty': 3.3,
            'energy_density_wh_kg': 180,
            'max_discharge_c': 100,
            'cycles': 300
        },
        'lihv': {
            'cell_voltage_nominal': 3.85,
            'cell_voltage_full': 4.35,
            'cell_voltage_empty': 3.3,
            'energy_density_wh_kg': 200,
            'max_discharge_c': 80,
            'cycles': 200
        },
        'li-ion': {
            'cell_voltage_nominal': 3.6,
            'cell_voltage_full': 4.2,
            'cell_voltage_empty': 2.8,
            'energy_density_wh_kg': 250,
            'max_discharge_c': 5,
            'cycles': 500
        }
    }
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
        self.batteries_db = self._load_database("databases/batteries/battery_database.json")
    
    def _load_database(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load {path}: {e}")
            return {}
    
    def _calculate_power_budget(self, propulsion: Dict, 
                                payload_power: float = 0) -> Dict[str, float]:
        """Calculate complete power budget"""
        # Propulsion power
        hover_power = propulsion.get('calculations', {}).get('total_hover_power_w', 300)
        max_power = propulsion.get('max_power_draw_w', hover_power * 3)
        
        # Electronics power (typical values)
        fc_power = 3  # Flight controller
        gps_power = 0.5
        receiver_power = 0.3
        telemetry_power = 2
        led_power = 2
        video_tx_power = 5  # Varies greatly
        
        total_electronics = fc_power + gps_power + receiver_power + telemetry_power + led_power + video_tx_power
        
        return {
            'propulsion_hover_w': hover_power,
            'propulsion_max_w': max_power,
            'flight_controller_w': fc_power,
            'gps_w': gps_power,
            'receiver_w': receiver_power,
            'telemetry_w': telemetry_power,
            'led_w': led_power,
            'video_tx_w': video_tx_power,
            'payload_w': payload_power,
            'total_electronics_w': total_electronics + payload_power,
            'total_hover_w': hover_power + total_electronics + payload_power,
            'total_max_w': max_power + total_electronics + payload_power
        }
    
    def _calculate_required_energy(self, power_budget: Dict, 
                                   endurance_min: float) -> float:
        """
        Calculate required battery energy.
        
        Returns:
            Required energy in Wh
        """
        avg_power = power_budget['total_hover_w'] * 1.1  # 10% margin for maneuvering
        endurance_hours = endurance_min / 60
        usable_fraction = 0.8  # Only use 80% of battery
        
        required_energy = (avg_power * endurance_hours) / usable_fraction
        return required_energy
    
    def _calculate_required_capacity(self, energy_wh: float, 
                                     voltage: float) -> float:
        """
        Calculate required capacity in mAh.
        
        Args:
            energy_wh: Energy in Wh
            voltage: Nominal voltage
            
        Returns:
            Capacity in mAh
        """
        return (energy_wh / voltage) * 1000
    
    def _select_cell_count(self, motor_kv: int, prop_size_inch: float) -> int:
        """
        Select appropriate cell count based on motor KV and prop size.
        
        Returns:
            Recommended cell count (S)
        """
        # Higher KV motors need lower voltage
        # Larger props need lower KV motors with higher voltage
        
        if motor_kv > 2000:
            return 4  # 4S for high KV racing motors
        elif motor_kv > 1000:
            return 4  # 4S
        elif motor_kv > 600:
            return 6  # 6S for medium KV
        elif motor_kv > 400:
            return 6  # 6S
        elif motor_kv > 200:
            return 8  # 8S for large props
        else:
            return 12  # 12S for very large systems
    
    def _calculate_flight_time(self, capacity_mah: float, voltage: float,
                               power_budget: Dict) -> Dict[str, float]:
        """Calculate expected flight times"""
        energy_wh = (capacity_mah / 1000) * voltage
        usable_energy = energy_wh * 0.8  # 80% usable
        
        hover_power = power_budget['total_hover_w']
        cruise_power = power_budget['total_hover_w'] * 1.15  # 15% more for cruise
        max_power = power_budget['total_max_w']
        
        hover_time = (usable_energy / hover_power) * 60 if hover_power > 0 else 0
        cruise_time = (usable_energy / cruise_power) * 60 if cruise_power > 0 else 0
        max_time = (usable_energy / max_power) * 60 if max_power > 0 else 0
        
        reserve_time = 5  # 5 minute reserve
        
        return {
            'hover_time_min': round(hover_time, 1),
            'cruise_time_min': round(cruise_time, 1),
            'max_power_time_min': round(max_time, 1),
            'reserve_time_min': reserve_time,
            'usable_hover_time_min': round(hover_time - reserve_time, 1),
            'usable_cruise_time_min': round(cruise_time - reserve_time, 1)
        }
    
    def _select_battery(self, required_capacity_mah: float, 
                        cell_count: int,
                        max_current_a: float,
                        weight_budget_g: float) -> Optional[Dict]:
        """Select suitable battery from database"""
        batteries = self.batteries_db.get('batteries', [])
        
        suitable = []
        for battery in batteries:
            specs = battery.get('specs', {})
            cells = specs.get('cell_count', 0)
            capacity = specs.get('capacity_mah', 0)
            c_rating = specs.get('c_rating', 0)
            weight = specs.get('weight_g', 9999)
            
            max_discharge = (capacity / 1000) * c_rating
            
            if (cells == cell_count and
                capacity >= required_capacity_mah * 0.8 and  # Allow 20% under
                max_discharge >= max_current_a and
                weight <= weight_budget_g * 1.2):
                suitable.append(battery)
        
        if suitable:
            # Sort by capacity (closest to requirement)
            suitable.sort(key=lambda b: abs(b.get('specs', {}).get('capacity_mah', 0) - required_capacity_mah))
            return suitable[0]
        
        return None
    
    def _calculate_bec_requirements(self, has_video: bool = True,
                                    has_gimbal: bool = False,
                                    has_leds: bool = True) -> List[Dict]:
        """Calculate BEC (voltage regulator) requirements"""
        becs = []
        
        # 5V BEC for FC, GPS, receiver
        becs.append({
            'voltage_v': 5,
            'current_a': 3,
            'purpose': 'Flight controller, GPS, receiver, peripherals'
        })
        
        # 12V BEC for video TX (if needed)
        if has_video:
            becs.append({
                'voltage_v': 12,
                'current_a': 2,
                'purpose': 'Video transmitter'
            })
        
        # Gimbal power
        if has_gimbal:
            becs.append({
                'voltage_v': 12,
                'current_a': 5,
                'purpose': 'Gimbal motors'
            })
        
        return becs
    
    def design(self, requirements: Any, propulsion: Any) -> Any:
        """
        Design power system.
        
        Args:
            requirements: Mission requirements
            propulsion: Propulsion design
            
        Returns:
            PowerDesign dataclass
        """
        logger.info("Starting power system design")
        
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion_dict = asdict(propulsion)
        else:
            propulsion_dict = propulsion if isinstance(propulsion, dict) else {}
        
        endurance_min = mission_req.get('endurance_min', 20)
        payload_power = 10  # Default payload power consumption
        
        # Calculate power budget
        power_budget = self._calculate_power_budget(propulsion_dict, payload_power)
        
        # Get motor specs for cell count selection
        motors = propulsion_dict.get('motors', [{}])
        motor_kv = motors[0].get('specs', {}).get('kv', 700) if motors else 700
        props = propulsion_dict.get('propellers', [{}])
        prop_size = props[0].get('size_inch', 15) if props else 15
        
        # Select cell count
        cell_count = self._select_cell_count(motor_kv, prop_size)
        chemistry = self.BATTERY_CHEMISTRY['lipo']
        nominal_voltage = cell_count * chemistry['cell_voltage_nominal']
        
        # Calculate required energy and capacity
        required_energy = self._calculate_required_energy(power_budget, endurance_min)
        required_capacity = self._calculate_required_capacity(required_energy, nominal_voltage)
        
        # Calculate max current from propulsion
        motor_count = propulsion_dict.get('motor_count', 4)
        max_current = propulsion_dict.get('max_power_draw_w', 1000) / nominal_voltage
        
        # Weight budget for battery (typically 30-40% of AUW)
        calcs = propulsion_dict.get('calculations', {})
        if isinstance(calcs, dict):
            auw_kg = calcs.get('estimated_auw_kg', 2.0)
        else:
            auw_kg = 2.0
        battery_weight_budget = auw_kg * 1000 * 0.35
        
        # Select battery
        selected_battery = self._select_battery(
            required_capacity, cell_count, max_current, battery_weight_budget
        )
        
        if selected_battery:
            battery_specs = selected_battery.get('specs', {})
            actual_capacity = battery_specs.get('capacity_mah', required_capacity)
            actual_weight = battery_specs.get('weight_g', 500)
            battery_price = selected_battery.get('price', {}).get('usd', 100)
        else:
            # Estimate battery specs
            actual_capacity = round(required_capacity / 1000) * 1000  # Round to nearest 1000
            actual_weight = required_energy / chemistry['energy_density_wh_kg'] * 1000
            battery_price = actual_capacity * 0.015  # ~$15 per 1000mAh for quality LiPo
            
            selected_battery = {
                'id': 'estimated',
                'brand': 'Generic',
                'model': f'{cell_count}S {actual_capacity}mAh',
                'specs': {
                    'cell_count': cell_count,
                    'capacity_mah': actual_capacity,
                    'c_rating': 25,
                    'weight_g': actual_weight
                }
            }
        
        # Calculate flight times with selected battery
        flight_times = self._calculate_flight_time(
            actual_capacity, nominal_voltage, power_budget
        )
        
        # BEC requirements
        bec_reqs = self._calculate_bec_requirements()
        
        # Safety thresholds
        low_voltage_warning = cell_count * 3.5
        low_voltage_cutoff = cell_count * 3.3
        
        # Build power design result
        from ..core.state import PowerDesign
        
        result = PowerDesign(
            battery=selected_battery,
            battery_count=1,
            total_capacity_mah=actual_capacity,
            total_voltage_v=nominal_voltage,
            total_weight_g=actual_weight,
            total_energy_wh=round(actual_capacity / 1000 * nominal_voltage, 1),
            total_hover_power_w=power_budget['total_hover_w'],
            total_max_power_w=power_budget['total_max_w'],
            calculated_flight_time_min=flight_times['cruise_time_min'],
            usable_flight_time_min=flight_times['usable_cruise_time_min'],
            calculations={
                'required_energy_wh': round(required_energy, 1),
                'required_capacity_mah': round(required_capacity, 0),
                'selected_capacity_mah': actual_capacity,
                'cell_count': cell_count,
                'nominal_voltage_v': nominal_voltage,
                'max_current_a': round(max_current, 1),
                'flight_times': flight_times,
                'battery_weight_fraction': round(actual_weight / (auw_kg * 1000) * 100, 1),
                'low_voltage_warning_v': round(low_voltage_warning, 1),
                'low_voltage_cutoff_v': round(low_voltage_cutoff, 1),
                'power_budget': power_budget,
            },
            justifications=[
                f"Selected {cell_count}S configuration for motor KV {motor_kv}",
                f"Capacity {actual_capacity}mAh provides {flight_times['cruise_time_min']} min cruise time",
                f"Battery is {round(actual_weight / (auw_kg * 1000) * 100, 0)}% of AUW (target: 30-40%)",
            ]
        )
        
        logger.info("Power system design completed")
        return result
