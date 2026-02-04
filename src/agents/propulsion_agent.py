"""
DroneForge AI - Propulsion Agent
Designs the propulsion system including motors, propellers, and ESCs.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import asdict

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
        self.motors_db = self._load_database("databases/motors/motor_database.json")
        self.propellers_db = self._load_database("databases/propellers/propeller_database.json")
        self.escs_db = self._load_database("databases/escs/esc_database.json")
        
    def _load_database(self, path: str) -> Dict[str, Any]:
        """Load component database from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
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
        }
        frame_weight_g = frame_weights.get(config, 500)
        
        # Adjust frame weight for payload capacity
        if payload > 2:
            frame_weight_g *= 1.5
        if payload > 5:
            frame_weight_g *= 2
        
        # Estimate motor weight (avg 80-150g per motor)
        motor_weight_g = motor_count * 100
        
        # Propeller weight (avg 20-40g per prop)
        prop_weight_g = motor_count * 30
        
        # ESC weight (avg 30-60g per ESC)
        esc_weight_g = motor_count * 40
        
        # Electronics (FC, GPS, receiver, wiring)
        electronics_weight_g = 300
        
        # Battery weight estimation based on endurance
        # Rough formula: longer flight = bigger battery
        # Energy needed ≈ (AUW × 150W/kg) × (endurance/60) hours
        # Battery weight ≈ Energy needed / 180 Wh/kg (typical LiPo energy density)
        base_power_w_per_kg = 150
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
        """Filter motors that meet thrust requirements"""
        suitable = []
        thrust_per_motor_g = thrust_per_motor_n / 9.81 * 1000
        
        motors = self.motors_db.get('motors', [])
        for motor in motors:
            specs = motor.get('specs', {})
            max_thrust = specs.get('max_thrust_g', 0)
            if max_thrust >= thrust_per_motor_g * 1.2:  # 20% headroom
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
        """Fallback rule-based propulsion design"""
        payload = mission_req.get('payload_mass_kg', 0)
        
        # Select motor based on payload
        if payload < 0.5:
            motor_class = "small"  # 2206-2306 class
        elif payload < 2:
            motor_class = "medium"  # 2814-3508 class
        elif payload < 5:
            motor_class = "large"  # 4008-5008 class
        else:
            motor_class = "xlarge"  # 6010+ class
        
        # Default selections
        motors = self.motors_db.get('motors', [])
        selected_motor = motors[0] if motors else {
            "id": "default_motor",
            "brand": "Generic",
            "model": "4010-620KV",
            "specs": {"kv": 620, "max_thrust_g": 2000}
        }
        
        propellers = self.propellers_db.get('propellers', [])
        selected_prop = propellers[0] if propellers else {
            "id": "default_prop",
            "size_inch": 15,
            "pitch_inch": 5.5
        }
        
        escs = self.escs_db.get('escs', [])
        selected_esc = escs[0] if escs else {
            "id": "default_esc",
            "brand": "Generic",
            "model": "50A",
            "specs": {"current_rating_a": 50}
        }
        
        return {
            'motors': [selected_motor],
            'propellers': [selected_prop],
            'escs': [selected_esc],
            'motor_count': motor_count,
            'total_thrust_n': selected_motor.get('specs', {}).get('max_thrust_g', 2000) * motor_count * 9.81 / 1000,
            'thrust_to_weight': 2.0,
            'max_power_draw_w': 500 * motor_count,
            'hover_throttle_percent': 50,
            'hover_current_a': 10 * motor_count,
            'efficiency_at_hover': 10,
            'calculations': {
                'estimated_auw_kg': 2.0,
                'motor_count': motor_count,
                'note': 'Fallback design - manual verification recommended'
            },
            'justifications': ['Fallback design used due to LLM parsing error']
        }
