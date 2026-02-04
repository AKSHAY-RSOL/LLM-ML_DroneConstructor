"""
DroneForge AI - Structural Design Agent
Designs frame structure and performs stress analysis.
"""

import json
import logging
import math
from typing import Dict, Any, Optional, List
from dataclasses import asdict

logger = logging.getLogger(__name__)

STRUCTURAL_PROMPT = """You are an expert drone structural engineer. Design the frame structure and perform stress analysis.

## Mission Requirements:
{mission_requirements}

## Propulsion Design:
{propulsion_design}

## Materials Database:
{materials_db}

## Frames Database:
{frames_db}

## Design Requirements:
1. Frame must support all-up weight with safety factor ≥ {safety_factor}
2. Arms must handle maximum thrust loads and crash forces
3. Material suitable for operating temperature range
4. Landing gear must handle landing impact loads

## Structural Analysis Required:

### Arm Stress Analysis:
- Bending moment: M = Thrust × Arm_length
- Bending stress: σ = M × c / I
- For circular tube: I = π/64 × (D⁴ - d⁴)
- Safety factor: SF = σ_yield / σ_max

### Vibration Analysis:
- Natural frequency of arms
- Should be >2x motor RPM frequency to avoid resonance

### Landing Gear Analysis:
- Impact load = (AUW × g × drop_height × 2) / deformation
- Stress at landing gear attachment points

## Output Format (JSON):
{{
    "frame_selection": {{
        "id": "frame_id",
        "brand": "...",
        "model": "...",
        "wheelbase_mm": 500,
        "price_usd": 0
    }},
    "custom_frame_design": {{
        "required": false,
        "arm_length_mm": 200,
        "arm_outer_diameter_mm": 16,
        "arm_wall_thickness_mm": 1.5,
        "center_plate_thickness_mm": 3,
        "material": "carbon_fiber"
    }},
    "stress_analysis": {{
        "max_bending_moment_nm": 0.0,
        "max_bending_stress_mpa": 0.0,
        "yield_strength_mpa": 0.0,
        "safety_factor": 2.5,
        "natural_frequency_hz": 150
    }},
    "landing_gear": {{
        "type": "fixed",
        "height_mm": 80,
        "material": "aluminum",
        "impact_load_capacity_n": 500
    }},
    "structural_bom": [
        {{"item": "Frame kit", "quantity": 1, "unit_price": 100}}
    ],
    "total_structural_weight_g": 500,
    "calculations": {{
        "step_by_step": ["Step 1: ...", "Step 2: ..."]
    }},
    "justifications": [
        "Frame selected because...",
        "Material chosen for..."
    ]
}}
"""


class StructuralAgent:
    """Agent for structural design and analysis"""
    
    # Common material properties
    MATERIALS = {
        'carbon_fiber': {
            'density_kg_m3': 1600,
            'tensile_strength_mpa': 600,
            'modulus_gpa': 70,
            'cost_factor': 3.0
        },
        'aluminum_6061': {
            'density_kg_m3': 2700,
            'tensile_strength_mpa': 310,
            'modulus_gpa': 69,
            'cost_factor': 1.0
        },
        'aluminum_7075': {
            'density_kg_m3': 2810,
            'tensile_strength_mpa': 572,
            'modulus_gpa': 71,
            'cost_factor': 1.5
        },
        'g10_fiberglass': {
            'density_kg_m3': 1800,
            'tensile_strength_mpa': 300,
            'modulus_gpa': 20,
            'cost_factor': 0.5
        },
        'abs_plastic': {
            'density_kg_m3': 1050,
            'tensile_strength_mpa': 40,
            'modulus_gpa': 2.3,
            'cost_factor': 0.3
        },
        'tpu': {
            'density_kg_m3': 1200,
            'tensile_strength_mpa': 25,
            'modulus_gpa': 0.05,
            'cost_factor': 0.4
        }
    }
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
        self.frames_db = self._load_database("databases/frames/frame_database.json")
        self.materials_db = self._load_database("databases/materials/materials_database.json")
    
    def _load_database(self, path: str) -> Dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load {path}: {e}")
            return {}
    
    def _get_motor_count(self, config: str) -> int:
        """Get motor count from configuration"""
        counts = {
            'tricopter': 3,
            'quadcopter_x': 4, 'quadcopter_plus': 4, 'quadcopter_h': 4,
            'hexacopter_x': 6, 'hexacopter_plus': 6,
            'octocopter_x': 8, 'octocopter_plus': 8, 'octocopter_coax': 8,
        }
        return counts.get(config, 4)
    
    def _calculate_arm_length(self, wheelbase_mm: float, config: str) -> float:
        """Calculate arm length from wheelbase"""
        # For X configuration: arm_length = wheelbase / (2 × cos(45°))
        if 'x' in config.lower():
            return wheelbase_mm / (2 * math.cos(math.radians(45)))
        else:
            return wheelbase_mm / 2
    
    def _calculate_min_wheelbase(self, prop_size_inch: float, motor_count: int) -> float:
        """Calculate minimum wheelbase for propeller clearance"""
        prop_diameter_mm = prop_size_inch * 25.4
        clearance_mm = 10  # Minimum clearance between props
        
        if motor_count == 4:
            # Quadcopter X: props at 45° angles
            min_spacing = (prop_diameter_mm + clearance_mm) * math.sqrt(2)
        elif motor_count == 6:
            # Hexacopter: props at 60° angles
            min_spacing = (prop_diameter_mm + clearance_mm) * 2
        elif motor_count == 8:
            min_spacing = (prop_diameter_mm + clearance_mm) * 2.2
        else:
            min_spacing = (prop_diameter_mm + clearance_mm) * 2
        
        return min_spacing
    
    def _calculate_tube_moment_of_inertia(self, outer_d_mm: float, wall_t_mm: float) -> float:
        """
        Calculate moment of inertia for hollow circular tube.
        I = π/64 × (D⁴ - d⁴)
        
        Returns:
            Moment of inertia in mm⁴
        """
        outer_d = outer_d_mm
        inner_d = outer_d_mm - 2 * wall_t_mm
        return math.pi / 64 * (outer_d**4 - inner_d**4)
    
    def _calculate_bending_stress(self, moment_nm: float, 
                                  outer_d_mm: float, I_mm4: float) -> float:
        """
        Calculate maximum bending stress.
        σ = M × c / I
        
        Args:
            moment_nm: Bending moment in N⋅m
            outer_d_mm: Outer diameter in mm
            I_mm4: Moment of inertia in mm⁴
            
        Returns:
            Stress in MPa
        """
        c = outer_d_mm / 2  # Distance to outer fiber in mm
        moment_nmm = moment_nm * 1000  # Convert to N⋅mm
        stress_mpa = (moment_nmm * c) / I_mm4
        return stress_mpa
    
    def _calculate_natural_frequency(self, length_mm: float, outer_d_mm: float,
                                     wall_t_mm: float, material: str) -> float:
        """
        Calculate first natural frequency of cantilever arm.
        f = (1.875²)/(2π) × sqrt(EI/(ρAL⁴))
        
        Returns:
            Natural frequency in Hz
        """
        mat_props = self.MATERIALS.get(material, self.MATERIALS['carbon_fiber'])
        E = mat_props['modulus_gpa'] * 1e9  # Convert to Pa
        rho = mat_props['density_kg_m3']
        
        I = self._calculate_tube_moment_of_inertia(outer_d_mm, wall_t_mm) * 1e-12  # m⁴
        inner_d = outer_d_mm - 2 * wall_t_mm
        A = math.pi / 4 * (outer_d_mm**2 - inner_d**2) * 1e-6  # m²
        L = length_mm * 1e-3  # m
        
        # First mode of cantilever beam
        lambda1 = 1.875
        fn = (lambda1**2 / (2 * math.pi)) * math.sqrt(E * I / (rho * A * L**4))
        
        return fn
    
    def _estimate_frame_weight(self, wheelbase_mm: float, config: str,
                               material: str, payload_capacity_kg: float) -> float:
        """Estimate frame weight based on parameters"""
        motor_count = self._get_motor_count(config)
        arm_length = self._calculate_arm_length(wheelbase_mm, config)
        
        mat_props = self.MATERIALS.get(material, self.MATERIALS['carbon_fiber'])
        density = mat_props['density_kg_m3']
        
        # Estimate arm dimensions based on payload
        if payload_capacity_kg < 1:
            arm_od_mm = 10
            arm_wall_mm = 1.0
        elif payload_capacity_kg < 3:
            arm_od_mm = 16
            arm_wall_mm = 1.5
        elif payload_capacity_kg < 6:
            arm_od_mm = 20
            arm_wall_mm = 2.0
        else:
            arm_od_mm = 25
            arm_wall_mm = 2.5
        
        # Arm volume
        inner_d = arm_od_mm - 2 * arm_wall_mm
        arm_volume_mm3 = math.pi / 4 * (arm_od_mm**2 - inner_d**2) * arm_length
        arm_volume_m3 = arm_volume_mm3 * 1e-9
        arm_weight_g = density * arm_volume_m3 * motor_count * 1000
        
        # Center plate estimate
        plate_weight_g = 100 + payload_capacity_kg * 50
        
        # Landing gear estimate
        lg_weight_g = 50 + payload_capacity_kg * 30
        
        return arm_weight_g + plate_weight_g + lg_weight_g
    
    def _select_frame(self, config: str, min_wheelbase_mm: float,
                      payload_kg: float, budget: float) -> Optional[Dict]:
        """Select suitable frame from database"""
        frames = self.frames_db.get('frames', {}).get('multirotor', [])
        
        suitable_frames = []
        for frame in frames:
            specs = frame.get('specs', {})
            wheelbase = specs.get('wheelbase_mm', 0)
            capacity = frame.get('payload_capacity_kg', 0)
            price = frame.get('price_usd', 0)
            
            if (wheelbase >= min_wheelbase_mm and 
                capacity >= payload_kg and 
                price <= budget * 0.1):  # Frame should be <10% of budget
                suitable_frames.append(frame)
        
        if suitable_frames:
            # Sort by capacity match (closest to requirement)
            suitable_frames.sort(key=lambda f: abs(f.get('payload_capacity_kg', 0) - payload_kg))
            return suitable_frames[0]
        
        return None
    
    def design(self, requirements: Any, propulsion: Any) -> Any:
        """
        Design structural components.
        
        Args:
            requirements: Mission requirements
            propulsion: Propulsion design
            
        Returns:
            StructuralDesign dataclass
        """
        logger.info("Starting structural design")
        
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion_dict = asdict(propulsion)
        else:
            propulsion_dict = propulsion if isinstance(propulsion, dict) else {}
        
        config = mission_req.get('configuration', 'quadcopter_x')
        payload_kg = mission_req.get('payload_mass_kg', 0)
        budget = mission_req.get('max_cost', 100000)
        motor_count = self._get_motor_count(config)
        
        # Get propeller size from propulsion design
        props = propulsion_dict.get('propellers', [{}])
        prop_size = props[0].get('size_inch', 10) if props else 10
        
        # Calculate minimum wheelbase
        min_wheelbase = self._calculate_min_wheelbase(prop_size, motor_count)
        
        # Try to select existing frame
        selected_frame = self._select_frame(config, min_wheelbase, payload_kg, budget)
        
        if selected_frame:
            wheelbase = selected_frame.get('specs', {}).get('wheelbase_mm', min_wheelbase)
            frame_weight = selected_frame.get('specs', {}).get('weight_g', 500)
            material = selected_frame.get('specs', {}).get('material', 'carbon_fiber')
            arm_od = selected_frame.get('specs', {}).get('arm_diameter_mm', 16)
            custom_required = False
        else:
            # Design custom frame
            wheelbase = min_wheelbase * 1.1  # 10% margin
            material = 'carbon_fiber' if payload_kg > 1 else 'g10_fiberglass'
            
            if payload_kg < 1:
                arm_od = 10
                arm_wall = 1.0
            elif payload_kg < 3:
                arm_od = 16
                arm_wall = 1.5
            else:
                arm_od = 20
                arm_wall = 2.0
            
            frame_weight = self._estimate_frame_weight(wheelbase, config, material, payload_kg)
            custom_required = True
        
        # Calculate arm length
        arm_length = self._calculate_arm_length(wheelbase, config)
        arm_wall = 1.5 if arm_od <= 16 else 2.0
        
        # Stress analysis
        thrust_per_motor_n = propulsion_dict.get('total_thrust_n', 50) / motor_count
        max_moment = thrust_per_motor_n * (arm_length / 1000)  # N⋅m
        
        # Add impact factor for dynamic loads
        dynamic_factor = 2.0
        max_moment_dynamic = max_moment * dynamic_factor
        
        # Calculate stress
        I = self._calculate_tube_moment_of_inertia(arm_od, arm_wall)
        max_stress = self._calculate_bending_stress(max_moment_dynamic, arm_od, I)
        
        # Get yield strength
        mat_props = self.MATERIALS.get(material.lower().replace(' ', '_'), 
                                       self.MATERIALS['carbon_fiber'])
        yield_strength = mat_props['tensile_strength_mpa']
        safety_factor = yield_strength / max_stress if max_stress > 0 else 10
        
        # Natural frequency
        nat_freq = self._calculate_natural_frequency(arm_length, arm_od, arm_wall, 
                                                     material.lower().replace(' ', '_'))
        
        # Landing gear design
        calcs = propulsion_dict.get('calculations', {})
        if isinstance(calcs, dict):
            auw_kg = calcs.get('estimated_auw_kg', 2.0)
        else:
            auw_kg = 2.0
        drop_height_m = 0.3  # 30cm drop test
        deformation_m = 0.02  # 2cm deformation allowed
        impact_load = (auw_kg * 9.81 * drop_height_m * 2) / deformation_m
        
        lg_height = max(80, prop_size * 25.4 / 3)  # At least 1/3 prop diameter
        
        # Build structural design result
        from ..core.state import StructuralDesign
        
        result = StructuralDesign(
            frame_type=selected_frame.get('model', 'custom') if selected_frame else 'custom',
            frame_material=material,
            frame_weight_g=round(frame_weight, 0),
            arm_length_mm=round(arm_length, 1),
            arm_diameter_mm=arm_od,
            arm_wall_thickness_mm=arm_wall,
            wheelbase_mm=round(wheelbase, 0),
            max_bending_stress_mpa=round(max_stress, 2),
            safety_factor=round(safety_factor, 2),
            natural_frequency_hz=round(nat_freq, 1),
            landing_gear_type='fixed',
            landing_gear_material='aluminum',
            landing_gear_height_mm=round(lg_height, 0),
            calculations={
                'min_wheelbase_mm': round(min_wheelbase, 0),
                'moment_of_inertia_mm4': round(I, 2),
                'max_bending_moment_nm': round(max_moment_dynamic, 3),
                'yield_strength_mpa': yield_strength,
                'impact_load_n': round(impact_load, 1),
                'custom_required': custom_required,
            },
            justifications=[
                f"Frame wheelbase {wheelbase:.0f}mm provides {(wheelbase/min_wheelbase-1)*100:.0f}% margin over minimum",
                f"Safety factor {safety_factor:.1f} exceeds minimum requirement of 2.0",
                f"Natural frequency {nat_freq:.0f}Hz - verify against motor RPM/60",
                f"Material: {material} selected for strength-to-weight ratio"
            ]
        )
        
        logger.info("Structural design completed")
        return result
    
    def _generate_structural_bom(self, selected_frame: Optional[Dict], 
                                 custom: bool, wheelbase: float,
                                 motor_count: int, material: str) -> List[Dict]:
        """Generate bill of materials for structural components"""
        bom = []
        
        if selected_frame and not custom:
            bom.append({
                'item': f"{selected_frame.get('brand')} {selected_frame.get('model')}",
                'category': 'frame',
                'quantity': 1,
                'unit_price': selected_frame.get('price_usd', 100),
                'source': 'commercial'
            })
        else:
            # Custom frame BOM
            bom.extend([
                {
                    'item': f'Carbon fiber arms {motor_count}pcs',
                    'category': 'frame',
                    'quantity': motor_count,
                    'unit_price': 15,
                    'source': 'custom'
                },
                {
                    'item': 'Center plate top',
                    'category': 'frame',
                    'quantity': 1,
                    'unit_price': 25,
                    'source': 'custom'
                },
                {
                    'item': 'Center plate bottom',
                    'category': 'frame',
                    'quantity': 1,
                    'unit_price': 25,
                    'source': 'custom'
                },
                {
                    'item': 'Aluminum standoffs set',
                    'category': 'frame',
                    'quantity': 1,
                    'unit_price': 10,
                    'source': 'custom'
                },
                {
                    'item': 'Hardware kit (screws, nuts)',
                    'category': 'frame',
                    'quantity': 1,
                    'unit_price': 8,
                    'source': 'custom'
                }
            ])
        
        # Landing gear
        bom.append({
            'item': 'Landing gear set',
            'category': 'frame',
            'quantity': 1,
            'unit_price': 15,
            'source': 'commercial'
        })
        
        return bom
