"""
DroneForge AI - Center of Gravity Agent
Calculates CG position and moments of inertia.
"""

import json
import logging
import math
from typing import Dict, Any, List, Tuple
from dataclasses import asdict

logger = logging.getLogger(__name__)


class CogAgent:
    """Agent for center of gravity and moment of inertia calculations"""
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _get_motor_positions(self, config: str, wheelbase_mm: float, 
                            arm_length_mm: float) -> List[Tuple[float, float, float]]:
        """
        Calculate motor positions based on configuration.
        
        Returns:
            List of (x, y, z) positions in mm from geometric center
        """
        positions = []
        
        if 'quadcopter_x' in config:
            # Motors at 45° angles
            for i in range(4):
                angle = math.radians(45 + 90 * i)
                x = arm_length_mm * math.cos(angle)
                y = arm_length_mm * math.sin(angle)
                positions.append((x, y, 0))
        
        elif 'quadcopter_plus' in config:
            # Motors at 0°, 90°, 180°, 270°
            for i in range(4):
                angle = math.radians(90 * i)
                x = arm_length_mm * math.cos(angle)
                y = arm_length_mm * math.sin(angle)
                positions.append((x, y, 0))
        
        elif 'hexacopter_x' in config:
            # Motors at 60° intervals, rotated 30°
            for i in range(6):
                angle = math.radians(30 + 60 * i)
                x = arm_length_mm * math.cos(angle)
                y = arm_length_mm * math.sin(angle)
                positions.append((x, y, 0))
        
        elif 'octocopter_x' in config:
            # Motors at 45° intervals
            for i in range(8):
                angle = math.radians(22.5 + 45 * i)
                x = arm_length_mm * math.cos(angle)
                y = arm_length_mm * math.sin(angle)
                positions.append((x, y, 0))
        
        else:
            # Default to quad X
            for i in range(4):
                angle = math.radians(45 + 90 * i)
                x = arm_length_mm * math.cos(angle)
                y = arm_length_mm * math.sin(angle)
                positions.append((x, y, 0))
        
        return positions
    
    def _calculate_cg(self, components: List[Dict]) -> Tuple[float, float, float]:
        """
        Calculate center of gravity from component list.
        
        Each component should have: mass_g, x_mm, y_mm, z_mm
        
        Returns:
            (cg_x, cg_y, cg_z) in mm
        """
        total_mass = 0
        moment_x = 0
        moment_y = 0
        moment_z = 0
        
        for comp in components:
            mass = comp.get('mass_g', 0)
            x = comp.get('x_mm', 0)
            y = comp.get('y_mm', 0)
            z = comp.get('z_mm', 0)
            
            total_mass += mass
            moment_x += mass * x
            moment_y += mass * y
            moment_z += mass * z
        
        if total_mass > 0:
            cg_x = moment_x / total_mass
            cg_y = moment_y / total_mass
            cg_z = moment_z / total_mass
        else:
            cg_x = cg_y = cg_z = 0
        
        return (cg_x, cg_y, cg_z)
    
    def _calculate_moments_of_inertia(self, components: List[Dict], 
                                      cg: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Calculate moments of inertia about CG.
        Uses point mass approximation: I = Σ m × r²
        
        Returns:
            (Ixx, Iyy, Izz) in kg⋅m²
        """
        Ixx = 0  # Rotation about X axis (roll)
        Iyy = 0  # Rotation about Y axis (pitch)
        Izz = 0  # Rotation about Z axis (yaw)
        
        cg_x, cg_y, cg_z = cg
        
        for comp in components:
            mass_kg = comp.get('mass_g', 0) / 1000
            x = (comp.get('x_mm', 0) - cg_x) / 1000  # m from CG
            y = (comp.get('y_mm', 0) - cg_y) / 1000
            z = (comp.get('z_mm', 0) - cg_z) / 1000
            
            # Point mass MOI: I = m × r² where r is perpendicular distance from axis
            Ixx += mass_kg * (y**2 + z**2)
            Iyy += mass_kg * (x**2 + z**2)
            Izz += mass_kg * (x**2 + y**2)
        
        return (Ixx, Iyy, Izz)
    
    def _build_component_list(self, state: Dict[str, Any]) -> List[Dict]:
        """Build list of components with masses and positions"""
        components = []
        
        mission_req = state.get('mission_requirements', {})
        if hasattr(mission_req, '__dict__'):
            mission_req = asdict(mission_req)
        
        propulsion = state.get('propulsion_design', {})
        structural = state.get('structural_design', {})
        power = state.get('power_design', {})
        electronics = state.get('electronics_design', {})
        
        config = mission_req.get('configuration', 'quadcopter_x')
        wheelbase = structural.get('wheelbase_mm', 500)
        arm_length = structural.get('arm_length_mm', 200)
        
        # Motor positions
        motor_positions = self._get_motor_positions(config, wheelbase, arm_length)
        motor_count = propulsion.get('motor_count', 4)
        motors = propulsion.get('motors', [{}])
        motor_weight = motors[0].get('specs', {}).get('weight_g', 80) if motors else 80
        
        for i, pos in enumerate(motor_positions[:motor_count]):
            components.append({
                'name': f'Motor {i+1}',
                'mass_g': motor_weight,
                'x_mm': pos[0],
                'y_mm': pos[1],
                'z_mm': 20  # Above center plate
            })
            
            # Propeller (at motor position, slightly above)
            props = propulsion.get('propellers', [{}])
            prop_weight = props[0].get('weight_g', 25) if props else 25
            components.append({
                'name': f'Propeller {i+1}',
                'mass_g': prop_weight,
                'x_mm': pos[0],
                'y_mm': pos[1],
                'z_mm': 30
            })
            
            # ESC (along arm or on center)
            escs = propulsion.get('escs', [{}])
            esc_weight = escs[0].get('specs', {}).get('weight_g', 30) if escs else 30
            components.append({
                'name': f'ESC {i+1}',
                'mass_g': esc_weight,
                'x_mm': pos[0] * 0.5,  # Halfway along arm
                'y_mm': pos[1] * 0.5,
                'z_mm': 0
            })
        
        # Center stack components
        # Frame
        frame_weight = structural.get('frame_weight_g', 400)
        components.append({
            'name': 'Frame (center)',
            'mass_g': frame_weight * 0.4,  # 40% at center
            'x_mm': 0,
            'y_mm': 0,
            'z_mm': 0
        })
        
        # Flight Controller
        fc = electronics.get('flight_controller', {})
        fc_weight = fc.get('specs', {}).get('weight_g', 50)
        components.append({
            'name': 'Flight Controller',
            'mass_g': fc_weight,
            'x_mm': 0,
            'y_mm': 0,
            'z_mm': 15
        })
        
        # GPS (typically on mast, above center)
        gps = electronics.get('gps_module', {})
        gps_weight = gps.get('specs', {}).get('weight_g', 35)
        components.append({
            'name': 'GPS Module',
            'mass_g': gps_weight,
            'x_mm': 0,
            'y_mm': -30,  # Slightly behind center
            'z_mm': 80  # On mast
        })
        
        # Battery (largest mass, position is critical)
        battery_weight = power.get('total_weight_g', 500)
        components.append({
            'name': 'Battery',
            'mass_g': battery_weight,
            'x_mm': 0,  # Centered for balance
            'y_mm': 0,
            'z_mm': -30  # Below center plate
        })
        
        # Receiver
        rx = electronics.get('receiver', {})
        rx_weight = rx.get('specs', {}).get('weight_g', 5)
        components.append({
            'name': 'Receiver',
            'mass_g': rx_weight,
            'x_mm': 10,
            'y_mm': -20,
            'z_mm': 10
        })
        
        # Telemetry
        telem = electronics.get('telemetry_system', {})
        telem_weight = telem.get('specs', {}).get('weight_g', 25)
        components.append({
            'name': 'Telemetry Radio',
            'mass_g': telem_weight,
            'x_mm': -10,
            'y_mm': -25,
            'z_mm': 10
        })
        
        # Power Distribution
        pdb = electronics.get('pdb', {})
        pdb_weight = pdb.get('specs', {}).get('weight_g', 30)
        components.append({
            'name': 'PDB',
            'mass_g': pdb_weight,
            'x_mm': 0,
            'y_mm': 0,
            'z_mm': -5
        })
        
        # Payload
        payload_mass = mission_req.get('payload_mass_kg', 0) * 1000
        if payload_mass > 0:
            payload_mounting = mission_req.get('payload_mounting', 'bottom')
            if payload_mounting == 'bottom':
                payload_z = -60
            elif payload_mounting == 'front':
                payload_z = -20
            else:
                payload_z = -30
            
            components.append({
                'name': 'Payload',
                'mass_g': payload_mass,
                'x_mm': 0 if payload_mounting != 'front' else 50,
                'y_mm': 0,
                'z_mm': payload_z
            })
        
        # Landing gear
        lg_weight = 50 + payload_mass * 0.05
        components.append({
            'name': 'Landing Gear',
            'mass_g': lg_weight,
            'x_mm': 0,
            'y_mm': 0,
            'z_mm': -50
        })
        
        # Wiring harness (distributed)
        wiring_weight = 50 + motor_count * 10
        components.append({
            'name': 'Wiring',
            'mass_g': wiring_weight,
            'x_mm': 0,
            'y_mm': 0,
            'z_mm': 0
        })
        
        return components
    
    def _check_cg_tolerance(self, cg: Tuple[float, float, float], 
                           tolerance_mm: float = 10) -> Dict:
        """Check if CG is within acceptable tolerance from center"""
        cg_x, cg_y, cg_z = cg
        
        horizontal_offset = math.sqrt(cg_x**2 + cg_y**2)
        
        return {
            'cg_x_mm': round(cg_x, 1),
            'cg_y_mm': round(cg_y, 1),
            'cg_z_mm': round(cg_z, 1),
            'horizontal_offset_mm': round(horizontal_offset, 1),
            'within_tolerance': horizontal_offset <= tolerance_mm,
            'tolerance_mm': tolerance_mm,
            'recommendations': self._get_balance_recommendations(cg_x, cg_y)
        }
    
    def _get_balance_recommendations(self, cg_x: float, cg_y: float) -> List[str]:
        """Generate recommendations for balancing if CG is off-center"""
        recommendations = []
        threshold = 5  # mm
        
        if abs(cg_x) > threshold:
            direction = 'backward' if cg_x > 0 else 'forward'
            recommendations.append(f"Move battery {direction} by {abs(cg_x):.0f}mm to center CG")
        
        if abs(cg_y) > threshold:
            direction = 'right' if cg_y > 0 else 'left'
            recommendations.append(f"Adjust component placement {direction} by {abs(cg_y):.0f}mm")
        
        if not recommendations:
            recommendations.append("CG is well centered, no adjustments needed")
        
        return recommendations
    
    def analyze(self, propulsion: Any, structure: Any, power: Any, electronics: Any, requirements: Any) -> Any:
        """
        Analyze center of gravity.
        
        Args:
            propulsion: Propulsion design
            structure: Structural design
            power: Power design
            electronics: Electronics design
            requirements: Mission requirements
            
        Returns:
            CenterOfGravity dataclass
        """
        logger.info("Starting center of gravity analysis")
        
        # Build state dict for internal use
        state = {
            'propulsion_design': asdict(propulsion) if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict) else propulsion,
            'structural_design': asdict(structure) if hasattr(structure, '__dict__') and not isinstance(structure, dict) else structure,
            'power_design': asdict(power) if hasattr(power, '__dict__') and not isinstance(power, dict) else power,
            'electronics_design': asdict(electronics) if hasattr(electronics, '__dict__') and not isinstance(electronics, dict) else electronics,
            'mission_requirements': asdict(requirements) if hasattr(requirements, '__dict__') and not isinstance(requirements, dict) else requirements,
        }
        
        # Build component list
        components = self._build_component_list(state)
        
        # Calculate CG
        cg = self._calculate_cg(components)
        
        # Calculate moments of inertia
        moi = self._calculate_moments_of_inertia(components, cg)
        
        # Calculate total mass
        total_mass_g = sum(c.get('mass_g', 0) for c in components)
        
        # Check tolerance
        cg_check = self._check_cg_tolerance(cg)
        
        # Build result
        from ..core.state import CenterOfGravity
        
        result = CenterOfGravity(
            cg_x_mm=round(cg[0], 2),
            cg_y_mm=round(cg[1], 2),
            cg_z_mm=round(cg[2], 2),
            ixx_kg_m2=round(moi[0], 6),
            iyy_kg_m2=round(moi[1], 6),
            izz_kg_m2=round(moi[2], 6),
            total_mass_kg=round(total_mass_g / 1000, 3),
            cg_within_tolerance=cg_check['within_tolerance'],
            calculations={
                'component_count': len(components),
                'horizontal_cg_offset_mm': cg_check['horizontal_offset_mm'],
                'cg_tolerance_mm': 10,
                'component_masses': components,
            },
            justifications=[
                f"Total mass: {total_mass_g/1000:.2f} kg from {len(components)} components",
                f"CG position: ({cg[0]:.1f}, {cg[1]:.1f}, {cg[2]:.1f}) mm",
                f"CG offset from center: {cg_check['horizontal_offset_mm']:.1f} mm",
                *cg_check['recommendations']
            ]
        )
        
        logger.info("Center of gravity analysis completed")
        return result
