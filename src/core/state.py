"""
DroneForge AI - State Management
Defines the state schema for the drone design workflow.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum


class DroneType(str, Enum):
    """Supported drone types"""
    MULTIROTOR = "multirotor"
    FIXED_WING = "fixed_wing"
    VTOL = "vtol"
    HYBRID = "hybrid"


class MultirotorConfig(str, Enum):
    """Multirotor configurations"""
    TRICOPTER = "tricopter"
    QUADCOPTER_X = "quadcopter_x"
    QUADCOPTER_PLUS = "quadcopter_plus"
    QUADCOPTER_H = "quadcopter_h"
    HEXACOPTER_X = "hexacopter_x"
    HEXACOPTER_PLUS = "hexacopter_plus"
    OCTOCOPTER_X = "octocopter_x"
    OCTOCOPTER_PLUS = "octocopter_plus"
    OCTOCOPTER_COAX = "octocopter_coax"


class FixedWingConfig(str, Enum):
    """Fixed-wing configurations"""
    CONVENTIONAL = "conventional"
    FLYING_WING = "flying_wing"
    CANARD = "canard"
    BIPLANE = "biplane"
    DELTA = "delta"


class VTOLConfig(str, Enum):
    """VTOL configurations"""
    TILTROTOR_QUAD = "tiltrotor_quad"
    TILTROTOR_TRI = "tiltrotor_tri"
    TAILSITTER = "tailsitter"
    QUADPLANE = "quadplane"
    LIFT_CRUISE = "lift_cruise"


@dataclass
class MissionRequirements:
    """Parsed mission requirements"""
    # Basic info
    drone_type: DroneType = DroneType.MULTIROTOR
    configuration: str = "quadcopter_x"
    use_case: str = ""
    
    # Payload
    payload_mass_kg: float = 0.0
    payload_type: str = ""
    payload_dimensions_mm: List[float] = field(default_factory=list)
    payload_mounting: str = "bottom"
    
    # Performance
    endurance_min: float = 20.0
    range_km: float = 5.0
    max_speed_ms: float = 15.0
    cruise_speed_ms: float = 10.0
    max_altitude_m: float = 120.0
    wind_resistance_ms: float = 8.0
    
    # Environment
    temp_min_c: float = 0.0
    temp_max_c: float = 45.0
    humidity_percent: float = 70.0
    precipitation_resistant: bool = False
    
    # Budget
    max_cost: float = 100000.0
    currency: str = "INR"
    
    # Regulatory
    jurisdictions: List[str] = field(default_factory=lambda: ["india_dgca"])
    
    # Autonomy
    waypoint_navigation: bool = False
    obstacle_avoidance: bool = False
    return_to_home: bool = True
    geofencing: bool = True
    beyond_vlos: bool = False
    
    # CAD detail level
    cad_detail: Literal["basic", "detailed"] = "basic"
    
    # Assumptions made during parsing
    assumptions: List[str] = field(default_factory=list)


@dataclass
class PropulsionDesign:
    """Propulsion system design"""
    motors: List[Dict[str, Any]] = field(default_factory=list)
    propellers: List[Dict[str, Any]] = field(default_factory=list)
    escs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Calculated values
    motor_count: int = 4
    total_thrust_n: float = 0.0
    thrust_to_weight: float = 2.0
    max_power_draw_w: float = 0.0
    hover_throttle_percent: float = 50.0
    hover_current_a: float = 0.0
    efficiency_at_hover: float = 0.0
    
    # Calculations documentation
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class AerodynamicsAnalysis:
    """Aerodynamics analysis results"""
    # Drag
    drag_coefficient: float = 0.0
    frontal_area_m2: float = 0.0
    drag_force_at_cruise_n: float = 0.0
    
    # For fixed-wing
    lift_coefficient: float = 0.0
    wing_area_m2: float = 0.0
    aspect_ratio: float = 0.0
    stall_speed_ms: float = 0.0
    
    # Stability
    static_margin: float = 0.0
    cg_range_mm: List[float] = field(default_factory=list)
    
    # Wind
    max_wind_speed_ms: float = 0.0
    wind_penetration_capability: str = ""
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class StructuralDesign:
    """Structural design"""
    # Frame
    frame_type: str = ""
    frame_material: str = ""
    frame_weight_g: float = 0.0
    arm_length_mm: float = 0.0
    arm_diameter_mm: float = 0.0
    arm_wall_thickness_mm: float = 0.0
    wheelbase_mm: float = 0.0
    
    # Analysis
    max_bending_stress_mpa: float = 0.0
    safety_factor: float = 2.5
    natural_frequency_hz: float = 0.0
    
    # Landing gear
    landing_gear_type: str = ""
    landing_gear_material: str = ""
    landing_gear_height_mm: float = 0.0
    
    # Bill of materials for structure
    structural_bom: List[Dict[str, Any]] = field(default_factory=list)
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class PowerDesign:
    """Power system design"""
    # Battery
    battery: Dict[str, Any] = field(default_factory=dict)
    battery_count: int = 1
    total_capacity_mah: float = 0.0
    total_voltage_v: float = 0.0
    total_weight_g: float = 0.0
    total_energy_wh: float = 0.0
    
    # Power budget
    power_budget: Dict[str, float] = field(default_factory=dict)
    total_hover_power_w: float = 0.0
    total_max_power_w: float = 0.0
    
    # Flight time
    calculated_flight_time_min: float = 0.0
    reserve_time_min: float = 0.0
    usable_flight_time_min: float = 0.0
    
    # Voltage regulation
    bec_requirements: List[Dict[str, Any]] = field(default_factory=list)
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class ElectronicsDesign:
    """Electronics selection"""
    # Flight controller
    flight_controller: Dict[str, Any] = field(default_factory=dict)
    
    # GPS
    gps_module: Dict[str, Any] = field(default_factory=dict)
    
    # RC system
    receiver: Dict[str, Any] = field(default_factory=dict)
    transmitter_recommendation: str = ""
    
    # Telemetry
    telemetry_system: Dict[str, Any] = field(default_factory=dict)
    
    # Sensors
    additional_sensors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Companion computer (for autonomy)
    companion_computer: Optional[Dict[str, Any]] = None
    
    # LEDs and indicators
    led_system: Dict[str, Any] = field(default_factory=dict)
    
    # Power distribution
    pdb: Dict[str, Any] = field(default_factory=dict)
    
    # Total weight
    total_electronics_weight_g: float = 0.0
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass 
class CenterOfGravity:
    """Center of gravity analysis"""
    # Component masses and positions
    component_masses: List[Dict[str, Any]] = field(default_factory=list)
    
    # Calculated CG
    cg_x_mm: float = 0.0
    cg_y_mm: float = 0.0
    cg_z_mm: float = 0.0
    
    # Moments of inertia
    ixx_kg_m2: float = 0.0
    iyy_kg_m2: float = 0.0
    izz_kg_m2: float = 0.0
    
    # Total mass
    total_mass_kg: float = 0.0
    all_up_weight_kg: float = 0.0
    
    # CG tolerance
    cg_tolerance_mm: float = 5.0
    cg_within_tolerance: bool = True
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class AutonomyDesign:
    """Autonomous flight system design"""
    # Navigation
    navigation_system: str = ""  # GPS, RTK-GPS, Visual, etc.
    waypoint_capability: bool = False
    max_waypoints: int = 0
    
    # Obstacle avoidance
    obstacle_avoidance_type: str = ""  # None, Lidar, Stereo, ToF
    obstacle_sensors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Safety features
    return_to_home: bool = True
    rth_altitude_m: float = 50.0
    low_battery_rth_percent: float = 20.0
    signal_loss_behavior: str = "RTH"
    geofencing_enabled: bool = True
    
    # Mission planning
    supported_missions: List[str] = field(default_factory=list)
    ground_station_software: str = ""
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class SoftwareConfig:
    """Software and firmware configuration"""
    # Firmware
    firmware_type: str = ""  # Betaflight, INAV, ArduPilot, PX4
    firmware_version: str = ""
    
    # Configuration
    pid_values: Dict[str, List[float]] = field(default_factory=dict)
    rates: Dict[str, float] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    
    # Flight modes
    flight_modes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Failsafes
    failsafe_config: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration files (ready to upload)
    config_files: Dict[str, str] = field(default_factory=dict)
    
    justifications: List[str] = field(default_factory=list)


@dataclass
class WiringDesign:
    """Wiring and electrical integration"""
    # Wiring diagram (SVG or description)
    wiring_diagram_svg: str = ""
    
    # Wire specifications
    wires: List[Dict[str, Any]] = field(default_factory=list)
    wire_gauge_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Connectors
    connectors: List[Dict[str, Any]] = field(default_factory=list)
    connector_list: List[Dict[str, Any]] = field(default_factory=list)
    
    # Connection table
    connection_table: List[Dict[str, Any]] = field(default_factory=list)
    
    # EMI considerations
    emi_notes: List[str] = field(default_factory=list)
    
    calculations: Dict[str, Any] = field(default_factory=dict)
    justifications: List[str] = field(default_factory=list)


@dataclass
class CADDesign:
    """CAD model outputs"""
    # Detail level
    detail_level: str = "basic"
    
    # Frame parameters
    frame_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Generated files
    stl_files: List[str] = field(default_factory=list)
    step_files: List[str] = field(default_factory=list)
    dxf_files: List[str] = field(default_factory=list)
    
    # OpenSCAD/CadQuery code
    cad_code: str = ""
    
    # 3D printing recommendations
    print_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Assembly instructions
    assembly_notes: List[str] = field(default_factory=list)


@dataclass
class RegulatoryCompliance:
    """Regulatory compliance check"""
    # Checked jurisdictions
    jurisdictions_checked: List[str] = field(default_factory=list)
    
    # Compliance status per jurisdiction
    compliance_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Required registrations
    registrations_required: List[Dict[str, Any]] = field(default_factory=list)
    
    # Required equipment
    equipment_required: List[Dict[str, Any]] = field(default_factory=list)
    
    # Operational restrictions
    restrictions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Overall compliance
    fully_compliant: bool = False
    compliance_notes: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Validation agent results"""
    # Physics validation
    physics_valid: bool = True
    physics_issues: List[str] = field(default_factory=list)
    
    # Component compatibility
    compatibility_valid: bool = True
    compatibility_issues: List[str] = field(default_factory=list)
    
    # Safety margins
    safety_valid: bool = True
    safety_issues: List[str] = field(default_factory=list)
    
    # Regulatory compliance
    regulatory_valid: bool = True
    regulatory_issues: List[str] = field(default_factory=list)
    
    # Overall
    all_valid: bool = True
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Optimization results"""
    # Objectives
    optimized_weight_kg: float = 0.0
    optimized_cost: float = 0.0
    optimized_endurance_min: float = 0.0
    optimized_performance_score: float = 0.0
    
    # Trade-offs
    pareto_solutions: List[Dict[str, Any]] = field(default_factory=list)
    selected_solution: Dict[str, Any] = field(default_factory=dict)
    
    # Sensitivity
    sensitivity_analysis: Dict[str, Any] = field(default_factory=dict)
    
    # Notes
    optimization_notes: List[str] = field(default_factory=list)


@dataclass
class BillOfMaterials:
    """Complete bill of materials"""
    items: List[Dict[str, Any]] = field(default_factory=list)
    total_cost: float = 0.0
    currency: str = "INR"
    
    # Categorized
    by_category: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Purchase links
    purchase_summary: List[Dict[str, Any]] = field(default_factory=list)


class DroneDesignState(TypedDict, total=False):
    """
    Complete state for drone design workflow.
    This is the state passed between agents in the LangGraph workflow.
    """
    # Input
    mission_statement: str
    cad_detail_level: str
    
    # LLM configuration
    llm_provider: str
    llm_model: str
    
    # Parsed requirements
    mission_requirements: MissionRequirements
    
    # Design outputs from agents
    propulsion_design: PropulsionDesign
    aerodynamics_analysis: AerodynamicsAnalysis
    structural_design: StructuralDesign
    power_design: PowerDesign
    electronics_design: ElectronicsDesign
    cog_analysis: CenterOfGravity
    autonomy_design: AutonomyDesign
    software_config: SoftwareConfig
    wiring_design: WiringDesign
    cad_design: CADDesign
    regulatory_compliance: RegulatoryCompliance
    
    # Validation and optimization
    validation_result: ValidationResult
    optimization_result: OptimizationResult
    
    # Final outputs
    bill_of_materials: BillOfMaterials
    
    # Workflow control
    current_agent: str
    iteration: int
    errors: List[str]
    warnings: List[str]
    skip_agents: List[str]
    
    # Output paths
    output_directory: str


def create_initial_state(
    mission_statement: str,
    cad_detail: str = "basic",
    llm_provider: str = "ollama",
    llm_model: str = "llama3.1:70b",
    output_dir: str = "./output"
) -> DroneDesignState:
    """Create initial state for workflow"""
    return DroneDesignState(
        mission_statement=mission_statement,
        cad_detail_level=cad_detail,
        llm_provider=llm_provider,
        llm_model=llm_model,
        mission_requirements=MissionRequirements(cad_detail=cad_detail),
        propulsion_design=PropulsionDesign(),
        aerodynamics_analysis=AerodynamicsAnalysis(),
        structural_design=StructuralDesign(),
        power_design=PowerDesign(),
        electronics_design=ElectronicsDesign(),
        cog_analysis=CenterOfGravity(),
        autonomy_design=AutonomyDesign(),
        software_config=SoftwareConfig(),
        wiring_design=WiringDesign(),
        cad_design=CADDesign(detail_level=cad_detail),
        regulatory_compliance=RegulatoryCompliance(),
        validation_result=ValidationResult(),
        optimization_result=OptimizationResult(),
        bill_of_materials=BillOfMaterials(),
        current_agent="mission_analyzer",
        iteration=0,
        errors=[],
        warnings=[],
        skip_agents=[],
        output_directory=output_dir
    )
