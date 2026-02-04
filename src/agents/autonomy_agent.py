"""
DroneForge AI - Autonomy Agent
Designs autonomous flight capabilities and navigation systems.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class AutonomyAgent:
    """Agent for autonomous flight system design"""
    
    # Supported mission types by firmware
    FIRMWARE_CAPABILITIES = {
        'ArduPilot': {
            'waypoint_navigation': True,
            'max_waypoints': 500,
            'rth': True,
            'geofencing': True,
            'terrain_following': True,
            'precision_landing': True,
            'object_avoidance': True,
            'follow_me': True,
            'orbit': True,
            'survey_grid': True
        },
        'PX4': {
            'waypoint_navigation': True,
            'max_waypoints': 200,
            'rth': True,
            'geofencing': True,
            'terrain_following': True,
            'precision_landing': True,
            'object_avoidance': True,
            'follow_me': True,
            'orbit': True,
            'survey_grid': True
        },
        'Betaflight': {
            'waypoint_navigation': False,
            'max_waypoints': 0,
            'rth': True,
            'geofencing': False,
            'terrain_following': False,
            'precision_landing': False,
            'object_avoidance': False,
            'follow_me': False,
            'orbit': False,
            'survey_grid': False
        },
        'INAV': {
            'waypoint_navigation': True,
            'max_waypoints': 120,
            'rth': True,
            'geofencing': True,
            'terrain_following': False,
            'precision_landing': False,
            'object_avoidance': False,
            'follow_me': False,
            'orbit': True,
            'survey_grid': False
        }
    }
    
    # Ground control software
    GROUND_STATIONS = {
        'ArduPilot': ['Mission Planner', 'QGroundControl', 'APM Planner 2'],
        'PX4': ['QGroundControl', 'MAVSDK'],
        'INAV': ['INAV Configurator', 'Mwp', 'Ezgui'],
        'Betaflight': ['Betaflight Configurator']
    }
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _select_firmware(self, requirements: Dict, electronics: Dict) -> str:
        """Select appropriate firmware based on requirements"""
        needs_waypoints = requirements.get('waypoint_navigation', False)
        needs_obstacle = requirements.get('obstacle_avoidance', False)
        needs_survey = 'survey' in requirements.get('use_case', '').lower()
        
        fc = electronics.get('flight_controller', {})
        supported_firmware = fc.get('firmware_support', ['ArduPilot', 'PX4'])
        
        if needs_waypoints or needs_obstacle or needs_survey:
            if 'ArduPilot' in supported_firmware:
                return 'ArduPilot'
            elif 'PX4' in supported_firmware:
                return 'PX4'
            elif 'INAV' in supported_firmware:
                return 'INAV'
        
        # For simple builds
        if 'Betaflight' in supported_firmware:
            return 'Betaflight'
        
        return 'ArduPilot'  # Default
    
    def _design_navigation_system(self, requirements: Dict, 
                                  electronics: Dict) -> Dict:
        """Design navigation system"""
        gps = electronics.get('gps_module', {})
        gps_specs = gps.get('specs', {})
        
        nav_type = 'GPS'
        if gps_specs.get('rtk_capable', False):
            nav_type = 'RTK-GPS'
        
        # Check for additional nav sensors
        sensors = electronics.get('additional_sensors', [])
        has_optical_flow = any(s.get('type') == 'optical_flow' for s in sensors)
        has_lidar = any(s.get('type') == 'lidar' for s in sensors)
        
        if has_optical_flow:
            nav_type += ' + Optical Flow'
        
        return {
            'primary_navigation': nav_type,
            'gps_accuracy_m': gps_specs.get('accuracy_m', 2.5),
            'update_rate_hz': gps_specs.get('update_rate_hz', 10),
            'has_optical_flow': has_optical_flow,
            'has_lidar': has_lidar,
            'indoor_capable': has_optical_flow
        }
    
    def _design_obstacle_avoidance(self, requirements: Dict,
                                   electronics: Dict) -> Dict:
        """Design obstacle avoidance system"""
        if not requirements.get('obstacle_avoidance', False):
            return {
                'enabled': False,
                'type': 'None',
                'sensors': []
            }
        
        sensors = electronics.get('additional_sensors', [])
        lidar_sensors = [s for s in sensors if s.get('type') == 'lidar']
        
        companion = electronics.get('companion_computer')
        
        if companion and 'Jetson' in companion.get('brand', ''):
            avoidance_type = 'AI-based with depth perception'
        elif lidar_sensors:
            avoidance_type = 'LiDAR-based'
        else:
            avoidance_type = 'Ultrasonic'
        
        return {
            'enabled': True,
            'type': avoidance_type,
            'sensors': lidar_sensors,
            'min_distance_m': 2.0,
            'reaction_time_ms': 100,
            'coverage': {
                'forward': True,
                'backward': bool(len(lidar_sensors) > 1),
                'left': bool(len(lidar_sensors) > 2),
                'right': bool(len(lidar_sensors) > 2),
                'down': any(s.get('type') == 'optical_flow' for s in sensors),
                'up': False
            }
        }
    
    def _design_safety_features(self, requirements: Dict, 
                                power: Dict) -> Dict:
        """Design safety features"""
        low_batt_warning = power.get('safety_thresholds', {}).get('low_voltage_warning_v', 21)
        low_batt_cutoff = power.get('safety_thresholds', {}).get('low_voltage_cutoff_v', 19.8)
        
        total_voltage = power.get('total_voltage_v', 22.2)
        
        # Calculate percentage thresholds
        warning_percent = 25  # Typical
        critical_percent = 15
        
        return {
            'return_to_home': {
                'enabled': requirements.get('return_to_home', True),
                'altitude_m': 50,  # Default RTH altitude
                'speed_ms': 10
            },
            'low_battery': {
                'warning_percent': warning_percent,
                'warning_voltage_v': round(low_batt_warning, 1),
                'rth_percent': 20,
                'land_percent': critical_percent,
                'action': 'RTH'
            },
            'signal_loss': {
                'behavior': 'RTH',
                'timeout_s': 3,
                'hover_time_s': 10
            },
            'geofencing': {
                'enabled': requirements.get('geofencing', True),
                'max_distance_m': requirements.get('range_km', 5) * 1000 * 0.8,
                'max_altitude_m': requirements.get('max_altitude_m', 120),
                'action': 'RTH'
            },
            'failsafe_modes': [
                {'trigger': 'low_battery', 'action': 'RTH'},
                {'trigger': 'signal_loss', 'action': 'RTH'},
                {'trigger': 'gps_loss', 'action': 'Land'},
                {'trigger': 'geofence_breach', 'action': 'Stop and hover'}
            ]
        }
    
    def _get_supported_missions(self, firmware: str, 
                                requirements: Dict) -> List[str]:
        """Get list of supported mission types"""
        capabilities = self.FIRMWARE_CAPABILITIES.get(firmware, {})
        missions = []
        
        if capabilities.get('waypoint_navigation'):
            missions.append('Waypoint Navigation')
        
        if capabilities.get('survey_grid'):
            missions.append('Survey/Mapping Grid')
        
        if capabilities.get('orbit'):
            missions.append('Point of Interest Orbit')
        
        if capabilities.get('follow_me'):
            missions.append('Follow Me')
        
        if capabilities.get('terrain_following'):
            missions.append('Terrain Following')
        
        if capabilities.get('precision_landing'):
            missions.append('Precision Landing')
        
        # Always available
        missions.extend(['Manual Flight', 'Stabilized Flight', 'Position Hold'])
        
        return missions
    
    def design(self, requirements: Any, electronics: Any) -> Any:
        """
        Design autonomy system.
        
        Args:
            requirements: Mission requirements
            electronics: Electronics design
            
        Returns:
            AutonomyDesign dataclass
        """
        logger.info("Starting autonomy system design")
        
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(electronics, '__dict__') and not isinstance(electronics, dict):
            electronics_dict = asdict(electronics)
        else:
            electronics_dict = electronics if isinstance(electronics, dict) else {}
        
        # Select firmware
        firmware = self._select_firmware(mission_req, electronics_dict)
        capabilities = self.FIRMWARE_CAPABILITIES.get(firmware, {})
        
        # Design navigation
        navigation = self._design_navigation_system(mission_req, electronics_dict)
        
        # Design obstacle avoidance
        obstacle_avoidance = self._design_obstacle_avoidance(mission_req, electronics_dict)
        
        # Design safety features
        safety = self._design_safety_features(mission_req, {})
        
        # Get supported missions
        missions = self._get_supported_missions(firmware, mission_req)
        
        # Ground station recommendation
        ground_stations = self.GROUND_STATIONS.get(firmware, ['QGroundControl'])
        
        # Build autonomy design
        from ..core.state import AutonomyDesign
        
        result = AutonomyDesign(
            navigation_system=navigation['primary_navigation'],
            waypoint_capability=capabilities.get('waypoint_navigation', False),
            max_waypoints=capabilities.get('max_waypoints', 0),
            obstacle_avoidance_type=obstacle_avoidance['type'],
            obstacle_sensors=obstacle_avoidance['sensors'],
            return_to_home=safety['return_to_home']['enabled'],
            rth_altitude_m=safety['return_to_home']['altitude_m'],
            low_battery_rth_percent=safety['low_battery']['rth_percent'],
            geofencing_enabled=safety['geofencing']['enabled'],
            supported_missions=missions,
            calculations={
                'firmware': firmware,
                'ground_station_software': ground_stations[0],
                'all_ground_stations': ground_stations,
                'firmware_capabilities': capabilities,
                'navigation_details': navigation,
                'obstacle_avoidance_details': obstacle_avoidance,
                'safety_features': safety,
            },
            justifications=[
                f"Selected {firmware} for comprehensive autonomy support",
                f"Navigation: {navigation['primary_navigation']} with {navigation['gps_accuracy_m']}m accuracy",
                f"Obstacle avoidance: {obstacle_avoidance['type']}",
                f"Supports {len(missions)} mission types",
                f"Recommended ground station: {ground_stations[0]}"
            ]
        )
        
        logger.info("Autonomy system design completed")
        return result
