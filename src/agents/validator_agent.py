"""
DroneForge AI - Validation Agent
Validates design physics, compatibility, and safety.
"""

import json
import logging
import math
from typing import Dict, Any, List
from dataclasses import asdict

logger = logging.getLogger(__name__)


class ValidatorAgent:
    """Agent for design validation"""
    
    # Safety margins
    SAFETY_MARGINS = {
        'thrust_to_weight_min': 1.5,
        'thrust_to_weight_recommended': 2.0,
        'battery_c_rating_margin': 1.2,
        'structural_safety_factor': 2.0,
        'max_motor_temp_c': 80,
        'max_esc_temp_c': 85,
    }
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _validate_physics(self, state: Dict[str, Any]) -> Dict:
        """Validate physics calculations"""
        issues = []
        warnings = []
        
        # Helper to convert dataclass to dict
        def to_dict(obj):
            if hasattr(obj, '__dict__') and not isinstance(obj, dict):
                return asdict(obj)
            return obj if isinstance(obj, dict) else {}
        
        propulsion = to_dict(state.get('propulsion_design', {}))
        power = to_dict(state.get('power_design', {}))
        cog = to_dict(state.get('cog_analysis', {}))
        aero = to_dict(state.get('aerodynamics_analysis', {}))
        
        auw_kg = cog.get('all_up_weight_kg', 0)
        
        # Thrust to weight validation
        total_thrust = propulsion.get('total_thrust_n', 0)
        weight_n = auw_kg * 9.81
        
        if weight_n > 0:
            tw_ratio = total_thrust / weight_n
            
            if tw_ratio < self.SAFETY_MARGINS['thrust_to_weight_min']:
                issues.append(f"Thrust-to-weight ratio {tw_ratio:.2f} is below minimum {self.SAFETY_MARGINS['thrust_to_weight_min']}")
            elif tw_ratio < self.SAFETY_MARGINS['thrust_to_weight_recommended']:
                warnings.append(f"Thrust-to-weight ratio {tw_ratio:.2f} is below recommended {self.SAFETY_MARGINS['thrust_to_weight_recommended']}")
        
        # Power budget validation
        total_power = power.get('total_max_power_w', 0)
        battery_power = power.get('total_energy_wh', 0) * 10  # Rough max power estimate
        
        if total_power > battery_power * 0.9:
            issues.append(f"Power draw {total_power:.0f}W may exceed battery capability")
        
        # Flight time validation
        mission_req = state.get('mission_requirements', {})
        if hasattr(mission_req, '__dict__'):
            mission_req = asdict(mission_req)
        
        required_endurance = mission_req.get('endurance_min', 20)
        calculated_endurance = power.get('usable_flight_time_min', 0)
        
        if calculated_endurance < required_endurance:
            issues.append(f"Calculated flight time {calculated_endurance:.1f}min is less than required {required_endurance}min")
        elif calculated_endurance < required_endurance * 1.1:
            warnings.append(f"Flight time {calculated_endurance:.1f}min has minimal margin over required {required_endurance}min")
        
        # Drag vs thrust validation
        drag_at_cruise = aero.get('drag_force_at_cruise_n', 0)
        available_horizontal_thrust = total_thrust * 0.3  # ~30% for forward flight
        
        if drag_at_cruise > available_horizontal_thrust * 0.8:
            warnings.append(f"Cruise drag {drag_at_cruise:.1f}N is high relative to available thrust")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def _validate_compatibility(self, state: Dict[str, Any]) -> Dict:
        """Validate component compatibility"""
        issues = []
        warnings = []
        
        # Helper to convert dataclass to dict
        def to_dict(obj):
            if hasattr(obj, '__dict__') and not isinstance(obj, dict):
                return asdict(obj)
            return obj if isinstance(obj, dict) else {}
        
        propulsion = to_dict(state.get('propulsion_design', {}))
        power = to_dict(state.get('power_design', {}))
        electronics = to_dict(state.get('electronics_design', {}))
        structural = to_dict(state.get('structural_design', {}))
        
        # Motor-ESC compatibility
        motors = propulsion.get('motors', [{}])
        escs = propulsion.get('escs', [{}])
        
        if motors and escs:
            motor_max_current = motors[0].get('specs', {}).get('max_current_a', 30)
            esc_rating = escs[0].get('specs', {}).get('current_rating_a', 30)
            
            if esc_rating < motor_max_current * 1.1:
                issues.append(f"ESC rating {esc_rating}A may be insufficient for motor max {motor_max_current}A")
        
        # Motor-Battery voltage compatibility
        if motors:
            motor_kv = motors[0].get('specs', {}).get('kv', 700)
            battery_voltage = power.get('total_voltage_v', 22.2)
            
            # Check if motor can handle voltage
            motor_cells = motors[0].get('specs', {}).get('cell_count_max', 6)
            actual_cells = power.get('battery', {}).get('specs', {}).get('cell_count', 6)
            
            if actual_cells > motor_cells:
                issues.append(f"Battery {actual_cells}S exceeds motor max {motor_cells}S rating")
        
        # Propeller-Frame clearance
        props = propulsion.get('propellers', [{}])
        if props:
            prop_diameter_mm = props[0].get('size_inch', 10) * 25.4
            wheelbase = structural.get('wheelbase_mm', 500)
            motor_count = propulsion.get('motor_count', 4)
            
            # Calculate min spacing between props
            if motor_count == 4:
                motor_spacing = wheelbase / math.sqrt(2)
            else:
                motor_spacing = wheelbase * math.pi / motor_count
            
            clearance = motor_spacing - prop_diameter_mm
            
            if clearance < 10:
                issues.append(f"Propeller clearance {clearance:.0f}mm is dangerously low")
            elif clearance < 20:
                warnings.append(f"Propeller clearance {clearance:.0f}mm is tight")
        
        # FC-Motor output compatibility
        fc = electronics.get('flight_controller', {})
        motor_count = propulsion.get('motor_count', 4)
        fc_outputs = fc.get('specs', {}).get('motor_outputs', 8)
        
        if fc_outputs < motor_count:
            issues.append(f"Flight controller has {fc_outputs} outputs but need {motor_count} motors")
        
        # Protocol compatibility
        receiver = electronics.get('receiver', {})
        rx_protocol = receiver.get('protocol', '')
        
        # Check if FC supports protocol
        fc_protocols = fc.get('specs', {}).get('rc_protocols', ['SBUS', 'CRSF', 'PPM'])
        if rx_protocol and rx_protocol not in str(fc_protocols):
            warnings.append(f"Verify FC supports {rx_protocol} protocol")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def _validate_safety(self, state: Dict[str, Any]) -> Dict:
        """Validate safety margins"""
        issues = []
        warnings = []
        
        # Helper to convert dataclass to dict
        def to_dict(obj):
            if hasattr(obj, '__dict__') and not isinstance(obj, dict):
                return asdict(obj)
            return obj if isinstance(obj, dict) else {}
        
        structural = to_dict(state.get('structural_design', {}))
        power = to_dict(state.get('power_design', {}))
        autonomy = to_dict(state.get('autonomy_design', {}))
        cog = to_dict(state.get('cog_analysis', {}))
        
        # Structural safety factor
        safety_factor = structural.get('safety_factor', 0)
        if safety_factor < self.SAFETY_MARGINS['structural_safety_factor']:
            issues.append(f"Structural safety factor {safety_factor:.1f} is below minimum 2.0")
        elif safety_factor < 2.5:
            warnings.append(f"Structural safety factor {safety_factor:.1f} provides minimal margin")
        
        # CG position
        if not cog.get('cg_within_tolerance', True):
            warnings.append(f"CG is outside recommended tolerance of {cog.get('cg_tolerance_mm', 10)}mm")
        
        # Battery safety
        battery = power.get('battery', {})
        battery_c = battery.get('specs', {}).get('c_rating', 25)
        max_current = power.get('calculations', {}).get('max_current_a', 50)
        capacity_ah = power.get('total_capacity_mah', 5000) / 1000
        
        actual_c = max_current / capacity_ah if capacity_ah > 0 else 0
        
        if actual_c > battery_c:
            issues.append(f"Max current draw {max_current:.0f}A exceeds battery C-rating ({battery_c}C = {battery_c * capacity_ah:.0f}A)")
        elif actual_c > battery_c * 0.8:
            warnings.append(f"Max current {max_current:.0f}A is near battery limit ({battery_c * capacity_ah:.0f}A)")
        
        # Failsafe configuration
        if not autonomy.get('return_to_home', True):
            warnings.append("Return-to-home is disabled - consider enabling for safety")
        
        if not autonomy.get('geofencing_enabled', True):
            warnings.append("Geofencing is disabled - consider enabling for safety")
        
        # Low battery threshold
        low_batt_percent = power.get('safety_thresholds', {}).get('low_voltage_warning_v', 0)
        if low_batt_percent == 0:
            warnings.append("No low battery warning configured")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def _validate_regulatory(self, state: Dict[str, Any]) -> Dict:
        """Validate regulatory compliance"""
        issues = []
        warnings = []
        
        # Helper to convert dataclass to dict
        def to_dict(obj):
            if hasattr(obj, '__dict__') and not isinstance(obj, dict):
                return asdict(obj)
            return obj if isinstance(obj, dict) else {}
        
        regulatory = to_dict(state.get('regulatory_compliance', {}))
        
        if not regulatory.get('fully_compliant', True):
            compliance_status = regulatory.get('compliance_status', {})
            for jurisdiction, status in compliance_status.items():
                if not status.get('compliant', True):
                    for issue in status.get('issues', []):
                        issues.append(f"[{jurisdiction}] {issue}")
        
        # Check required equipment
        equipment = regulatory.get('equipment_required', [])
        for item in equipment:
            if item.get('status') == 'required':
                warnings.append(f"Required equipment: {item.get('item')} for {item.get('jurisdictions')}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def _generate_recommendations(self, validation_results: Dict) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Physics recommendations
        physics = validation_results.get('physics', {})
        if not physics.get('valid', True):
            recommendations.append("Consider increasing motor size or reducing weight")
            recommendations.append("Review battery selection for adequate capacity")
        
        # Compatibility recommendations
        compat = validation_results.get('compatibility', {})
        if not compat.get('valid', True):
            recommendations.append("Review component specifications for compatibility")
        
        # Safety recommendations
        safety = validation_results.get('safety', {})
        if safety.get('warnings'):
            recommendations.append("Review safety margins and increase where possible")
            recommendations.append("Ensure all failsafes are configured properly")
        
        # General recommendations
        recommendations.append("Perform a bench test before first flight")
        recommendations.append("Start with low throttle in a safe area")
        recommendations.append("Verify motor directions and propeller orientation")
        
        return recommendations
    
    def validate(self, state: Dict[str, Any]) -> Any:
        """
        Validate the complete design.
        
        Args:
            state: Complete workflow state dict
            
        Returns:
            ValidationResult dataclass
        """
        logger.info("Starting design validation")
        
        # Run all validations
        physics_result = self._validate_physics(state)
        compat_result = self._validate_compatibility(state)
        safety_result = self._validate_safety(state)
        regulatory_result = self._validate_regulatory(state)
        
        # Aggregate results
        all_issues = []
        all_warnings = []
        
        for name, result in [('physics', physics_result), 
                            ('compatibility', compat_result),
                            ('safety', safety_result),
                            ('regulatory', regulatory_result)]:
            for issue in result.get('issues', []):
                all_issues.append(f"[{name.upper()}] {issue}")
            for warning in result.get('warnings', []):
                all_warnings.append(f"[{name.upper()}] {warning}")
        
        # Generate recommendations
        recommendations = self._generate_recommendations({
            'physics': physics_result,
            'compatibility': compat_result,
            'safety': safety_result,
            'regulatory': regulatory_result
        })
        
        # Determine overall validity
        all_valid = (physics_result['valid'] and 
                    compat_result['valid'] and 
                    safety_result['valid'])
        
        # Separate critical issues
        critical_issues = [i for i in all_issues if any(
            word in i.lower() for word in ['exceed', 'insufficient', 'dangerous', 'below minimum']
        )]
        
        # Build validation result
        from ..core.state import ValidationResult
        
        result = ValidationResult(
            physics_valid=physics_result['valid'],
            physics_issues=physics_result.get('issues', []),
            compatibility_valid=compat_result['valid'],
            compatibility_issues=compat_result.get('issues', []),
            safety_valid=safety_result['valid'],
            safety_issues=safety_result.get('issues', []),
            regulatory_valid=regulatory_result['valid'],
            regulatory_issues=regulatory_result.get('issues', []),
            all_valid=all_valid,
            critical_issues=critical_issues,
            warnings=all_warnings,
            recommendations=recommendations
        )
        
        if all_valid:
            logger.info("Design validation passed")
        else:
            logger.warning(f"Design validation failed with {len(all_issues)} issues")
        
        return result
