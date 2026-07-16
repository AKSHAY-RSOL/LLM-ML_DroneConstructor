"""
DroneForge AI - CAD Generation Agent
Generates CAD models and 3D printable files.
"""

import json
import logging
import math
from typing import Dict, Any, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class CADAgent:
    """Agent for CAD model generation"""
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _generate_frame_parameters(self, state: Dict[str, Any]) -> Dict:
        """Generate frame parameters for CAD"""
        structural = state.get('structural_design', {})
        propulsion = state.get('propulsion_design', {})
        mission_req = state.get('mission_requirements', {})
        
        if hasattr(mission_req, '__dict__'):
            mission_req = asdict(mission_req)
        
        config = mission_req.get('configuration', 'quadcopter_x')
        motor_count = propulsion.get('motor_count', 4)
        
        # Get structural dimensions
        wheelbase = structural.get('wheelbase_mm', 500)
        arm_length = structural.get('arm_length_mm', 200)
        arm_diameter = structural.get('arm_diameter_mm', 16)
        arm_wall = structural.get('arm_wall_thickness_mm', 1.5)
        
        # Motor mount pattern
        motors = propulsion.get('motors', [{}])
        if motors:
            motor_specs = motors[0].get('specs', {})
            motor_mount = motor_specs.get('mounting_pattern_mm', 16)
        else:
            motor_mount = 16
        
        # Propeller size for arm spacing
        props = propulsion.get('propellers', [{}])
        prop_size = props[0].get('size_inch', 10) if props else 10
        prop_diameter_mm = prop_size * 25.4
        
        # Center plate dimensions
        if motor_count <= 4:
            center_size = 100
        elif motor_count <= 6:
            center_size = 140
        else:
            center_size = 180
        
        return {
            'configuration': config,
            'motor_count': motor_count,
            'wheelbase_mm': wheelbase,
            'arm_length_mm': arm_length,
            'arm_outer_diameter_mm': arm_diameter,
            'arm_inner_diameter_mm': arm_diameter - 2 * arm_wall,
            'arm_wall_thickness_mm': arm_wall,
            'center_plate_width_mm': center_size,
            'center_plate_length_mm': center_size * 1.2,
            'center_plate_thickness_mm': 3,
            'motor_mount_pattern_mm': motor_mount,
            'prop_diameter_mm': prop_diameter_mm,
            'motor_angle_offset_deg': 45 if 'x' in config.lower() else 0,
            'arm_angles_deg': self._calculate_arm_angles(motor_count, config),
            'landing_gear_height_mm': structural.get('landing_gear_height_mm', 80),
            'battery_mount_length_mm': 150,
            'battery_mount_width_mm': 50
        }
    
    def _calculate_arm_angles(self, motor_count: int, config: str) -> List[float]:
        """Calculate arm angles for each motor"""
        angles = []
        
        if 'x' in config.lower():
            base_angle = 45
        else:
            base_angle = 0
        
        angle_step = 360 / motor_count
        
        for i in range(motor_count):
            angles.append(base_angle + i * angle_step)
        
        return angles
    
    def _generate_openscad_code(self, params: Dict, detail: str) -> str:
        """Generate OpenSCAD code for the drone frame"""
        code = '''// DroneForge AI Generated OpenSCAD Model
// Configuration: {config}
// Generated automatically - may need manual adjustments

// Parameters
wheelbase = {wheelbase};
arm_length = {arm_length};
arm_od = {arm_od};
arm_id = {arm_id};
center_width = {center_width};
center_length = {center_length};
center_thickness = {center_thickness};
motor_mount = {motor_mount};
motor_count = {motor_count};
arm_angles = {arm_angles};
landing_gear_height = {lg_height};

// Modules
module arm() {{
    difference() {{
        cylinder(h=arm_length, d=arm_od, center=false, $fn=32);
        translate([0, 0, -1])
            cylinder(h=arm_length+2, d=arm_id, center=false, $fn=32);
    }}
}}

module motor_mount() {{
    difference() {{
        cylinder(h=5, d=arm_od+10, $fn=32);
        // Mounting holes
        for(a = [0, 90, 180, 270]) {{
            rotate([0, 0, a])
                translate([motor_mount/2, 0, -1])
                    cylinder(h=7, d=3, $fn=16);
        }}
    }}
}}

module center_plate() {{
    difference() {{
        // Main plate
        hull() {{
            translate([center_length/2-10, center_width/2-10, 0])
                cylinder(h=center_thickness, r=10, $fn=32);
            translate([-center_length/2+10, center_width/2-10, 0])
                cylinder(h=center_thickness, r=10, $fn=32);
            translate([center_length/2-10, -center_width/2+10, 0])
                cylinder(h=center_thickness, r=10, $fn=32);
            translate([-center_length/2+10, -center_width/2+10, 0])
                cylinder(h=center_thickness, r=10, $fn=32);
        }}
        
        // Arm slots
        for(i = [0:motor_count-1]) {{
            rotate([0, 0, arm_angles[i]])
                translate([center_width/2-5, 0, -1])
                    cylinder(h=center_thickness+2, d=arm_od+0.5, $fn=32);
        }}
        
        // Center hole
        translate([0, 0, -1])
            cylinder(h=center_thickness+2, d=30, $fn=32);
        
        // Mounting holes for FC
        for(x = [-15, 15]) {{
            for(y = [-15, 15]) {{
                translate([x, y, -1])
                    cylinder(h=center_thickness+2, d=3, $fn=16);
            }}
        }}
    }}
}}

module landing_gear_leg() {{
    difference() {{
        union() {{
            // Vertical leg
            cylinder(h=landing_gear_height, d=10, $fn=16);
            // Foot
            translate([0, 0, 0])
                sphere(d=15, $fn=16);
        }}
        translate([0, 0, landing_gear_height])
            sphere(d=10, $fn=16);
    }}
}}

module drone_frame() {{
    // Center plates
    center_plate();
    translate([0, 0, 25])
        center_plate();
    
    // Arms
    for(i = [0:motor_count-1]) {{
        rotate([0, 0, arm_angles[i]])
            translate([0, 0, center_thickness])
                rotate([0, 90, 0])
                    arm();
    }}
    
    // Motor mounts
    for(i = [0:motor_count-1]) {{
        rotate([0, 0, arm_angles[i]])
            translate([arm_length, 0, center_thickness])
                motor_mount();
    }}
    
    // Landing gear
    for(a = [45, 135, 225, 315]) {{
        rotate([0, 0, a])
            translate([center_width/2 * 0.7, 0, 0])
                rotate([180, 0, 0])
                    landing_gear_leg();
    }}
}}

// Render
drone_frame();
'''.format(
            config=params['configuration'],
            wheelbase=params['wheelbase_mm'],
            arm_length=params['arm_length_mm'],
            arm_od=params['arm_outer_diameter_mm'],
            arm_id=params['arm_inner_diameter_mm'],
            center_width=params['center_plate_width_mm'],
            center_length=params['center_plate_length_mm'],
            center_thickness=params['center_plate_thickness_mm'],
            motor_mount=params['motor_mount_pattern_mm'],
            motor_count=params['motor_count'],
            arm_angles=str(params['arm_angles_deg']),
            lg_height=params['landing_gear_height_mm']
        )
        
        return code
    
    def _generate_cadquery_code(self, params: Dict, detail: str) -> str:
        """Generate CadQuery code for the drone frame (BUG-048 / BUG-049)"""
        config_lower = params.get('configuration', 'quadcopter_x').lower()
        is_fixed_wing = 'flying_wing' in config_lower or 'conventional' in config_lower or 'delta' in config_lower or 'canard' in config_lower or 'biplane' in config_lower
        is_vtol = 'quadplane' in config_lower or 'tailsitter' in config_lower or 'tiltrotor' in config_lower or 'lift_cruise' in config_lower
        
        if is_fixed_wing or is_vtol:
            wingspan = params.get('wheelbase_mm', 1400)
            fuselage_length = wingspan * 0.7
            wing_chord = wingspan * 0.15
            wing_thickness = 15
            motor_count = params.get('motor_count', 1)
            
            accessories_code = ""
            render_accessories = ""
            if detail == "detailed":
                accessories_code = """
def create_flight_controller():
    return cq.Workplane("XY").workplane(offset=15).box(35, 35, 10)

def create_battery_pack():
    return cq.Workplane("XY").workplane(offset=-5).box(80, 30, 20)
"""
                render_accessories = """
    # Flight controller and battery
    fc = create_flight_controller()
    frame.add(fc, name="flight_controller")
    bat = create_battery_pack()
    frame.add(bat, name="battery")
"""
            
            code = f'''# DroneForge AI Generated CadQuery Model
# Configuration: {params['configuration']}
# Type: Fixed-Wing/VTOL Airframe (BUG-048 / BUG-049)

import cadquery as cq
import math

# Parameters
wingspan = {wingspan}
fuselage_length = {fuselage_length}
wing_chord = {wing_chord}
wing_thickness = {wing_thickness}
motor_count = {motor_count}

def create_fuselage():
    return (cq.Workplane("YZ")
        .cylinder(fuselage_length, wingspan*0.08/2)
    )

def create_wing():
    return (cq.Workplane("XY")
        .box(wingspan, wing_chord, wing_thickness)
    )

def create_tail():
    # Vertical stabilizer
    vert = (cq.Workplane("XZ")
        .workplane(offset=-fuselage_length/2 + 50)
        .box(5, wing_chord*0.6, wingspan*0.2)
        .translate(cq.Vector(0, 0, wingspan*0.1))
    )
    # Horizontal stabilizer
    horiz = (cq.Workplane("XY")
        .workplane(offset=-fuselage_length/2 + 50)
        .box(wingspan*0.3, wing_chord*0.5, 5)
    )
    return vert.union(horiz)
{accessories_code}
def create_frame():
    frame = cq.Assembly()
    
    fuse = create_fuselage()
    frame.add(fuse, name="fuselage")
    
    wing = create_wing()
    wing_pos = cq.Location(cq.Vector(0, fuselage_length*0.1, 0))
    frame.add(wing, name="wing", loc=wing_pos)
    
    tail = create_tail()
    frame.add(tail, name="tail")
    
    if motor_count > 0:
        for i in range(motor_count):
            if motor_count == 1:
                # Nose motor
                motor = cq.Workplane("YZ").cylinder(20, (wingspan*0.04)/2)
                motor_pos = cq.Location(cq.Vector(0, fuselage_length/2, 0))
                frame.add(motor, name=f"motor_{{i+1}}", loc=motor_pos)
            else:
                # Wing motors
                offset = (1 if i % 2 == 0 else -1) * (wingspan * 0.25) * (1 + (0.3 if i > 1 else 0))
                motor = cq.Workplane("YZ").cylinder(30, (wingspan*0.03)/2)
                motor_pos = cq.Location(cq.Vector(offset, fuselage_length*0.1, 0))
                frame.add(motor, name=f"motor_{{i+1}}", loc=motor_pos)
    {render_accessories}
    return frame

if __name__ == "__main__":
    frame = create_frame()
    show_object(frame)
'''
            return code

        # Multirotor standard layout
        accessories_code = ""
        render_accessories = ""
        if detail == "detailed":
            accessories_code = """
def create_flight_controller():
    return cq.Workplane("XY").workplane(offset=10).box(35, 35, 10)

def create_battery_pack():
    return cq.Workplane("XY").workplane(offset=-20).box(135, 45, 35)
"""
            render_accessories = """
    # Flight controller and battery
    fc = create_flight_controller()
    frame.add(fc, name="flight_controller")
    bat = create_battery_pack()
    frame.add(bat, name="battery")
"""
            
        code = '''# DroneForge AI Generated CadQuery Model
# Configuration: {config}
# Detail Level: {detail} (BUG-049)

import cadquery as cq
import math

# Parameters
wheelbase = {wheelbase}
arm_length = {arm_length}
arm_od = {arm_od}
arm_id = {arm_id}
center_width = {center_width}
center_length = {center_length}
center_thickness = {center_thickness}
motor_mount = {motor_mount}
motor_count = {motor_count}
arm_angles = {arm_angles}
landing_gear_height = {lg_height}

def create_arm():
    """Create a single arm as hollow tube"""
    outer = cq.Workplane("XY").cylinder(arm_length, arm_od/2)
    inner = cq.Workplane("XY").cylinder(arm_length, arm_id/2)
    return outer.cut(inner)

def create_motor_mount():
    """Create motor mount plate"""
    mount = (cq.Workplane("XY")
        .cylinder(5, (arm_od + 10)/2)
    )
    
    # Add mounting holes
    for angle in [0, 90, 180, 270]:
        rad = math.radians(angle)
        x = (motor_mount/2) * math.cos(rad)
        y = (motor_mount/2) * math.sin(rad)
        mount = mount.faces(">Z").workplane().pushPoints([(x, y)]).hole(3)
    
    return mount

def create_center_plate():
    """Create center mounting plate"""
    plate = (cq.Workplane("XY")
        .box(center_length, center_width, center_thickness)
        .edges("|Z").fillet(10)
    )
    
    # FC mounting holes
    holes = [(15, 15), (-15, 15), (15, -15), (-15, -15)]
    for x, y in holes:
        plate = plate.faces(">Z").workplane().pushPoints([(x, y)]).hole(3)
    
    # Center hole
    plate = plate.faces(">Z").workplane().hole(30)
    
    return plate

def create_landing_gear_leg():
    """Create landing gear leg"""
    leg = cq.Workplane("XY").cylinder(landing_gear_height, 5)
    foot = cq.Workplane("XY").sphere(7.5)
    return leg.union(foot)
{accessories_code}
def create_frame():
    """Assemble complete frame"""
    frame = cq.Assembly()
    
    # Bottom plate
    bottom_plate = create_center_plate()
    frame.add(bottom_plate, name="bottom_plate")
    
    # Top plate
    top_plate = create_center_plate()
    frame.add(top_plate, name="top_plate", 
              loc=cq.Location(cq.Vector(0, 0, 25)))
    
    # Arms and motor mounts
    for i, angle in enumerate(arm_angles):
        rad = math.radians(angle)
        arm = create_arm()
        
        # Position arm
        arm_pos = cq.Location(
            cq.Vector(arm_length/2 * math.cos(rad), 
                     arm_length/2 * math.sin(rad), 
                     center_thickness),
            cq.Vector(0, 1, 0), 90 - angle
        )
        frame.add(arm, name=f"arm_{{i+1}}", loc=arm_pos)
        
        # Motor mount
        mount = create_motor_mount()
        mount_x = arm_length * math.cos(rad)
        mount_y = arm_length * math.sin(rad)
        mount_pos = cq.Location(cq.Vector(mount_x, mount_y, center_thickness))
        frame.add(mount, name=f"motor_mount_{{i+1}}", loc=mount_pos)
        
    # Landing gear
    for i, angle in enumerate([45, 135, 225, 315]):
        rad = math.radians(angle)
        leg = create_landing_gear_leg()
        leg_x = (center_width/2 * 0.7) * math.cos(rad)
        leg_y = (center_width/2 * 0.7) * math.sin(rad)
        leg_pos = cq.Location(
            cq.Vector(leg_x, leg_y, 0),
            cq.Vector(1, 0, 0), 180
        )
        frame.add(leg, name=f"landing_gear_{{i+1}}", loc=leg_pos)
    {render_accessories}
    return frame

# Create and export
if __name__ == "__main__":
    frame = create_frame()
    show_object(frame)
'''.format(
            config=params['configuration'],
            detail=detail,
            accessories_code=accessories_code,
            render_accessories=render_accessories,
            wheelbase=params['wheelbase_mm'],
            arm_length=params['arm_length_mm'],
            arm_od=params['arm_outer_diameter_mm'],
            arm_id=params['arm_inner_diameter_mm'],
            center_width=params['center_plate_width_mm'],
            center_length=params['center_plate_length_mm'],
            center_thickness=params['center_plate_thickness_mm'],
            motor_mount=params['motor_mount_pattern_mm'],
            motor_count=params['motor_count'],
            arm_angles=str(params['arm_angles_deg']),
            lg_height=params['landing_gear_height_mm']
        )
        
        return code
    
    def _get_print_settings(self, material: str) -> Dict:
        """Get recommended 3D print settings"""
        settings = {
            'carbon_fiber': {
                'material': 'Carbon Fiber PETG or Nylon',
                'nozzle_temp_c': 260,
                'bed_temp_c': 90,
                'layer_height_mm': 0.2,
                'infill_percent': 50,
                'wall_count': 4,
                'supports': 'tree',
                'notes': 'Use hardened steel nozzle for carbon fiber filaments'
            },
            'abs_plastic': {
                'material': 'ABS',
                'nozzle_temp_c': 245,
                'bed_temp_c': 100,
                'layer_height_mm': 0.2,
                'infill_percent': 40,
                'wall_count': 3,
                'supports': 'normal',
                'notes': 'Ensure enclosure to prevent warping'
            },
            'tpu': {
                'material': 'TPU 95A',
                'nozzle_temp_c': 230,
                'bed_temp_c': 50,
                'layer_height_mm': 0.2,
                'infill_percent': 30,
                'wall_count': 2,
                'supports': 'minimal',
                'notes': 'Reduce print speed for flexible parts'
            },
            'default': {
                'material': 'PETG',
                'nozzle_temp_c': 240,
                'bed_temp_c': 80,
                'layer_height_mm': 0.2,
                'infill_percent': 40,
                'wall_count': 3,
                'supports': 'tree',
                'notes': 'Good balance of strength and ease of printing'
            }
        }
        
        return settings.get(material.lower(), settings['default'])
    
    def _generate_assembly_notes(self, params: Dict) -> List[str]:
        """Generate assembly instructions"""
        notes = [
            "Assembly Instructions:",
            "",
            "1. FRAME ASSEMBLY:",
            f"   - Slide arms through center plate slots at {params['arm_angles_deg']} degree angles",
            "   - Secure arms with arm clamps or adhesive",
            "   - Attach motor mounts to arm ends",
            "",
            "2. ELECTRONICS MOUNTING:",
            "   - Mount flight controller on center plate using vibration damping",
            "   - Install PDB below FC with standoffs",
            "   - Route all wires before final assembly",
            "",
            "3. MOTOR INSTALLATION:",
            f"   - Mount motors using {params['motor_mount_pattern_mm']}mm bolt pattern",
            "   - Ensure correct motor rotation direction:",
            "     * Front-left and rear-right: CCW",
            "     * Front-right and rear-left: CW",
            "",
            "4. PROPELLER INSTALLATION:",
            f"   - Propeller diameter: {params['prop_diameter_mm']:.0f}mm",
            "   - Match CW/CCW props to motor rotation",
            "   - Tighten prop nuts securely",
            "",
            "5. LANDING GEAR:",
            f"   - Attach landing gear ({params['landing_gear_height_mm']}mm height)",
            "   - Ensure clearance for battery and payload",
            "",
            "6. FINAL CHECKS:",
            "   - Verify all screws are tight",
            "   - Check propeller clearance",
            "   - Balance the drone with battery installed",
            "   - Verify CG is centered"
        ]
        
        return notes
    
    def generate(self, requirements: Any, structure: Any, propulsion: Any, detail_level: str = 'basic') -> Any:
        """
        Generate CAD models.
        
        Args:
            requirements: Mission requirements
            structure: Structural design
            propulsion: Propulsion design
            detail_level: CAD detail level
            
        Returns:
            CADDesign dataclass
        """
        logger.info("Starting CAD generation")
        
        # Convert dataclasses to dicts
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(structure, '__dict__') and not isinstance(structure, dict):
            structural = asdict(structure)
        else:
            structural = structure if isinstance(structure, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion_dict = asdict(propulsion)
        else:
            propulsion_dict = propulsion if isinstance(propulsion, dict) else {}
        
        detail_level = detail_level or mission_req.get('cad_detail', 'basic')
        material = structural.get('frame_material', 'carbon_fiber')
        
        # Build internal state for helper methods
        state = {
            'mission_requirements': mission_req,
            'structural_design': structural,
            'propulsion_design': propulsion_dict
        }
        
        # Generate frame parameters
        params = self._generate_frame_parameters(state)
        
        # Generate CAD code
        openscad_code = self._generate_openscad_code(params, detail_level)
        cadquery_code = self._generate_cadquery_code(params, detail_level)
        
        # Get print settings
        print_settings = self._get_print_settings(material)
        
        # Generate assembly notes
        assembly_notes = self._generate_assembly_notes(params)
        
        # Build CAD design result
        from ..core.state import CADDesign
        
        result = CADDesign(
            detail_level=detail_level,
            frame_parameters=params,
            stl_files=[],
            step_files=[],
            dxf_files=[],
            cad_code={'openscad': openscad_code, 'cadquery': cadquery_code},
            print_settings=print_settings,
            assembly_notes=assembly_notes
        )
        
        logger.info("CAD generation completed")
        return result
