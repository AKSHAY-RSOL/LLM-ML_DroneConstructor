"""
DroneForge AI - Optimizer Agent
Optimizes design for weight, cost, and performance.
"""

import json
import logging
import random
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class OptimizerAgent:
    """Agent for design optimization"""
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _to_dict(self, obj):
        """Convert dataclass to dict"""
        if hasattr(obj, '__dict__') and not isinstance(obj, dict):
            return asdict(obj)
        return obj if isinstance(obj, dict) else {}
    
    def _get_state_value(self, state_key, state, default=None):
        """Get value from state, converting dataclass to dict if needed"""
        value = state.get(state_key, default or {})
        return self._to_dict(value)
    
    def _calculate_performance_score(self, state: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        score = 0
        max_score = 100
        
        propulsion = self._get_state_value('propulsion_design', state, {})
        power = self._get_state_value('power_design', state, {})
        cog = self._get_state_value('cog_analysis', state, {})
        validation = self._get_state_value('validation_result', state, {})
        mission_req = self._get_state_value('mission_requirements', state, {})
        
        # Thrust-to-weight (20 points)
        tw = propulsion.get('thrust_to_weight', 0)
        if tw >= 2.5:
            score += 20
        elif tw >= 2.0:
            score += 15
        elif tw >= 1.5:
            score += 10
        
        # Flight time vs requirement (25 points)
        required_time = mission_req.get('endurance_min', 20)
        actual_time = power.get('usable_flight_time_min', 0)
        time_ratio = actual_time / required_time if required_time > 0 else 0
        if time_ratio >= 1.2:
            score += 25
        elif time_ratio >= 1.0:
            score += 20
        elif time_ratio >= 0.8:
            score += 10
        
        # CG balance (15 points)
        if cog.get('cg_within_tolerance', False):
            score += 15
        else:
            offset = cog.get('calculations', {}).get('horizontal_cg_offset_mm', 50)
            if offset < 20:
                score += 10
        
        # Validation pass (20 points)
        if validation.get('all_valid', False):
            score += 20
        else:
            issues = len(validation.get('critical_issues', []))
            score += max(0, 20 - issues * 5)
        
        # Efficiency (10 points)
        efficiency = propulsion.get('efficiency_at_hover', 0)
        if efficiency > 10:
            score += 10
        elif efficiency > 7:
            score += 7
        elif efficiency > 5:
            score += 5
        
        # Wind resistance (10 points)
        aero = self._get_state_value('aerodynamics_analysis', state, {})
        wind = aero.get('max_wind_speed_ms', 0)
        required_wind = mission_req.get('wind_resistance_ms', 8)
        if wind >= required_wind:
            score += 10
        elif wind >= required_wind * 0.8:
            score += 7
        
        return min(score, max_score)
    
    def _calculate_total_cost(self, state: Dict[str, Any]) -> float:
        """Calculate total build cost"""
        total = 0
        
        propulsion = self._get_state_value('propulsion_design', state, {})
        power = self._get_state_value('power_design', state, {})
        electronics = self._get_state_value('electronics_design', state, {})
        structural = self._get_state_value('structural_design', state, {})
        
        # Propulsion costs (BUG-037)
        motors = propulsion.get('motors', [])
        motor_count = propulsion.get('motor_count', 4)
        
        def get_price(item, default):
            if not item: return default
            if 'price_usd' in item: return item['price_usd']
            specs = item.get('specs', {})
            if 'price_usd' in specs: return specs['price_usd']
            price_obj = item.get('price', {})
            if isinstance(price_obj, dict): return price_obj.get('usd', default)
            return default

        if motors:
            total += get_price(motors[0], 30) * motor_count
        
        props = propulsion.get('propellers', [])
        if props:
            # PROP database uses pair/unit pricing. Already scaled.
            total += get_price(props[0], 5) * motor_count
        
        escs = propulsion.get('escs', [])
        if escs:
            total += get_price(escs[0], 20) * motor_count
        
        # Battery (BUG-058 / BUG-051)
        battery = power.get('battery', {})
        if battery:
            total += get_price(battery, 100)
        
        # Electronics (BUG-051 / BUG-058)
        fc = electronics.get('flight_controller', {})
        if fc:
            total += get_price(fc, 100)
        
        gps = electronics.get('gps_module', {}) or electronics.get('gps', {})
        if gps:
            total += get_price(gps, 50)
        
        receiver = electronics.get('receiver', {})
        if receiver:
            total += get_price(receiver, 30)
        
        telemetry = electronics.get('telemetry_system', {}) or electronics.get('telemetry', {})
        if telemetry:
            total += get_price(telemetry, 50)
        
        pdb = electronics.get('pdb', {})
        if pdb:
            total += get_price(pdb, 30)
        
        # Additional sensors
        sensors = electronics.get('additional_sensors', [])
        for sensor in sensors:
            total += sensor.get('price_usd', 0) * sensor.get('quantity', 1)
        
        # Companion computer
        companion = electronics.get('companion_computer')
        if companion:
            total += companion.get('price_usd', 0)
        
        # LEDs
        leds = electronics.get('led_system', {})
        total += leds.get('total_price_usd', 20)
        
        # Frame/Structural
        frame = structural.get('frame_selection')
        if frame:
            total += frame.get('price_usd', 100)
        else:
            # Custom frame estimate
            bom = structural.get('structural_bom', [])
            for item in bom:
                total += item.get('unit_price', 0) * item.get('quantity', 1)
        
        # Wiring and misc
        total += 50  # Wires, connectors, heatshrink, etc.
        
        return total
    
    def _calculate_total_weight(self, state: Dict[str, Any]) -> float:
        """Calculate total weight from all components"""
        cog = self._get_state_value('cog_analysis', state, {})
        return cog.get('all_up_weight_kg', 0)
    
    def _generate_pareto_solutions(self, state: Dict[str, Any]) -> List[Dict]:
        """Generate Pareto-optimal solutions exploring trade-offs"""
        # This is a simplified representation
        # A full implementation would use pymoo or optuna
        
        base_weight = self._calculate_total_weight(state)
        base_cost = self._calculate_total_cost(state)
        base_performance = self._calculate_performance_score(state)
        
        solutions = []
        
        # Current design
        solutions.append({
            'name': 'Current Design',
            'weight_kg': base_weight,
            'cost_usd': base_cost,
            'performance_score': base_performance,
            'changes': []
        })
        
        # Weight-optimized (lighter components, possibly lower performance)
        solutions.append({
            'name': 'Weight Optimized',
            'weight_kg': base_weight * 0.85,
            'cost_usd': base_cost * 1.2,  # Lighter components often more expensive
            'performance_score': base_performance * 0.95,
            'changes': [
                'Use carbon fiber for all structural components',
                'Select lighter motor option',
                'Use compact flight controller'
            ]
        })
        
        # Cost-optimized (cheaper components, acceptable performance)
        solutions.append({
            'name': 'Budget Optimized',
            'weight_kg': base_weight * 1.1,
            'cost_usd': base_cost * 0.7,
            'performance_score': base_performance * 0.85,
            'changes': [
                'Use G10 fiberglass instead of carbon fiber',
                'Select budget motor/ESC combos',
                'Use basic GPS module'
            ]
        })
        
        # Performance-optimized (best performance, higher cost)
        solutions.append({
            'name': 'Performance Optimized',
            'weight_kg': base_weight * 1.05,
            'cost_usd': base_cost * 1.4,
            'performance_score': min(base_performance * 1.15, 100),
            'changes': [
                'Upgrade to premium motors with higher efficiency',
                'Use high-C-rating batteries',
                'Add RTK GPS for precision'
            ]
        })
        
        return solutions
    
    def _perform_sensitivity_analysis(self, state: Dict[str, Any]) -> Dict:
        """Analyze sensitivity of performance to design parameters"""
        propulsion = self._get_state_value('propulsion_design', state, {})
        power = self._get_state_value('power_design', state, {})
        structural = self._get_state_value('structural_design', state, {})
        
        # Get motor KV safely
        motors = propulsion.get('motors', [{}])
        motor_kv = 700
        if motors and len(motors) > 0:
            motor_kv = motors[0].get('specs', {}).get('kv', 700)
        
        # Get propeller pitch safely
        props = propulsion.get('propellers', [{}])
        prop_pitch = 5
        if props and len(props) > 0:
            prop_pitch = props[0].get('pitch_inch', 5)
        
        # Get battery cell count safely
        battery = power.get('battery', {})
        cell_count = battery.get('specs', {}).get('cell_count', 6) if isinstance(battery, dict) else 6
        
        analysis = {
            'motor_kv': {
                'current_value': motor_kv,
                'impact': 'High',
                'notes': 'Lower KV = more torque, larger props; Higher KV = more RPM, smaller props'
            },
            'battery_capacity': {
                'current_value': power.get('total_capacity_mah', 5000),
                'impact': 'High',
                'notes': '+20% capacity = +15% flight time, +18% weight'
            },
            'propeller_pitch': {
                'current_value': prop_pitch,
                'impact': 'Medium',
                'notes': 'Higher pitch = more speed, more current; Lower pitch = better hover efficiency'
            },
            'frame_material': {
                'current_value': structural.get('frame_material', 'carbon_fiber'),
                'impact': 'Medium',
                'notes': 'Carbon fiber = lightest but expensive; Aluminum = heavier but cheaper'
            },
            'cell_count': {
                'current_value': cell_count,
                'impact': 'High',
                'notes': 'More cells = higher voltage, can use lower KV motors, heavier battery'
            }
        }
        
        return analysis
    
    def _get_validation_dict(self, validation: Any) -> Dict:
        """BUG-030: Safely convert validation to dict regardless of type."""
        if isinstance(validation, dict):
            return validation
        if hasattr(validation, '__dict__'):
            try:
                return asdict(validation)
            except Exception:
                return validation.__dict__
        return {}

    def _build_component_swaps(self, state: Dict[str, Any],
                               validation_dict: Dict) -> Dict[str, Any]:
        """
        BUG-015: Analyse validation failures and return concrete component swaps
        that the workflow can apply directly to propulsion/power state.
        
        Returns a dict with optional keys:
          - 'new_motor'      : replacement motor dict (same format as propulsion motors list)
          - 'new_battery'    : replacement battery dict (same format as power battery)
          - 'new_cell_count' : int — requested cell count for power agent re-run
          - 'notes'          : list of strings describing changes
        """
        swaps: Dict[str, Any] = {'notes': []}
        issues = validation_dict.get('critical_issues', []) + validation_dict.get('physics_issues', [])
        warnings = validation_dict.get('warnings', [])
        all_text = ' '.join(issues + warnings).lower()

        propulsion = self._get_state_value('propulsion_design', state, {})
        power = self._get_state_value('power_design', state, {})
        motors = propulsion.get('motors', [{}])
        current_motor = motors[0] if motors else {}
        current_tw = propulsion.get('thrust_to_weight', 0)
        auw_kg = (self._get_state_value('cog_analysis', state, {})
                  .get('all_up_weight_kg', 0) or
                  propulsion.get('calculations', {}).get('estimated_auw_kg', 2.0))

        # --- Fix 1: Low thrust-to-weight ---
        if 'thrust' in all_text and ('insufficient' in all_text or 'low' in all_text
                                     or current_tw < 1.5):
            # Load motor database and find next stronger motor
            try:
                db_root = Path(__file__).parent.parent.parent / 'databases'
                import json as _json
                with open(db_root / 'motors' / 'motor_database.json') as f:
                    motors_db = _json.load(f)
                motor_count = propulsion.get('motor_count', 4)
                # Target: achieve T/W = 2.0 at min
                required_thrust_per_motor_g = auw_kg * 9.81 * 2.0 / motor_count / 9.81 * 1000
                all_motors = sorted(
                    motors_db.get('motors', []),
                    key=lambda m: m.get('max_thrust_g', 0)
                )
                # Find lightest motor that meets requirement + 15% headroom
                for candidate in all_motors:
                    if candidate.get('max_thrust_g', 0) >= required_thrust_per_motor_g * 1.15:
                        if candidate.get('model') != current_motor.get('model'):  # Different from current
                            swaps['new_motor'] = candidate
                            swaps['notes'].append(
                                f"Motor upgraded: {current_motor.get('model','?')} → "
                                f"{candidate.get('model','?')} (thrust "
                                f"{candidate.get('max_thrust_g',0)}g/motor)"
                            )
                            break
            except Exception as e:
                logger.warning(f"Could not load motor database for swap: {e}")

        # --- Fix 2: Battery cell count mismatch ---
        if 'cell' in all_text and ('exceed' in all_text or 'mismatch' in all_text):
            motor_cells_max = current_motor.get('specs', {}).get('cell_count_max', 0)
            if motor_cells_max == 0:
                cells = current_motor.get('battery_cells') or current_motor.get('specs', {}).get('battery_cells', [])
                if cells:
                    motor_cells_max = max(cells)
            current_cells = power.get('calculations', {}).get('cell_count', 0)
            if motor_cells_max > 0 and current_cells > motor_cells_max:
                swaps['new_cell_count'] = motor_cells_max
                swaps['notes'].append(
                    f"Cell count reduced {current_cells}S → {motor_cells_max}S to match motor rating"
                )

        # --- Fix 3: Flight time too short ---
        if 'flight time' in all_text or 'endurance' in all_text:
            current_cells = power.get('calculations', {}).get('cell_count', 6)
            current_cap = power.get('total_capacity_mah', 0)
            swaps['new_battery_capacity_mah'] = int(current_cap * 1.25)  # +25%
            swaps['notes'].append(
                f"Battery capacity increased {current_cap:.0f} → {current_cap*1.25:.0f}mAh (+25%)"
            )

        return swaps

    def optimize(self, state: Dict[str, Any], requirements: Any, validation: Any) -> Any:
        """
        Optimize the design.
        
        Args:
            state: Complete workflow state
            requirements: Mission requirements
            validation: Validation result (may be dict or ValidationResult dataclass)
            
        Returns:
            OptimizationResult dataclass
        """
        logger.info("Starting design optimization")
        
        # BUG-030: Safely handle validation regardless of dict vs dataclass
        validation_dict = self._get_validation_dict(validation)
        
        # Calculate current metrics
        current_weight = self._calculate_total_weight(state)
        current_cost = self._calculate_total_cost(state)
        current_performance = self._calculate_performance_score(state)
        
        # BUG-015: Build concrete component swaps from validation failures
        component_swaps = self._build_component_swaps(state, validation_dict)
        
        # Generate Pareto solutions
        pareto_solutions = self._generate_pareto_solutions(state)
        
        # Select best solution (current design by default)
        selected_solution = pareto_solutions[0]
        
        # Sensitivity analysis
        sensitivity = self._perform_sensitivity_analysis(state)
        
        # Build optimization result
        from ..core.state import OptimizationResult
        
        power_design = state.get('power_design', {})
        if hasattr(power_design, '__dict__') and not isinstance(power_design, dict):
            power_design = asdict(power_design)
        
        all_notes = [
            f"Current design scores {current_performance:.0f}/100",
            f"Total estimated cost: ${current_cost:.0f}",
            f"All-up weight: {current_weight:.2f}kg",
            "See Pareto solutions for alternative trade-offs"
        ] + component_swaps.get('notes', [])
        
        result = OptimizationResult(
            optimized_weight_kg=current_weight,
            optimized_cost=current_cost,
            optimized_endurance_min=power_design.get('usable_flight_time_min', 0),
            optimized_performance_score=current_performance,
            pareto_solutions=pareto_solutions,
            selected_solution=selected_solution,
            sensitivity_analysis=sensitivity,
            optimization_notes=all_notes
        )
        
        # Attach component_swaps so workflow can apply them back to state (BUG-015)
        result.component_swaps = component_swaps
        
        logger.info("Design optimization completed")
        return result
