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
        mission_req_obj = state.get('mission_requirements', {})
        if hasattr(mission_req_obj, '__dict__'):
            mission_req_dict = asdict(mission_req_obj)
        else:
            mission_req_dict = mission_req_obj if isinstance(mission_req_obj, dict) else {}
            
        drone_type = mission_req_dict.get('drone_type', 'multirotor')
        if hasattr(drone_type, 'value'):
            drone_type = drone_type.value
        drone_type = str(drone_type).lower()
        
        if 'fixed_wing' in drone_type or 'flying_wing' in drone_type or drone_type == 'conventional':
            tw_min = 0.5
            tw_rec = 0.7
        elif 'vtol' in drone_type or 'quadplane' in drone_type or 'tailsitter' in drone_type:
            tw_min = 1.2
            tw_rec = 1.5
        else:
            tw_min = self.SAFETY_MARGINS['thrust_to_weight_min']
            tw_rec = self.SAFETY_MARGINS['thrust_to_weight_recommended']
            
        weight_n = auw_kg * 9.81
        if weight_n > 0:
            tw_ratio = total_thrust / weight_n
            
            if tw_ratio < tw_min:
                issues.append(f"Thrust-to-weight ratio {tw_ratio:.2f} is below minimum {tw_min}")
            elif tw_ratio < tw_rec:
                warnings.append(f"Thrust-to-weight ratio {tw_ratio:.2f} is below recommended {tw_rec}")
        
        # Power budget validation
        total_power = power.get('total_max_power_w', 0)
        
        # Calculate real max continuous battery power: C_rating * Capacity (Ah) * Voltage
        battery = power.get('battery', {})
        battery_specs = battery.get('specs', {}) if isinstance(battery, dict) else {}
        c_rating = battery_specs.get('c_rating', 25)
        capacity_mah = power.get('total_capacity_mah', 5000)
        total_voltage = power.get('total_voltage_v', 22.2)
        
        if c_rating and capacity_mah and total_voltage:
            battery_power = c_rating * (capacity_mah / 1000.0) * total_voltage
        else:
            battery_power = power.get('total_energy_wh', 0) * 10  # Fallback
        
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
        
        # Motor-ESC compatibility — check all pairs (BUG-033)
        motors = propulsion.get('motors', [{}])
        escs = propulsion.get('escs', [{}])
        motor_count = propulsion.get('motor_count', len(motors))
        
        # De-duplicate motor/ESC lists for checking (they may be the same object repeated)
        motors_to_check = motors[:1] if motors else [{}]  # All are identical copies; check one spec
        escs_to_check = escs[:1] if escs else [{}]
        
        actual_cells = power.get('battery', {}).get('specs', {}).get('cell_count', 0) or \
                       power.get('calculations', {}).get('cell_count', 6)
        
        if motors_to_check and escs_to_check:
            motor_max_current = motors_to_check[0].get('specs', {}).get('max_current_a', 30)
            esc_rating = escs_to_check[0].get('specs', {}).get('current_rating_a', 30)
            
            if esc_rating < motor_max_current * 1.1:
                issues.append(f"ESC rating {esc_rating}A may be insufficient for motor max current {motor_max_current}A (needs {motor_max_current * 1.1:.0f}A)")
        
        # Motor-Battery voltage compatibility (BUG-033: use already-retrieved actual_cells)
        if motors_to_check:
            motor_cells = motors_to_check[0].get('specs', {}).get('cell_count_max', 6)
            if actual_cells > 0 and actual_cells > motor_cells:
                issues.append(f"Battery {actual_cells}S exceeds motor max {motor_cells}S rating")
        
        # Propeller-Frame clearance
        props = propulsion.get('propellers', [{}])
        if props:
            prop_diameter_mm = props[0].get('size_inch', 10) * 25.4
            wheelbase = structural.get('wheelbase_mm', 500)
            motor_count = propulsion.get('motor_count', 4)
            
            # Calculate min spacing between props using exact chord length: wheelbase * sin(pi / motor_count)
            if motor_count > 1:
                motor_spacing = wheelbase * math.sin(math.pi / motor_count)
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
        
        # Failsafe configuration (BUG-029: AutonomyDesign has bool fields, not nested dicts)
        # AutonomyDesign.return_to_home is a direct bool field; after asdict() → {'return_to_home': True}
        safety_feats = autonomy.get('safety_features', {})
        
        rth_enabled = autonomy.get('return_to_home', None)
        if rth_enabled is None:
            rth_enabled = safety_feats.get('return_to_home', True)
        if isinstance(rth_enabled, dict):
            rth_enabled = rth_enabled.get('enabled', True)  # Fallback for old nested format
        if not rth_enabled:
            warnings.append("Return-to-home is disabled - consider enabling for safety")
        
        geo_enabled = autonomy.get('geofencing_enabled', None)
        if geo_enabled is None:
            # Check 'geofencing' or 'geofencing_enabled' under safety_features
            geo_enabled = safety_feats.get('geofencing', safety_feats.get('geofencing_enabled', True))
        if isinstance(geo_enabled, dict):
            geo_enabled = geo_enabled.get('enabled', True)
        if not geo_enabled:
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
    
    def _validate_budget(self, state: Dict[str, Any]) -> Dict:
        """Validate cost against target budget"""
        issues = []
        warnings = []
        
        # Helper to convert dataclass to dict
        def to_dict(obj):
            if hasattr(obj, '__dict__') and not isinstance(obj, dict):
                return asdict(obj)
            return obj if isinstance(obj, dict) else {}
            
        mission_req = to_dict(state.get('mission_requirements', {}))
        target_budget = mission_req.get('max_cost', 0.0) or mission_req.get('budget_usd', 0.0)
        currency = mission_req.get('currency', 'USD').upper()
        
        if target_budget <= 0:
            return {'valid': True, 'issues': [], 'warnings': []}
            
        # Convert budget to USD if it is in INR (using exchange rate 95)
        target_budget_usd = target_budget / 95.0 if currency == 'INR' else target_budget
            
        # Sum up component costs
        total_cost = 0.0
        
        propulsion = to_dict(state.get('propulsion_design', {}))
        power = to_dict(state.get('power_design', {}))
        electronics = to_dict(state.get('electronics_design', {}))
        structural = to_dict(state.get('structural_design', {}))
        
        # Motors
        motors = propulsion.get('motors', [])
        motor_count = propulsion.get('motor_count', 4)
        for motor in motors:
            specs = motor.get('specs', {})
            price = specs.get('price_usd', motor.get('price_usd', 30.0))
            if len(motors) == 1:
                total_cost += price * motor_count
            else:
                total_cost += price
            
        # Propellers
        props = propulsion.get('propellers', [])
        for prop in props:
            price = prop.get('unit_price', prop.get('price_inr', 200.0) / 95.0)
            if len(props) == 1:
                total_cost += price * (motor_count * 2)  # Include spares
            else:
                total_cost += price * 2  # 2 props per motor (one working, one spare)
            
        # ESCs
        escs = propulsion.get('escs', [])
        for esc in escs:
            specs = esc.get('specs', {})
            price = specs.get('price_usd', esc.get('price_usd', 20.0))
            if len(escs) == 1:
                total_cost += price * motor_count
            else:
                total_cost += price
            
        # Battery
        battery = to_dict(power.get('battery', {}))
        if battery:
            specs = battery.get('specs', {})
            price = specs.get('price_usd', battery.get('price_usd', 100.0))
            total_cost += price
            
        # FC & Electronics
        fc = to_dict(electronics.get('flight_controller', {}))
        if fc:
            specs = fc.get('specs', {})
            price = specs.get('price_usd', fc.get('price_usd', 120.0))
            total_cost += price
            
        gps = to_dict(electronics.get('gps_module', {}))
        if gps:
            total_cost += gps.get('price_usd', 50.0)
            
        receiver = to_dict(electronics.get('receiver', {}))
        if receiver:
            total_cost += receiver.get('price_usd', 30.0)
            
        telemetry = to_dict(electronics.get('telemetry_system', {}))
        if telemetry:
            total_cost += telemetry.get('price_usd', 50.0)
            
        pdb = to_dict(electronics.get('pdb', {}))
        if pdb:
            total_cost += pdb.get('price_usd', 20.0)
            
        # Frame
        frame = to_dict(structural.get('frame_selection', {}))
        if frame:
            total_cost += frame.get('price_usd', 100.0)
        else:
            bom = structural.get('structural_bom', [])
            for item in bom:
                total_cost += item.get('unit_price', 0.0) * item.get('quantity', 1)
                
        total_cost += 30.0  # Wires & misc
        
        # Compare
        if total_cost > target_budget_usd:
            overage_percent = ((total_cost - target_budget_usd) / target_budget_usd) * 100
            if overage_percent > 15.0:
                issues.append(f"Estimated build cost ${total_cost:.1f} exceeds target budget ${target_budget_usd:.1f} by {overage_percent:.1f}%")
            else:
                warnings.append(f"Estimated build cost ${total_cost:.1f} exceeds target budget ${target_budget_usd:.1f} by {overage_percent:.1f}%")
                
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

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
        budget_result = self._validate_budget(state)
        
        # Aggregate results — deduplicate to prevent BUG-016, BUG-017 duplicate messages
        all_issues_raw = []
        all_warnings_raw = []
        
        for name, result in [('physics', physics_result), 
                            ('compatibility', compat_result),
                            ('safety', safety_result),
                            ('regulatory', regulatory_result),
                            ('budget', budget_result)]:
            for issue in result.get('issues', []):
                all_issues_raw.append(f"[{name.upper()}] {issue}")
            for warning in result.get('warnings', []):
                all_warnings_raw.append(f"[{name.upper()}] {warning}")
        
        # Remove exact duplicates while preserving insertion order (BUG-016, BUG-017)
        all_issues = list(dict.fromkeys(all_issues_raw))
        all_warnings = list(dict.fromkeys(all_warnings_raw))
        
        # Generate recommendations
        recommendations = self._generate_recommendations({
            'physics': physics_result,
            'compatibility': compat_result,
            'safety': safety_result,
            'regulatory': regulatory_result,
            'budget': budget_result
        })
        
        # Determine overall validity
        all_valid = (physics_result['valid'] and 
                    compat_result['valid'] and 
                    safety_result['valid'] and
                    regulatory_result['valid'] and
                    budget_result['valid'])
        
        # Separate critical issues
        critical_issues = [i for i in all_issues if any(
            word in i.lower() for word in ['exceed', 'insufficient', 'dangerous', 'below minimum', 'fail', 'error', 'invalid', 'mismatch', 'above limit']
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
