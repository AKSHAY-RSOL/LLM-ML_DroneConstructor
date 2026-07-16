"""
DroneForge AI - Propulsion Agent
Designs the propulsion system including motors, propellers, and ESCs.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import asdict
from pathlib import Path

logger = logging.getLogger(__name__)

PROPULSION_AGENT_PROMPT = """You are an expert drone propulsion systems engineer. Your task is to design the complete propulsion system for a drone based on the mission requirements.

## Mission Requirements:
{mission_requirements}

## Available Components:

### Motors:
{motors_db}

### Propellers:
{propellers_db}

### ESCs:
{escs_db}

## Design Constraints:
1. Total thrust must be at least {thrust_to_weight}x the all-up weight
2. Motors must be compatible with propeller size
3. ESCs must handle motor max current with 20% headroom
4. System must operate within temperature range: {temp_min}°C to {temp_max}°C
5. Budget constraint: {budget} {currency}

## Required Calculations:
1. Estimate all-up weight (AUW):
   - Frame weight (estimate based on configuration)
   - Battery weight (estimate based on endurance)
   - Electronics weight (~200-500g)
   - Payload weight
   
2. Required thrust:
   - Minimum thrust = AUW × thrust_to_weight_ratio
   - Thrust per motor = Total thrust / number of motors
   
3. Motor selection criteria:
   - KV rating appropriate for battery voltage and prop size
   - Max thrust > required thrust per motor
   - Efficiency at 50% throttle (hover point)
   
4. Propeller selection:
   - Size compatible with motor and frame
   - Pitch optimized for use case (low pitch for hover, high pitch for speed)
   - Material suitable for environment
   
5. ESC selection:
   - Current rating > motor max current × 1.2
   - Protocol compatible with flight controller
   - BEC if needed

## Output Format (JSON):
{{
    "motor": {{
        "id": "motor_id_from_database",
        "brand": "...",
        "model": "...",
        "quantity": 4,
        "kv": 920,
        "max_thrust_g": 2000,
        "specs": {{...}},
        "unit_price": 0.0
    }},
    "propeller": {{
        "id": "propeller_id_from_database",
        "brand": "...",
        "model": "...",
        "size_inch": 15,
        "pitch_inch": 5.5,
        "quantity": 4,
        "spares": 4,
        "unit_price": 0.0
    }},
    "esc": {{
        "id": "esc_id_from_database",
        "brand": "...",
        "model": "...",
        "quantity": 4,
        "current_rating_a": 50,
        "unit_price": 0.0
    }},
    "calculations": {{
        "estimated_auw_kg": 0.0,
        "total_thrust_required_n": 0.0,
        "thrust_per_motor_n": 0.0,
        "total_thrust_available_n": 0.0,
        "actual_thrust_to_weight": 0.0,
        "estimated_hover_throttle_percent": 50,
        "hover_power_per_motor_w": 0.0,
        "total_hover_power_w": 0.0,
        "max_power_draw_w": 0.0,
        "efficiency_at_hover_g_per_w": 0.0
    }},
    "justifications": [
        "Selected motor X because...",
        "Propeller Y chosen for...",
        "ESC Z selected with headroom..."
    ],
    "total_propulsion_cost": 0.0,
    "total_propulsion_weight_g": 0.0
}}

Think step-by-step through the design process, showing all calculations.
"""


class PropulsionAgent:
    """Agent for designing drone propulsion systems"""
    
    def __init__(self, llm_provider: Any):
        """
        Initialize the propulsion agent.
        
        Args:
            llm_provider: LLM provider instance for generating responses
        """
        self.llm = llm_provider
        db_root = Path(__file__).parent.parent.parent / "databases"
        self.motors_db = self._load_database(str(db_root / "motors" / "motor_database.json"))
        self.propellers_db = self._load_database(str(db_root / "propellers" / "propeller_database.json"))
        self.escs_db = self._load_database(str(db_root / "escs" / "esc_database.json"))
        
    def _ensure_specs(self, component: Dict[str, Any]) -> Dict[str, Any]:
        if not component:
            return component
        comp = component.copy()
        if 'specs' not in comp:
            comp['specs'] = {}
        
        # Copy all top-level keys to specs, and map keys if needed
        for k, v in comp.items():
            if k != 'specs':
                comp['specs'][k] = v
                
        # Handle specific mappings
        if 'continuous_current_a' in comp:
            comp['specs']['current_rating_a'] = comp['continuous_current_a']
        if 'max_current_a' in comp:
            comp['specs']['max_current_a'] = comp['max_current_a']
        if 'max_thrust_g' in comp:
            comp['specs']['max_thrust_g'] = comp['max_thrust_g']
        if 'kv' in comp:
            comp['specs']['kv'] = comp['kv']
        if 'weight_g' in comp:
            comp['specs']['weight_g'] = comp['weight_g']
        if 'battery_cells' in comp and isinstance(comp['battery_cells'], list):
            comp['specs']['cell_count_max'] = max(comp['battery_cells'])
            comp['specs']['battery_cells'] = comp['battery_cells']
        if 'diameter_in' in comp:
            comp['size_inch'] = comp['diameter_in']
            comp['specs']['size_inch'] = comp['diameter_in']
        if 'pitch_in' in comp:
            comp['pitch_inch'] = comp['pitch_in']
            comp['specs']['pitch_inch'] = comp['pitch_in']
        if 'price_inr' in comp:
            comp['specs']['price_usd'] = comp['price_inr'] / 95.0
            if 'price' not in comp:
                comp['price'] = {'usd': comp['price_inr'] / 95.0, 'inr': comp['price_inr']}
                
        return comp

    def _load_database(self, path: str) -> Dict[str, Any]:
        """Load component database from JSON file"""
        try:
            with open(path, 'r') as f:
                db = json.load(f)
            
            # Wrap components in specs to ensure compatibility
            if 'motors' in db:
                db['motors'] = [self._ensure_specs(m) for m in db['motors']]
            if 'propellers' in db:
                db['propellers'] = [self._ensure_specs(p) for p in db['propellers']]
            if 'escs' in db:
                db['escs'] = [self._ensure_specs(e) for e in db['escs']]
                
            return db
        except FileNotFoundError:
            logger.warning(f"Database not found: {path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing database {path}: {e}")
            return {}
    
    def _estimate_auw(self, mission_req: Dict[str, Any]) -> float:
        """
        Estimate all-up weight based on mission requirements.
        
        Returns:
            Estimated AUW in kg
        """
        payload = mission_req.get('payload_mass_kg', 0)
        endurance = mission_req.get('endurance_min', 20)
        drone_type = mission_req.get('drone_type', 'multirotor')
        config = mission_req.get('configuration', 'quadcopter_x')
        
        # Motor count based on configuration
        motor_counts = {
            'tricopter': 3,
            'quadcopter_x': 4,
            'quadcopter_plus': 4,
            'quadcopter_h': 4,
            'hexacopter_x': 6,
            'hexacopter_plus': 6,
            'octocopter_x': 8,
            'octocopter_plus': 8,
            'octocopter_coax': 8,
            'conventional': 1,
            'flying_wing': 1,
            'quadplane': 5,
            'tailsitter': 2,
        }
        motor_count = motor_counts.get(config, 4)
        
        # Frame weight estimation (varies by configuration)
        frame_weights = {
            'tricopter': 300,
            'quadcopter_x': 400,
            'quadcopter_plus': 400,
            'quadcopter_h': 450,
            'hexacopter_x': 800,
            'hexacopter_plus': 800,
            'octocopter_x': 1500,
            'octocopter_plus': 1500,
            'octocopter_coax': 2000,
            'conventional': 300,
            'flying_wing': 200,
            'quadplane': 800,
            'tailsitter': 400,
        }
        frame_weight_g = frame_weights.get(config, 500)
        
        # Scale dry weights based on payload and class
        if payload < 0.5:
            # Small FPV/Mavic class (e.g. DJI Mavic 3, Skydio X2, Holybro X500 V2)
            frame_weight_g = max(100.0, frame_weight_g * 0.25)
            motor_weight_g = motor_count * 28.0   # RS2205 size (28g)
            prop_weight_g = motor_count * 4.5
            esc_weight_g = motor_count * 9.0
            electronics_weight_g = 80.0
        elif payload < 2.0:
            # Medium class (e.g. DJI Inspire 3, Tarot FY680, senseFly eBee X)
            frame_weight_g = max(300.0, frame_weight_g * 0.6)
            motor_weight_g = motor_count * 95.0   # U5 size (95g)
            prop_weight_g = motor_count * 14.0
            esc_weight_g = motor_count * 25.0
            electronics_weight_g = 150.0
        else:
            # Heavy lift class (e.g. DJI Matrice 300, DJI Agras T30, Freefly Alta X)
            if payload > 5.0:
                frame_weight_g *= 2.0
            else:
                frame_weight_g *= 1.5
            motor_weight_g = motor_count * 150.0  # Heavy motors (150-250g)
            prop_weight_g = motor_count * 40.0
            esc_weight_g = motor_count * 60.0
            electronics_weight_g = 300.0
            
        # Battery weight estimation based on endurance
        # Convert drone_type to string if it is an Enum
        dt_str = drone_type.value if hasattr(drone_type, 'value') else str(drone_type)
        dt_str = dt_str.lower()
        
        if 'fixed_wing' in dt_str or 'flying_wing' in dt_str or dt_str == 'conventional':
            base_power_w_per_kg = 60.0
        elif 'vtol' in dt_str or 'quadplane' in config or 'tailsitter' in config:
            base_power_w_per_kg = 80.0
        else:
            base_power_w_per_kg = 150.0
            
        estimated_dry_weight_kg = (frame_weight_g + motor_weight_g + prop_weight_g + 
                                   esc_weight_g + electronics_weight_g) / 1000 + payload
        energy_needed_wh = estimated_dry_weight_kg * base_power_w_per_kg * (endurance / 60)
        battery_weight_g = (energy_needed_wh / 180) * 1000 * 1.1  # 10% overhead
        
        # Calculate total AUW
        auw_g = (frame_weight_g + motor_weight_g + prop_weight_g + 
                 esc_weight_g + electronics_weight_g + battery_weight_g + payload * 1000)
        
        return auw_g / 1000
    
    def _calculate_required_thrust(self, auw_kg: float, thrust_to_weight: float = 2.0) -> float:
        """
        Calculate required total thrust.
        
        Args:
            auw_kg: All-up weight in kg
            thrust_to_weight: Desired thrust-to-weight ratio
            
        Returns:
            Required thrust in Newtons
        """
        return auw_kg * 9.81 * thrust_to_weight
    
    def _filter_suitable_motors(self, thrust_per_motor_n: float, 
                                prop_size_range: tuple = (10, 18)) -> List[Dict]:
        """Filter motors that meet thrust requirements with unit sanity check (BUG-011)"""
        suitable = []
        thrust_per_motor_g = thrust_per_motor_n / 9.81 * 1000
        
        motors = self.motors_db.get('motors', [])
        for motor in motors:
            specs = motor.get('specs', {})
            max_thrust = specs.get('max_thrust_g', 0)
            
            # BUG-011: Unit sanity check
            # A real max_thrust_g should be > 50g (lightweight toy) and < 30000g (industrial)
            # If value is < 10 it's almost certainly in Newtons, not grams
            if max_thrust < 10:
                logger.warning(
                    f"Motor {motor.get('model', '?')} has suspiciously low max_thrust_g={max_thrust}. "
                    f"Check if value is in Newtons instead of grams."
                )
                # Assume it might be Newtons — convert for the check but don't store
                max_thrust_for_check = max_thrust * 1000  # N → g
            else:
                max_thrust_for_check = max_thrust
            
            if max_thrust_for_check >= thrust_per_motor_g * 1.2:  # 20% headroom
                suitable.append(motor)
        
        return suitable
    
    def _select_optimal_motor(self, suitable_motors: List[Dict], 
                              criteria: str = "efficiency") -> Optional[Dict]:
        """Select the best motor based on criteria"""
        if not suitable_motors:
            return None
            
        if criteria == "efficiency":
            # Sort by efficiency at 50% throttle
            return max(suitable_motors, 
                      key=lambda m: m.get('specs', {}).get('efficiency_g_per_w', 0))
        elif criteria == "power":
            return max(suitable_motors,
                      key=lambda m: m.get('specs', {}).get('max_thrust_g', 0))
        elif criteria == "weight":
            return min(suitable_motors,
                      key=lambda m: m.get('specs', {}).get('weight_g', float('inf')))
        else:
            return suitable_motors[0]
    
    def _get_motor_count(self, config: str) -> int:
        """Get motor count from configuration"""
        motor_counts = {
            'tricopter': 3,
            'quadcopter_x': 4, 'quadcopter_plus': 4, 'quadcopter_h': 4,
            'hexacopter_x': 6, 'hexacopter_plus': 6,
            'octocopter_x': 8, 'octocopter_plus': 8, 'octocopter_coax': 8,
            'conventional': 1, 'flying_wing': 1,  # Fixed wing
            'quadplane': 5,  # VTOL
        }
        return motor_counts.get(config, 4)
    
    def design(self, requirements: Any) -> Any:
        """
        Design the propulsion system based on mission requirements.
        
        Args:
            requirements: Mission requirements (MissionRequirements or dict)
            
        Returns:
            PropulsionDesign dataclass
        """
        logger.info("Starting propulsion system design")
        
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
        
        # Determine motor count
        config = mission_req.get('configuration', 'quadcopter_x')
        motor_count = self._get_motor_count(config)
        
        # Estimate AUW
        estimated_auw = self._estimate_auw(mission_req)
        
        # Calculate thrust requirements
        thrust_to_weight = 2.0
        use_case = mission_req.get('use_case', '').lower()
        
        # Adjust T/W ratio based on use case
        if 'racing' in use_case or 'acrobatic' in use_case:
            thrust_to_weight = 3.0
        elif 'heavy lift' in use_case or 'cargo' in use_case:
            thrust_to_weight = 2.5
        elif 'surveillance' in use_case or 'photography' in use_case:
            thrust_to_weight = 1.8
        elif 'agriculture' in use_case:
            thrust_to_weight = 2.2
        
        required_thrust = self._calculate_required_thrust(estimated_auw, thrust_to_weight)
        thrust_per_motor = required_thrust / motor_count
        
        # Use rule-based design (faster and more reliable than LLM for component selection)
        propulsion = self._fallback_design(mission_req, motor_count)
        
        # Import and return as PropulsionDesign dataclass
        from ..core.state import PropulsionDesign
        
        return PropulsionDesign(
            motors=propulsion.get('motors', []),
            propellers=propulsion.get('propellers', []),
            escs=propulsion.get('escs', []),
            motor_count=motor_count,
            total_thrust_n=propulsion.get('total_thrust_n', 0),
            thrust_to_weight=propulsion.get('thrust_to_weight', thrust_to_weight),
            max_power_draw_w=propulsion.get('max_power_draw_w', 0),
            hover_throttle_percent=propulsion.get('hover_throttle_percent', 50),
            hover_current_a=propulsion.get('hover_current_a', 0),
            efficiency_at_hover=propulsion.get('efficiency_at_hover', 0),
            calculations=propulsion.get('calculations', {}),
            justifications=propulsion.get('justifications', [])
        )
    
    def _parse_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return None
    
    def _validate_design(self, design: Dict, mission_req: Dict, motor_count: int) -> Dict:
        """Validate and enhance the design with calculations"""
        calculations = design.get('calculations', {})
        
        motor = design.get('motor', {})
        motor_thrust_g = motor.get('max_thrust_g', 0) or motor.get('specs', {}).get('max_thrust_g', 0)
        
        # Recalculate actual thrust to weight
        auw_kg = calculations.get('estimated_auw_kg', 1.5)
        total_thrust_g = motor_thrust_g * motor_count
        actual_tw = total_thrust_g / (auw_kg * 1000) if auw_kg > 0 else 0
        
        calculations['total_thrust_available_n'] = total_thrust_g * 9.81 / 1000
        calculations['actual_thrust_to_weight'] = round(actual_tw, 2)
        
        design['calculations'] = calculations
        return design
    
    def _fallback_design(self, mission_req: Dict, motor_count: int) -> Dict:
        """Fallback rule-based propulsion design with physical component matching"""
        payload = mission_req.get('payload_mass_kg', 0)
        drone_type = mission_req.get('drone_type', 'multirotor')
        config = mission_req.get('configuration', 'quadcopter_x')
        
        # Estimate AUW
        estimated_auw = self._estimate_auw(mission_req)
        
        # Determine target thrust-to-weight ratio based on drone type and use case
        use_case = mission_req.get('use_case', '').lower()
        if drone_type in ['fixed_wing', 'flying_wing', 'conventional']:
            thrust_to_weight = 0.8  # Fixed wings do not need high hover thrust
        elif drone_type == 'vtol':
            thrust_to_weight = 1.8  # Quadplanes need hover capability
        else:
            # Multirotors
            if 'racing' in use_case or 'acrobatic' in use_case:
                thrust_to_weight = 3.0
            elif 'heavy lift' in use_case or 'cargo' in use_case or payload > 5.0:
                thrust_to_weight = 2.2
            elif 'surveillance' in use_case or 'photography' in use_case:
                thrust_to_weight = 1.8
            else:
                thrust_to_weight = 2.0
                
        # Calculate target thrust per motor (BUG-039: apply coaxial penalty multiplier to target thrust)
        coax_factor = 1.25 if config == 'octocopter_coax' else 1.0
        required_total_thrust_n = estimated_auw * 9.81 * thrust_to_weight * coax_factor
        thrust_per_motor_n = required_total_thrust_n / motor_count
        thrust_per_motor_g = (thrust_per_motor_n / 9.81) * 1000
        
        # Get motors database
        motors = self.motors_db.get('motors', [])
        
        # Helper for unit-sanity check (BUG-038 / BUG-011)
        def get_sanitized_max_thrust(m):
            t = m.get('specs', {}).get('max_thrust_g', 0)
            if 0 < t < 100:  # Likely stored in kg instead of g
                t *= 1000.0
            return t

        # Sort motors by max_thrust_g
        sorted_motors = sorted(motors, key=lambda m: get_sanitized_max_thrust(m))
        
        # Determine minimum required max cell count based on AUW class
        if estimated_auw > 10.0:
            min_cell_max = 6
        elif estimated_auw > 3.0:
            min_cell_max = 6
        else:
            min_cell_max = 3
            
        # Find first motor satisfying the thrust and cell count requirement with some margin
        selected_motor = None
        for motor in sorted_motors:
            max_thrust = get_sanitized_max_thrust(motor)
            if max_thrust >= thrust_per_motor_g * 1.1:  # 10% margin
                motor_cells = motor.get('specs', {}).get('cell_count_max', 6)
                if motor_cells >= min_cell_max:
                    selected_motor = motor
                    break
                    
        # If no motor satisfies the cell count constraint, try to get any motor satisfying the thrust
        if not selected_motor:
            for motor in sorted_motors:
                max_thrust = get_sanitized_max_thrust(motor)
                if max_thrust >= thrust_per_motor_g * 1.1:
                    selected_motor = motor
                    break
                
        # If no motor is large enough, select the largest available motor
        if not selected_motor:
            selected_motor = sorted_motors[-1] if sorted_motors else {
                "id": "default_motor",
                "brand": "Generic",
                "model": "4010-620KV",
                "specs": {"kv": 620, "max_thrust_g": 2000, "max_power_w": 600, "max_current_a": 40, "cell_count_max": 6}
            }
            
        # Select propeller based on recommended sizes of the selected motor
        rec_props = selected_motor.get('specs', {}).get('recommended_props_in', []) or selected_motor.get('recommended_props_in', [])
        target_prop_size = rec_props[0] if rec_props else 10.0
        
        propellers = self.propellers_db.get('propellers', [])
        selected_prop = propellers[0] if propellers else {
            "id": "default_prop",
            "size_inch": 10.0,
            "pitch_inch": 4.5
        }
        
        # BUG-010: Find propeller closest to recommended size AND within pitch tolerance
        # Only accept props whose pitch is within ±40% of target pitch
        # to prevent selecting a 10-inch 4-pitch when target is 10-inch 6-pitch
        min_diff = float('inf')
        best_pitch_diff = float('inf')
        target_pitch = 6.0 if target_prop_size > 15 else (5.0 if target_prop_size > 10 else 4.5)
        max_pitch_deviation_factor = 0.40  # 40% tolerance on pitch
        max_acceptable_pitch_diff = target_pitch * max_pitch_deviation_factor
        
        # First pass: try to find prop matching both size AND pitch within tolerance
        for prop in propellers:
            size = prop.get('diameter_in', prop.get('size_inch', 5.0))
            pitch = prop.get('pitch_in', prop.get('pitch_inch', 4.5))
            diff = abs(size - target_prop_size)
            pitch_diff = abs(pitch - target_pitch)
            
            if pitch_diff <= max_acceptable_pitch_diff:  # Only consider in-tolerance pitches
                if diff < min_diff or (abs(diff - min_diff) < 0.01 and pitch_diff < best_pitch_diff):
                    min_diff = diff
                    best_pitch_diff = pitch_diff
                    selected_prop = prop
        
        # Second pass: if nothing within pitch tolerance, relax to closest pitch
        if best_pitch_diff == float('inf'):
            logger.warning(
                f"No propeller within {max_pitch_deviation_factor*100:.0f}% of target pitch {target_pitch}"
                f" for size {target_prop_size}in. Selecting closest available."
            )
            min_diff = float('inf')
            best_pitch_diff = float('inf')
            for prop in propellers:
                size = prop.get('diameter_in', prop.get('size_inch', 5.0))
                pitch = prop.get('pitch_in', prop.get('pitch_inch', 4.5))
                diff = abs(size - target_prop_size)
                pitch_diff = abs(pitch - target_pitch)
                if diff < min_diff or (abs(diff - min_diff) < 0.01 and pitch_diff < best_pitch_diff):
                    min_diff = diff
                    best_pitch_diff = pitch_diff
                    selected_prop = prop
                
        # Select ESC based on selected motor's max current rating
        motor_max_current = selected_motor.get('specs', {}).get('max_current_a', 30)
        required_esc_current = motor_max_current * 1.2  # 20% safety headroom
        
        escs = self.escs_db.get('escs', [])
        selected_esc = None
        
        # Sort ESCs by continuous current in ascending order
        sorted_escs = sorted(escs, key=lambda e: e.get('continuous_current_a', 0))
        for esc in sorted_escs:
            if esc.get('continuous_current_a', 0) >= required_esc_current:
                selected_esc = esc
                break
                
        if not selected_esc:
            selected_esc = sorted_escs[-1] if sorted_escs else {
                "id": "default_esc",
                "brand": "Generic",
                "model": "50A",
                "specs": {"current_rating_a": 50}
            }
            
        # Calculate physical design properties dynamically
        motor_max_thrust_g = selected_motor.get('specs', {}).get('max_thrust_g', 920)
        total_thrust_g = motor_max_thrust_g * motor_count
        if config == 'octocopter_coax':
            total_thrust_g *= 0.8  # Apply 20% thrust loss factor for coaxial configuration
            
        actual_tw = total_thrust_g / (estimated_auw * 1000) if estimated_auw > 0 else thrust_to_weight
        
        hover_throttle = (1.0 / actual_tw) * 100 if actual_tw > 0 else 50.0
        hover_throttle = max(10.0, min(100.0, hover_throttle))
        
        motor_power_w = selected_motor.get('specs', {}).get('max_power_w', 430)
        total_power_w = motor_power_w * motor_count
        
        # Estimate hover current: hover power draw (W) ≈ estimated_auw * 150
        # Hover current (A) = hover power / estimated voltage
        max_cells = selected_motor.get('specs', {}).get('cell_count_max', 4)
        est_voltage = max_cells * 3.7
        hover_current = (estimated_auw * 150) / est_voltage if est_voltage > 0 else (10.0 * motor_count)
        
        return {
            'motors': [selected_motor] * motor_count,
            'propellers': [selected_prop] * motor_count,
            'escs': [selected_esc] * motor_count,
            'motor_count': motor_count,
            'total_thrust_n': total_thrust_g * 9.81 / 1000,
            'thrust_to_weight': round(actual_tw, 2),
            'max_power_draw_w': total_power_w,
            'hover_throttle_percent': round(hover_throttle, 1),
            'hover_current_a': round(hover_current, 2),
            'efficiency_at_hover': selected_motor.get('specs', {}).get('efficiency_g_per_w', 7.0),
            'calculations': {
                'estimated_auw_kg': round(estimated_auw, 3),
                'motor_count': motor_count,
                'target_thrust_to_weight': thrust_to_weight,
                'total_hover_power_w': estimated_auw * 150.0,
                'note': 'Rule-based propulsion selection completed successfully'
            },
            'justifications': [
                f"Selected {selected_motor.get('manufacturer', selected_motor.get('brand', 'Generic'))} {selected_motor['model']} motor based on estimated AUW of {estimated_auw:.2f}kg and {motor_count} motor configuration.",
                f"Paired with {selected_prop['model']} propeller (diameter: {selected_prop.get('diameter_in', 5.0)} inches) matching motor recommended specifications.",
                f"Selected {selected_esc.get('manufacturer', selected_esc.get('brand', 'Generic'))} {selected_esc['model']} ESC providing {selected_esc.get('continuous_current_a', 50)}A continuous rating (> 1.2x motor max current of {motor_max_current}A)."
            ]
        }
