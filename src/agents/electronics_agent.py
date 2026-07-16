"""
DroneForge AI - Electronics Agent
Selects flight controller, GPS, receivers, telemetry, and sensors.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import asdict

logger = logging.getLogger(__name__)


class ElectronicsAgent:
    """Agent for electronics selection"""
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
        from pathlib import Path
        db_root = Path(__file__).parent.parent.parent / "databases"
        self.fc_db = self._load_database(db_root / "flight_controllers" / "flight_controller_database.json")
        self.gps_db = self._load_database(db_root / "gps" / "gps_database.json")
        self.comm_db = self._load_database(db_root / "communication" / "communication_database.json")
    
    def _load_database(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load {path}: {e}")
            return {}
    
    def _select_flight_controller(self, requirements: Dict) -> Optional[Dict]:
        """Select appropriate flight controller based on requirements"""
        fcs = self.fc_db.get('flight_controllers', [])
        
        needs_autonomy = requirements.get('waypoint_navigation', False)
        motor_count = self._get_motor_count(requirements.get('configuration', 'quadcopter_x'))
        budget = requirements.get('max_cost', 100000)
        
        suitable = []
        for fc in fcs:
            specs = fc.get('specs', {})
            
            # Check motor outputs (BUG-042: specs.pwm_outputs is the database key)
            motor_outputs = specs.get('pwm_outputs', 0)
            if motor_outputs < motor_count:
                continue
            
            # Check autonomy support (BUG-042: fc.firmware is the database key)
            firmware = fc.get('firmware', [])
            if needs_autonomy and not any(f in firmware for f in ['ArduPilot', 'PX4']):
                continue
            
            # Check price (BUG-042: fc.price_usd is the database key)
            price = fc.get('price_usd', 9999)
            if price > budget * 0.05:  # FC should be <5% of budget
                continue
            
            suitable.append(fc)
        
        if suitable:
            # Sort by capability score
            def score_fc(fc):
                specs = fc.get('specs', {})
                score = 0
                score += specs.get('pwm_outputs', 0) * 2
                score += specs.get('uart_ports', 0) * 5
                score += 20 if 'ArduPilot' in fc.get('firmware', []) else 0
                score += 20 if 'PX4' in fc.get('firmware', []) else 0
                score -= fc.get('price_usd', 0) / 10
                return score
            
            suitable.sort(key=score_fc, reverse=True)
            return suitable[0]
        
        # Fallback
        return {
            'id': 'pixhawk_6x',
            'brand': 'Holybro',
            'model': 'Pixhawk 6X',
            'specs': {
                'processor': 'STM32H753',
                'imu': 'ICM-42688-P',
                'motor_outputs': 16,
                'uarts': 8
            },
            'firmware_support': ['ArduPilot', 'PX4'],
            'price': {'usd': 399}
        }
    
    def _select_gps(self, requirements: Dict) -> Optional[Dict]:
        """Select GPS module based on requirements"""
        gps_modules = self.gps_db.get('gps_modules', [])
        
        needs_rtk = requirements.get('precision_landing', False) or requirements.get('survey', False)
        budget = requirements.get('max_cost', 100000)
        
        suitable = []
        for gps in gps_modules:
            specs = gps.get('specs', {})
            price = gps.get('price_usd', 9999)
            
            if needs_rtk and not specs.get('rtk_capable', False):
                continue
            
            if price > budget * 0.02:
                continue
            
            suitable.append(gps)
        
        if suitable:
            # Sort by accuracy
            suitable.sort(key=lambda g: g.get('specs', {}).get('accuracy_m', 99))
            return suitable[0]
        
        # Fallback
        return {
            'id': 'holybro_m10',
            'brand': 'Holybro',
            'model': 'M10 GPS',
            'specs': {
                'chipset': 'u-blox M10',
                'accuracy_m': 1.5,
                'update_rate_hz': 25
            },
            'price_usd': 65
        }
    
    def _select_receiver(self, requirements: Dict) -> Dict:
        """Select RC receiver"""
        receivers = self.comm_db.get('receivers', [])
        
        range_km = requirements.get('range_km', 5)
        beyond_vlos = requirements.get('beyond_vlos', False)
        
        suitable = []
        for rx in receivers:
            specs = rx.get('specs', {})
            rx_range = specs.get('range_km', 0)
            
            if rx_range >= range_km:
                suitable.append(rx)
        
        if suitable:
            # Sort by range and latency
            suitable.sort(key=lambda r: (r.get('specs', {}).get('range_km', 0), 
                                         -r.get('specs', {}).get('latency_ms', 99)))
            return suitable[-1]  # Highest range
        
        # Fallback to ExpressLRS
        return {
            'id': 'expresslrs_nano',
            'brand': 'Various',
            'model': 'ExpressLRS 2.4GHz',
            'protocol': 'ExpressLRS',
            'specs': {
                'frequency_mhz': 2400,
                'range_km': 30,
                'latency_ms': 2
            },
            'price_usd': 18
        }
    
    def _select_telemetry(self, requirements: Dict) -> Dict:
        """Select telemetry system"""
        telemetry = self.comm_db.get('telemetry_modules', [])
        
        range_km = requirements.get('range_km', 5)
        
        for telem in telemetry:
            specs = telem.get('specs', {})
            if specs.get('range_km', 0) >= range_km:
                return telem
        
        # Fallback
        return {
            'id': 'holybro_sik_v3',
            'brand': 'Holybro',
            'model': 'SiK Telemetry V3',
            'specs': {
                'frequency_mhz': 915,
                'range_km': 5,
                'data_rate_kbps': 250
            },
            'price_usd': 65
        }
    
    def _select_companion_computer(self, requirements: Dict) -> Optional[Dict]:
        """Select companion computer for autonomy if needed"""
        needs_autonomy = requirements.get('obstacle_avoidance', False)
        needs_ai = requirements.get('ai_features', False)
        
        if not (needs_autonomy or needs_ai):
            return None
        
        # Options
        if needs_ai:
            return {
                'id': 'jetson_orin_nano',
                'brand': 'NVIDIA',
                'model': 'Jetson Orin Nano',
                'specs': {
                    'cpu': '6-core ARM Cortex-A78',
                    'gpu': 'Ampere GPU with 1024 CUDA cores',
                    'memory_gb': 8,
                    'power_w': 15,
                    'weight_g': 75
                },
                'price_usd': 499
            }
        else:
            return {
                'id': 'raspberry_pi_5',
                'brand': 'Raspberry Pi',
                'model': 'Raspberry Pi 5',
                'specs': {
                    'cpu': 'Quad-core Cortex-A76 2.4GHz',
                    'memory_gb': 8,
                    'power_w': 8,
                    'weight_g': 50
                },
                'price_usd': 80
            }
    
    def _get_motor_count(self, config: str) -> int:
        """Get motor count from configuration"""
        counts = {
            'tricopter': 3,
            'quadcopter_x': 4, 'quadcopter_plus': 4, 'quadcopter_h': 4,
            'hexacopter_x': 6, 'hexacopter_plus': 6,
            'octocopter_x': 8, 'octocopter_plus': 8, 'octocopter_coax': 8,
        }
        return counts.get(config, 4)
    
    def _select_additional_sensors(self, requirements: Dict) -> List[Dict]:
        """Select additional sensors based on requirements"""
        sensors = []
        
        if requirements.get('obstacle_avoidance', False):
            sensors.append({
                'id': 'benewake_tf02_pro',
                'type': 'lidar',
                'brand': 'Benewake',
                'model': 'TF02-Pro',
                'specs': {
                    'range_m': 40,
                    'accuracy_cm': 1,
                    'fov_deg': 3
                },
                'quantity': 1,
                'price_usd': 80
            })
        
        if requirements.get('precision_landing', False):
            sensors.append({
                'id': 'optical_flow',
                'type': 'optical_flow',
                'brand': 'Holybro',
                'model': 'PM07 Optical Flow',
                'specs': {
                    'resolution': '72x72',
                    'interface': 'I2C'
                },
                'quantity': 1,
                'price_usd': 45
            })
        
        if requirements.get('max_altitude_m', 0) > 500:
            sensors.append({
                'id': 'airspeed',
                'type': 'airspeed',
                'brand': 'Holybro',
                'model': 'Digital Airspeed Sensor',
                'specs': {
                    'range_ms': 75,
                    'accuracy_percent': 2
                },
                'quantity': 1,
                'price_usd': 35
            })
        
        # Altimeter for all drones
        sensors.append({
            'id': 'barometer',
            'type': 'barometer',
            'brand': 'Various',
            'model': 'BMP390 (included in FC)',
            'specs': {
                'accuracy_m': 0.5
            },
            'quantity': 1,
            'price_usd': 0  # Included in FC
        })
        
        return sensors
    
    def _design_led_system(self, requirements: Dict) -> Dict:
        """Design LED system for visibility and orientation"""
        drone_type = requirements.get('drone_type', 'multirotor')
        
        return {
            'front_leds': {
                'color': 'white',
                'type': 'high_brightness',
                'purpose': 'Forward indication and night visibility'
            },
            'rear_leds': {
                'color': 'red',
                'type': 'high_brightness',
                'purpose': 'Rear indication'
            },
            'arm_leds': {
                'color': 'rgb',
                'type': 'ws2812b',
                'purpose': 'Orientation and status indication',
                'quantity': 4
            },
            'strobe': {
                'type': 'anti_collision',
                'color': 'white',
                'purpose': 'FAA/EASA anti-collision requirement'
            },
            'total_power_w': 5,
            'total_price_usd': 25
        }
    
    def _select_pdb(self, max_current: float) -> Dict:
        """Select power distribution board"""
        if max_current < 60:
            return {
                'id': 'matek_pdb_xt60',
                'brand': 'Matek',
                'model': 'PDB-XT60',
                'specs': {
                    'max_current_a': 120,
                    'bec_5v_a': 2,
                    'bec_12v_a': 0.5
                },
                'price_usd': 12
            }
        elif max_current < 120:
            return {
                'id': 'holybro_pm07',
                'brand': 'Holybro',
                'model': 'PM07',
                'specs': {
                    'max_current_a': 120,
                    'current_sensor': True,
                    'bec_5v_a': 3
                },
                'price_usd': 45
            }
        else:
            return {
                'id': 'matek_pdb_12s',
                'brand': 'Matek',
                'model': 'PDB for Large Drones',
                'specs': {
                    'max_current_a': 300,
                    'current_sensor': True
                },
                'price_usd': 65
            }
    
    def select(self, requirements: Any, propulsion: Any, power: Any) -> Any:
        """
        Design electronics system.
        
        Args:
            requirements: Mission requirements
            propulsion: Propulsion design
            power: Power design
            
        Returns:
            ElectronicsDesign dataclass
        """
        logger.info("Starting electronics design")
        
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion_dict = asdict(propulsion)
        else:
            propulsion_dict = propulsion if isinstance(propulsion, dict) else {}
            
        if hasattr(power, '__dict__') and not isinstance(power, dict):
            power_dict = asdict(power)
        else:
            power_dict = power if isinstance(power, dict) else {}
        
        # Select components
        fc = self._select_flight_controller(mission_req)
        gps = self._select_gps(mission_req)
        receiver = self._select_receiver(mission_req)
        telemetry = self._select_telemetry(mission_req)
        companion = self._select_companion_computer(mission_req)
        sensors = self._select_additional_sensors(mission_req)
        leds = self._design_led_system(mission_req)
        
        # Get max current for PDB selection
        calcs = power_dict.get('calculations', {})
        if isinstance(calcs, dict):
            max_current = calcs.get('max_current_a', 50)
        else:
            max_current = 50
        motor_count = propulsion_dict.get('motor_count', 4)
        pdb = self._select_pdb(max_current)
        
        # Calculate total weight and cost
        total_weight = 0
        total_cost = 0
        
        components = [
            (fc, 'flight_controller'),
            (gps, 'gps'),
            (receiver, 'receiver'),
            (telemetry, 'telemetry'),
            (pdb, 'pdb')
        ]
        
        for comp, name in components:
            if comp:
                weight = comp.get('specs', {}).get('weight_g', 30)
                # BUG-051: Check properly if 'price' contains nested 'usd', or use 'price_usd' flat key
                price = 50
                if 'price' in comp and isinstance(comp['price'], dict):
                    price = comp['price'].get('usd', 50)
                elif 'price_usd' in comp:
                    price = comp['price_usd']
                total_weight += weight
                total_cost += price
        
        if companion:
            total_weight += companion.get('specs', {}).get('weight_g', 50)
            total_cost += companion.get('price_usd', 0)
        
        for sensor in sensors:
            total_weight += sensor.get('specs', {}).get('weight_g', 10)
            total_cost += sensor.get('price_usd', 0) * sensor.get('quantity', 1)
        
        total_cost += leds.get('total_price_usd', 0)
        
        # Determine recommended transmitter
        protocol = receiver.get('protocol', 'ExpressLRS')
        if protocol == 'ExpressLRS':
            transmitter_rec = 'RadioMaster TX16S or Boxer with ELRS module'
        elif protocol == 'TBS Crossfire':
            transmitter_rec = 'Any radio with TBS Crossfire TX module'
        elif 'FrSky' in protocol:
            transmitter_rec = 'FrSky Taranis or Horus series'
        else:
            transmitter_rec = 'Compatible transmitter with matching protocol'
        
        # Build electronics design result
        from ..core.state import ElectronicsDesign
        
        result = ElectronicsDesign(
            flight_controller=fc,
            gps_module=gps,
            receiver=receiver,
            telemetry_system=telemetry,
            additional_sensors=sensors,
            total_electronics_weight_g=total_weight,
            calculations={
                'total_electronics_weight_g': total_weight,
                'total_electronics_cost_usd': total_cost,
                'power_consumption_estimate_w': 15 + (10 if companion else 0),
                'transmitter_recommendation': transmitter_rec,
                'companion_computer': companion,
                'led_system': leds,
                'pdb': pdb,
            },
            justifications=[
                f"Selected {fc.get('brand')} {fc.get('model')} for {motor_count} motor outputs and autonomy support",
                f"GPS {gps.get('model')} provides {gps.get('specs', {}).get('accuracy_m', 2)}m accuracy",
                f"Receiver protocol: {protocol} for {receiver.get('specs', {}).get('range_km', 0)}km range",
                f"Total electronics weight: {total_weight}g"
            ]
        )
        
        logger.info("Electronics design completed")
        return result
