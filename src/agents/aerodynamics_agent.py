"""
DroneForge AI - Aerodynamics Agent
Analyzes aerodynamic properties for all drone types.
"""

import json
import logging
import math
from typing import Dict, Any, Optional, List
from dataclasses import asdict

logger = logging.getLogger(__name__)

AERODYNAMICS_PROMPT = """You are an expert drone aerodynamics engineer. Analyze the aerodynamic properties of the drone based on the mission requirements and propulsion design.

## Mission Requirements:
{mission_requirements}

## Propulsion Design:
{propulsion_design}

## Drone Configuration:
- Type: {drone_type}
- Configuration: {configuration}

## Analysis Required:

### For Multirotors:
1. Drag coefficient estimation (typical range 0.3-1.2 for multirotors)
2. Frontal area calculation based on frame size
3. Drag force at cruise speed
4. Wind resistance capability
5. Prop wash interference analysis

### For Fixed-Wing:
1. Wing loading calculation
2. Lift coefficient for cruise
3. Drag polar (Cd0 + Cd_induced)
4. L/D ratio
5. Stall speed calculation
6. Aspect ratio effects

### For VTOL:
1. Transition corridor analysis
2. Hover efficiency vs cruise efficiency
3. Control authority during transition

## Required Calculations:
- Drag coefficient (Cd)
- Frontal area (A) in m²
- Drag force at cruise: Fd = 0.5 × ρ × V² × Cd × A
- Air density (ρ) at operating altitude
- Reynolds number for propellers/wings
- Wind penetration speed: V_wind = sqrt(2 × (Thrust_available - Weight) / (ρ × Cd × A))

## Output Format (JSON):
{{
    "drag_coefficient": 0.8,
    "frontal_area_m2": 0.05,
    "drag_force_at_cruise_n": 2.5,
    "lift_coefficient": 0.0,
    "wing_area_m2": 0.0,
    "aspect_ratio": 0.0,
    "stall_speed_ms": 0.0,
    "lift_to_drag_ratio": 0.0,
    "static_margin": 0.0,
    "cg_range_mm": [0, 0],
    "max_wind_speed_ms": 12.0,
    "wind_penetration_capability": "moderate",
    "reynolds_number": 500000,
    "propeller_efficiency": 0.65,
    "calculations": {{
        "air_density_kg_m3": 1.225,
        "cruise_speed_ms": 10,
        "operating_altitude_m": 100,
        "thrust_margin_for_wind_n": 0.0,
        "calculation_steps": [
            "Step 1: ...",
            "Step 2: ..."
        ]
    }},
    "justifications": [
        "Drag coefficient estimated based on...",
        "Frontal area calculated from..."
    ]
}}
"""


class AerodynamicsAgent:
    """Agent for aerodynamic analysis"""
    
    # Standard air properties
    AIR_DENSITY_SL = 1.225  # kg/m³ at sea level
    AIR_VISCOSITY = 1.81e-5  # Pa·s at 20°C
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _calculate_air_density(self, altitude_m: float, temp_c: float = 20) -> float:
        """
        Calculate air density at altitude using barometric formula.
        
        Args:
            altitude_m: Altitude in meters
            temp_c: Temperature in Celsius
            
        Returns:
            Air density in kg/m³
        """
        # Temperature lapse rate: -6.5°C per 1000m
        temp_at_altitude = temp_c - 0.0065 * altitude_m
        temp_k = temp_at_altitude + 273.15
        
        # Barometric formula
        pressure_ratio = (1 - 0.0065 * altitude_m / 288.15) ** 5.255
        density = self.AIR_DENSITY_SL * pressure_ratio * (288.15 / temp_k)
        
        return density
    
    def _estimate_frontal_area(self, config: str, frame_size_mm: float = 500) -> float:
        """
        Estimate frontal area based on drone configuration.
        
        Returns:
            Frontal area in m²
        """
        frame_size_m = frame_size_mm / 1000
        
        # Approximate frontal areas by configuration
        area_factors = {
            'quadcopter_x': 0.15,  # fraction of frame circle
            'quadcopter_plus': 0.15,
            'hexacopter_x': 0.18,
            'hexacopter_plus': 0.18,
            'octocopter_x': 0.20,
            'octocopter_plus': 0.20,
            'octocopter_coax': 0.25,
            'tricopter': 0.12,
            'conventional': 0.08,  # Fixed wing - sleeker
            'flying_wing': 0.05,
            'quadplane': 0.12,
        }
        
        factor = area_factors.get(config, 0.15)
        
        # Approximate as fraction of bounding circle
        return math.pi * (frame_size_m / 2) ** 2 * factor
    
    def _estimate_drag_coefficient(self, drone_type: str, config: str, 
                                   has_landing_gear: bool = True) -> float:
        """
        Estimate drag coefficient based on drone type.
        
        Returns:
            Estimated Cd
        """
        base_cd = {
            'multirotor': {
                'quadcopter_x': 0.7,
                'quadcopter_plus': 0.8,
                'hexacopter_x': 0.75,
                'hexacopter_plus': 0.85,
                'octocopter_x': 0.8,
                'tricopter': 0.65,
            },
            'fixed_wing': {
                'conventional': 0.04,  # Profile + induced
                'flying_wing': 0.03,
                'delta': 0.05,
            },
            'vtol': {
                'quadplane': 0.5,  # In hover mode
                'tiltrotor': 0.45,
                'tailsitter': 0.4,
            }
        }
        
        cd = base_cd.get(drone_type, {}).get(config, 0.7)
        
        # Adjustments
        if has_landing_gear:
            cd *= 1.1
        
        return cd
    
    def _calculate_drag_force(self, cd: float, area_m2: float, 
                              velocity_ms: float, density: float) -> float:
        """
        Calculate drag force using drag equation.
        
        Fd = 0.5 × ρ × V² × Cd × A
        
        Returns:
            Drag force in Newtons
        """
        return 0.5 * density * velocity_ms ** 2 * cd * area_m2
    
    def _calculate_wind_penetration(self, available_thrust_n: float, 
                                    weight_n: float, cd: float, 
                                    area_m2: float, density: float) -> float:
        """
        Calculate maximum wind speed the drone can fly into using correct physical limits.
        """
        # Physically correct available horizontal thrust: sqrt(T_max^2 - W^2) (BUG-061)
        if available_thrust_n > weight_n:
            horizontal_thrust = math.sqrt(available_thrust_n**2 - weight_n**2)
        else:
            horizontal_thrust = 0.0
            
        # V = sqrt(2F / (ρ × Cd × A))
        if cd * area_m2 > 0:
            return math.sqrt(2 * horizontal_thrust / (density * cd * area_m2))
        return 0
    
    def _calculate_reynolds_number(self, chord_m: float, velocity_ms: float,
                                   density: float) -> float:
        """
        Calculate Reynolds number for aerodynamic analysis.
        """
        return density * velocity_ms * chord_m / self.AIR_VISCOSITY
    
    def _fixed_wing_analysis(self, mission_req: Dict, propulsion: Dict, structural_dict: Dict = None) -> Dict:
        """Perform fixed-wing specific aerodynamic analysis (BUG-043)"""
        # Determine wingspan dynamically from structural design if available
        wingspan_mm = 1500  # Default fallback
        if structural_dict:
            wingspan_mm = structural_dict.get('calculations', {}).get('wingspan_mm', 1500)
            
        wing_span_m = wingspan_mm / 1000
        
        # Calculate wing area based on realistic aspect ratio (6.5)
        aspect_ratio = 6.5
        wing_area_m2 = (wing_span_m ** 2) / aspect_ratio
        
        auw_kg = propulsion.get('calculations', {}).get('estimated_auw_kg', 2.0)
        if structural_dict:
            auw_kg = structural_dict.get('frame_weight_g', 0) / 1000.0 + propulsion.get('calculations', {}).get('estimated_auw_kg', 2.0) - 0.5  # Adjust for actual frame weight
            if auw_kg <= 0:
                auw_kg = 2.0
                
        cruise_speed = mission_req.get('cruise_speed_ms', 15)
        
        # Wing loading
        wing_loading = (auw_kg * 9.81) / wing_area_m2  # N/m²
        
        # Lift coefficient for level flight: CL = 2W / (ρ × V² × S)
        density = self._calculate_air_density(100)
        cl_cruise = (2 * auw_kg * 9.81) / (density * cruise_speed ** 2 * wing_area_m2)
        
        # Stall speed (assuming CL_max ≈ 1.4)
        cl_max = 1.4
        stall_speed = math.sqrt((2 * auw_kg * 9.81) / (density * wing_area_m2 * cl_max))
        
        # Drag polar: CD = CD0 + CL² / (π × e × AR)
        cd0 = 0.025  # Zero-lift drag coefficient
        e = 0.8  # Oswald efficiency
        cd_induced = cl_cruise ** 2 / (math.pi * e * aspect_ratio)
        cd_total = cd0 + cd_induced
        
        # L/D ratio
        l_d_ratio = cl_cruise / cd_total if cd_total > 0 else 0
        
        return {
            'wing_area_m2': round(wing_area_m2, 4),
            'aspect_ratio': round(aspect_ratio, 2),
            'wing_loading_n_m2': round(wing_loading, 1),
            'lift_coefficient': round(cl_cruise, 3),
            'cd_zero_lift': cd0,
            'cd_induced': round(cd_induced, 4),
            'drag_coefficient': round(cd_total, 4),
            'lift_to_drag_ratio': round(l_d_ratio, 1),
            'stall_speed_ms': round(stall_speed, 1),
            'oswald_efficiency': e
        }
    
    def analyze(self, requirements: Any, propulsion: Any, structural: Any = None) -> Any:
        """
        Analyze aerodynamics based on mission and propulsion design.
        """
        logger.info("Starting aerodynamics analysis")
        
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion_dict = asdict(propulsion)
        else:
            propulsion_dict = propulsion if isinstance(propulsion, dict) else {}
            
        if structural and hasattr(structural, '__dict__') and not isinstance(structural, dict):
            structural_dict = asdict(structural)
        else:
            structural_dict = structural if isinstance(structural, dict) else {}
        
        drone_type = mission_req.get('drone_type', 'multirotor')
        config = mission_req.get('configuration', 'quadcopter_x')
        cruise_speed = mission_req.get('cruise_speed_ms', 10)
        max_altitude = mission_req.get('max_altitude_m', 120)
        
        # Calculate air properties
        density = self._calculate_air_density(max_altitude / 2)  # Average altitude
        
        # Estimate aerodynamic parameters
        if isinstance(drone_type, str):
            drone_type_str = drone_type
        else:
            drone_type_str = drone_type.value if hasattr(drone_type, 'value') else str(drone_type)
        
        cd = self._estimate_drag_coefficient(drone_type_str, config)
        frontal_area = self._estimate_frontal_area(config)
        
        # Calculate drag at cruise
        drag_force = self._calculate_drag_force(cd, frontal_area, cruise_speed, density)
        
        # Calculate wind penetration capability
        total_thrust = propulsion_dict.get('total_thrust_n', 50)
        calcs = propulsion_dict.get('calculations', {})
        if isinstance(calcs, dict):
            auw_kg = calcs.get('estimated_auw_kg', 2.0)
        else:
            auw_kg = 2.0
        weight_n = auw_kg * 9.81
        
        max_wind = self._calculate_wind_penetration(total_thrust, weight_n, 
                                                    cd, frontal_area, density)
        
        # Wind capability classification
        if max_wind >= 15:
            wind_capability = "excellent"
        elif max_wind >= 10:
            wind_capability = "good"
        elif max_wind >= 6:
            wind_capability = "moderate"
        else:
            wind_capability = "limited"
        
        # Fixed-wing specific analysis
        fw_analysis = {}
        if drone_type_str in ['fixed_wing', 'vtol']:
            fw_analysis = self._fixed_wing_analysis(mission_req, propulsion_dict, structural_dict)
        
        # Skip LLM call for now - use calculated values
        # This keeps the design fast and avoids async issues
        
        # Import AerodynamicsAnalysis from state
        from ..core.state import AerodynamicsAnalysis
        
        # Build aerodynamics result
        result = AerodynamicsAnalysis(
            drag_coefficient=round(cd, 3),
            frontal_area_m2=round(frontal_area, 4),
            drag_force_at_cruise_n=round(drag_force, 2),
            lift_coefficient=fw_analysis.get('lift_coefficient', 0),
            wing_area_m2=fw_analysis.get('wing_area_m2', 0),
            aspect_ratio=fw_analysis.get('aspect_ratio', 0),
            stall_speed_ms=fw_analysis.get('stall_speed_ms', 0),
            static_margin=0.15,
            cg_range_mm=[-10.0, 10.0],
            max_wind_speed_ms=round(max_wind, 1),
            wind_penetration_capability=wind_capability,
            calculations={
                'air_density_kg_m3': round(density, 4),
                'cruise_speed_ms': cruise_speed,
                'operating_altitude_m': max_altitude,
                'reynolds_number': int(self._calculate_reynolds_number(0.1, cruise_speed, density)),
                'lift_to_drag_ratio': fw_analysis.get('lift_to_drag_ratio', 0),
                **fw_analysis
            },
            justifications=[
                f"Drag coefficient {cd:.2f} estimated for {config} configuration",
                f"Frontal area {frontal_area:.4f} m² based on frame geometry",
                f"Wind penetration {max_wind:.1f} m/s based on available thrust margin",
            ]
        )
        
        logger.info("Aerodynamics analysis completed")
        return result
    
    def _parse_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        return None
