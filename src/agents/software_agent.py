"""
DroneForge AI - Software Configuration Agent
Configures firmware settings, PID values, flight modes, and failsafes.
"""

import json
import logging
from typing import Dict, Any, List
from dataclasses import asdict

logger = logging.getLogger(__name__)


class SoftwareAgent:
    """Agent for software and firmware configuration"""
    
    # Default PID values by frame type
    DEFAULT_PIDS = {
        'quadcopter_x': {
            'roll': {'P': 4.5, 'I': 0.045, 'D': 0.036},
            'pitch': {'P': 4.5, 'I': 0.045, 'D': 0.036},
            'yaw': {'P': 4.0, 'I': 0.040, 'D': 0.0}
        },
        'hexacopter_x': {
            'roll': {'P': 4.0, 'I': 0.040, 'D': 0.030},
            'pitch': {'P': 4.0, 'I': 0.040, 'D': 0.030},
            'yaw': {'P': 3.5, 'I': 0.035, 'D': 0.0}
        },
        'octocopter_x': {
            'roll': {'P': 3.5, 'I': 0.035, 'D': 0.025},
            'pitch': {'P': 3.5, 'I': 0.035, 'D': 0.025},
            'yaw': {'P': 3.0, 'I': 0.030, 'D': 0.0}
        }
    }
    
    # Flight modes by firmware
    FLIGHT_MODES = {
        'ArduPilot': {
            'basic': ['STABILIZE', 'ALT_HOLD', 'LOITER', 'RTL', 'LAND', 'POSHOLD'],
            'advanced': ['AUTO', 'GUIDED', 'CIRCLE', 'FOLLOW', 'BRAKE', 'SMART_RTL'],
            'acro': ['ACRO', 'SPORT']
        },
        'PX4': {
            'basic': ['Manual', 'Stabilized', 'Altitude', 'Position', 'Return', 'Land'],
            'advanced': ['Mission', 'Hold', 'Orbit', 'Follow Me'],
            'acro': ['Acro', 'Rattitude']
        },
        'Betaflight': {
            'basic': ['ANGLE', 'HORIZON', 'ACRO'],
            'advanced': ['LAUNCH', 'GPS RESCUE'],
            'acro': ['ACRO', '3D']
        },
        'INAV': {
            'basic': ['ANGLE', 'HORIZON', 'NAV POSHOLD', 'NAV RTH', 'NAV ALTHOLD'],
            'advanced': ['NAV WP', 'NAV CRUISE', 'NAV COURSE HOLD'],
            'acro': ['ACRO', 'MANUAL']
        }
    }
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _calculate_pids(self, config: str, auw_kg: float, 
                       moi: Dict[str, float]) -> Dict:
        """Calculate PID values based on physical properties"""
        # Start with defaults
        base_pids = self.DEFAULT_PIDS.get(config, self.DEFAULT_PIDS['quadcopter_x'])
        
        # Scale based on weight (heavier = lower P, higher I)
        weight_factor = 2.0 / auw_kg if auw_kg > 0 else 1.0
        weight_factor = max(0.5, min(2.0, weight_factor))  # Clamp
        
        # Scale based on moment of inertia
        ixx = moi.get('ixx_kg_m2', 0.01)
        iyy = moi.get('iyy_kg_m2', 0.01)
        izz = moi.get('izz_kg_m2', 0.02)
        
        # Larger MOI = lower gains needed
        moi_factor = 0.01 / max(ixx, 0.001)
        moi_factor = max(0.3, min(3.0, moi_factor))
        
        scaled_pids = {}
        for axis, values in base_pids.items():
            factor = weight_factor * moi_factor if axis != 'yaw' else 1.0
            scaled_pids[axis] = {
                'P': round(values['P'] * factor, 2),
                'I': round(values['I'] * factor, 3),
                'D': round(values['D'] * factor, 3)
            }
        
        return scaled_pids
    
    def _configure_rates(self, use_case: str) -> Dict:
        """Configure rate settings based on use case"""
        if 'racing' in use_case.lower() or 'acrobatic' in use_case.lower():
            return {
                'roll_rate_dps': 800,
                'pitch_rate_dps': 800,
                'yaw_rate_dps': 600,
                'expo': 0.3
            }
        elif 'photography' in use_case.lower() or 'cinema' in use_case.lower():
            return {
                'roll_rate_dps': 180,
                'pitch_rate_dps': 180,
                'yaw_rate_dps': 120,
                'expo': 0.7
            }
        else:
            return {
                'roll_rate_dps': 360,
                'pitch_rate_dps': 360,
                'yaw_rate_dps': 200,
                'expo': 0.5
            }
    
    def _configure_filters(self, motor_count: int) -> Dict:
        """Configure filter settings"""
        return {
            'gyro_lowpass_hz': 100,
            'gyro_lowpass2_hz': 200,
            'dterm_lowpass_hz': 80,
            'notch_filter_enabled': True,
            'dynamic_notch': {
                'enabled': True,
                'min_hz': 80,
                'max_hz': 400,
                'count': motor_count
            }
        }
    
    def _select_flight_modes(self, firmware: str, requirements: Dict) -> List[Dict]:
        """Select appropriate flight modes"""
        modes = self.FLIGHT_MODES.get(firmware, self.FLIGHT_MODES['ArduPilot'])
        
        selected = []
        
        # Always include basic modes
        for mode in modes['basic']:
            selected.append({
                'name': mode,
                'switch_position': len(selected) + 1,
                'description': f'{mode} mode'
            })
        
        # Add advanced if waypoint navigation needed
        if requirements.get('waypoint_navigation', False):
            for mode in modes['advanced'][:3]:  # First 3 advanced modes
                if len(selected) < 6:
                    selected.append({
                        'name': mode,
                        'switch_position': len(selected) + 1,
                        'description': f'{mode} mode'
                    })
        
        return selected[:6]  # Max 6 modes for most radios
    
    def _configure_failsafes(self, autonomy: Dict, power: Dict) -> Dict:
        """Configure failsafe settings"""
        return {
            'battery': {
                'low_voltage_warning': power.get('safety_thresholds', {}).get('low_voltage_warning_v', 21),
                'low_voltage_action': 'RTH',
                'critical_voltage_action': 'LAND'
            },
            'radio': {
                'failsafe_throttle': 975,
                'timeout_ms': 1000,
                'action': autonomy.get('signal_loss_behavior', 'RTH')
            },
            'gps': {
                'min_satellites': 6,
                'hdop_threshold': 2.0,
                'loss_action': 'LAND'
            },
            'geofence': {
                'enabled': autonomy.get('geofencing_enabled', True),
                'max_altitude_m': 120,
                'max_distance_m': 2000,
                'action': 'RTH'
            }
        }
    
    def _generate_config_file(self, firmware: str, config_data: Dict) -> str:
        """Generate configuration file content"""
        if firmware == 'ArduPilot':
            return self._generate_ardupilot_params(config_data)
        elif firmware == 'PX4':
            return self._generate_px4_params(config_data)
        elif firmware == 'Betaflight':
            return self._generate_betaflight_cli(config_data)
        else:
            return json.dumps(config_data, indent=2)
    
    def _generate_ardupilot_params(self, config: Dict) -> str:
        """Generate ArduPilot parameter file"""
        params = []
        
        pids = config.get('pids', {})
        params.append(f"ATC_RAT_RLL_P,{pids.get('roll', {}).get('P', 4.5)}")
        params.append(f"ATC_RAT_RLL_I,{pids.get('roll', {}).get('I', 0.045)}")
        params.append(f"ATC_RAT_RLL_D,{pids.get('roll', {}).get('D', 0.036)}")
        params.append(f"ATC_RAT_PIT_P,{pids.get('pitch', {}).get('P', 4.5)}")
        params.append(f"ATC_RAT_PIT_I,{pids.get('pitch', {}).get('I', 0.045)}")
        params.append(f"ATC_RAT_PIT_D,{pids.get('pitch', {}).get('D', 0.036)}")
        params.append(f"ATC_RAT_YAW_P,{pids.get('yaw', {}).get('P', 4.0)}")
        params.append(f"ATC_RAT_YAW_I,{pids.get('yaw', {}).get('I', 0.040)}")
        
        # Failsafes
        failsafe = config.get('failsafe', {})
        params.append(f"FS_THR_ENABLE,1")
        params.append(f"FS_THR_VALUE,{failsafe.get('radio', {}).get('failsafe_throttle', 975)}")
        params.append(f"RTL_ALT,{config.get('rth_altitude', 50) * 100}")  # cm
        
        # Battery
        battery = failsafe.get('battery', {})
        params.append(f"BATT_LOW_VOLT,{battery.get('low_voltage_warning', 21)}")
        
        return '\n'.join(params)
    
    def _generate_px4_params(self, config: Dict) -> str:
        """Generate PX4 parameter file"""
        params = []
        
        pids = config.get('pids', {})
        params.append(f"MC_ROLLRATE_P {pids.get('roll', {}).get('P', 0.15)}")
        params.append(f"MC_ROLLRATE_I {pids.get('roll', {}).get('I', 0.1)}")
        params.append(f"MC_ROLLRATE_D {pids.get('roll', {}).get('D', 0.003)}")
        params.append(f"MC_PITCHRATE_P {pids.get('pitch', {}).get('P', 0.15)}")
        params.append(f"MC_PITCHRATE_I {pids.get('pitch', {}).get('I', 0.1)}")
        params.append(f"MC_PITCHRATE_D {pids.get('pitch', {}).get('D', 0.003)}")
        
        return '\n'.join(params)
    
    def _generate_betaflight_cli(self, config: Dict) -> str:
        """Generate Betaflight CLI commands"""
        commands = ['# DroneForge AI Generated Config', '']
        
        pids = config.get('pids', {})
        commands.append(f"set p_roll = {int(pids.get('roll', {}).get('P', 45) * 10)}")
        commands.append(f"set i_roll = {int(pids.get('roll', {}).get('I', 0.045) * 1000)}")
        commands.append(f"set d_roll = {int(pids.get('roll', {}).get('D', 0.036) * 1000)}")
        commands.append(f"set p_pitch = {int(pids.get('pitch', {}).get('P', 45) * 10)}")
        commands.append(f"set i_pitch = {int(pids.get('pitch', {}).get('I', 0.045) * 1000)}")
        commands.append(f"set d_pitch = {int(pids.get('pitch', {}).get('D', 0.036) * 1000)}")
        
        rates = config.get('rates', {})
        commands.append(f"set roll_rate = {rates.get('roll_rate_dps', 360)}")
        commands.append(f"set pitch_rate = {rates.get('pitch_rate_dps', 360)}")
        commands.append(f"set yaw_rate = {rates.get('yaw_rate_dps', 200)}")
        
        commands.append('')
        commands.append('save')
        
        return '\n'.join(commands)
    
    def configure(self, requirements: Any, electronics: Any, propulsion: Any, autonomy: Any, cog: Any) -> Any:
        """
        Configure software settings.
        
        Args:
            requirements: Mission requirements
            electronics: Electronics design
            propulsion: Propulsion design
            autonomy: Autonomy design
            cog: Center of gravity analysis
            
        Returns:
            SoftwareConfig dataclass
        """
        logger.info("Starting software configuration")
        
        # Convert dataclasses to dicts
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion = asdict(propulsion)
        else:
            propulsion = propulsion if isinstance(propulsion, dict) else {}
            
        if hasattr(cog, '__dict__') and not isinstance(cog, dict):
            cog = asdict(cog)
        else:
            cog = cog if isinstance(cog, dict) else {}
            
        if hasattr(autonomy, '__dict__') and not isinstance(autonomy, dict):
            autonomy = asdict(autonomy)
        else:
            autonomy = autonomy if isinstance(autonomy, dict) else {}
        
        config = mission_req.get('configuration', 'quadcopter_x')
        use_case = mission_req.get('use_case', '')
        auw_kg = cog.get('all_up_weight_kg', 2.0) if isinstance(cog, dict) else 2.0
        motor_count = propulsion.get('motor_count', 4) if isinstance(propulsion, dict) else 4
        firmware = autonomy.get('firmware', 'ArduPilot') if isinstance(autonomy, dict) else 'ArduPilot'
        
        # Get moments of inertia
        moi = {
            'ixx_kg_m2': cog.get('ixx_kg_m2', 0.01),
            'iyy_kg_m2': cog.get('iyy_kg_m2', 0.01),
            'izz_kg_m2': cog.get('izz_kg_m2', 0.02)
        }
        
        # Calculate configurations
        pids = self._calculate_pids(config, auw_kg, moi)
        rates = self._configure_rates(use_case)
        filters = self._configure_filters(motor_count)
        flight_modes = self._select_flight_modes(firmware, mission_req)
        failsafes = self._configure_failsafes(autonomy, {})
        
        # Generate config files
        config_data = {
            'pids': pids,
            'rates': rates,
            'filters': filters,
            'flight_modes': flight_modes,
            'failsafe': failsafes,
            'rth_altitude': autonomy.get('rth_altitude_m', 50)
        }
        
        config_content = self._generate_config_file(firmware, config_data)
        
        # Build software config result
        from ..core.state import SoftwareConfig
        
        result = SoftwareConfig(
            firmware_type=firmware,
            firmware_version='latest_stable',
            pid_values=pids,
            rates=rates,
            filters=filters,
            flight_modes=flight_modes,
            failsafe_config=failsafes,
            config_files={f'{firmware.lower()}_config': config_content},
            justifications=[
                f"Firmware: {firmware} selected for autonomy requirements",
                f"PIDs scaled for {auw_kg:.1f}kg AUW",
                f"Rates configured for {use_case or 'general'} use case",
                f"{len(flight_modes)} flight modes configured",
                "Failsafes configured for safe operation"
            ]
        )
        
        logger.info("Software configuration completed")
        return result
