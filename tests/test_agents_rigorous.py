import pytest
import math
from unittest.mock import MagicMock

from src.core.state import (
    MissionRequirements,
    PropulsionDesign,
    AerodynamicsAnalysis,
    StructuralDesign,
    PowerDesign,
    ElectronicsDesign,
    CenterOfGravity,
    AutonomyDesign,
    SoftwareConfig,
    RegulatoryCompliance
)
from src.agents.aerodynamics_agent import AerodynamicsAgent
from src.agents.structural_agent import StructuralAgent
from src.agents.cog_agent import CogAgent
from src.agents.power_agent import PowerAgent
from src.agents.regulatory_agent import RegulatoryAgent
from src.agents.validator_agent import ValidatorAgent
from src.agents.software_agent import SoftwareAgent


@pytest.fixture
def mock_llm():
    return MagicMock()


# =====================================================================
# 1. Aerodynamics Agent Physical Equations
# =====================================================================
def test_aerodynamics_physical_equations(mock_llm):
    agent = AerodynamicsAgent(mock_llm)
    
    # Air density at sea level (0m) and 15C (standard day) should be close to 1.225 kg/m3
    density_0 = agent._calculate_air_density(0, 15)
    assert pytest.approx(density_0, abs=0.01) == 1.225
    
    # Air density at higher altitude should be lower
    density_1000 = agent._calculate_air_density(1000, 20)
    assert density_1000 < density_0
    
    # Frontal area estimation
    area_quad = agent._estimate_frontal_area('quadcopter_x', 500)
    # Area = pi * (0.25)^2 * 0.15 = 3.14159 * 0.0625 * 0.15 = 0.02945
    assert pytest.approx(area_quad, abs=0.001) == 0.02945
    
    # Drag force equation: Fd = 0.5 * rho * V^2 * Cd * A
    # rho = 1.2, V = 10, Cd = 0.8, A = 0.03
    # Fd = 0.5 * 1.2 * 100 * 0.8 * 0.03 = 1.44 N
    fd = agent._calculate_drag_force(cd=0.8, area_m2=0.03, velocity_ms=10.0, density=1.2)
    assert pytest.approx(fd, abs=0.01) == 1.44
    
    # Wind penetration: V_wind = sqrt(2 * horizontal_thrust / (rho * Cd * A)) (BUG-061)
    # horizontal_thrust = sqrt(available_thrust^2 - weight^2) = sqrt(50^2 - 20^2) = sqrt(2100) = 45.83 N
    # Denominator = rho * Cd * A = 1.2 * 0.8 * 0.03 = 0.0288
    # V = sqrt(2 * 45.83 / 0.0288) = sqrt(3182.34) = 56.41 m/s
    v_wind = agent._calculate_wind_penetration(available_thrust_n=50.0, weight_n=20.0, cd=0.8, area_m2=0.03, density=1.2)
    assert pytest.approx(v_wind, abs=0.01) == 56.41


# =====================================================================
# 2. Structural Agent Mechanics Equations
# =====================================================================
def test_structural_mechanics_equations(mock_llm):
    agent = StructuralAgent(mock_llm)
    
    # Arm length
    # Wheelbase = 500mm, X config. arm_length = 500 / (2 * cos(45)) = 353.55
    arm_x = agent._calculate_arm_length(500, 'quadcopter_x')
    assert pytest.approx(arm_x, abs=0.1) == 353.55
    
    # Wheelbase = 500mm, non-X config. arm_length = 250
    arm_plus = agent._calculate_arm_length(500, 'quadcopter_plus')
    assert arm_plus == 250
    
    # Bending Stress: sigma = M * c / I
    # M = 10 N-m = 10,000 N-mm
    # c = 8mm (Outer diameter 16mm)
    # I = 1000 mm^4
    # sigma = 10000 * 8 / 1000 = 80 MPa
    stress = agent._calculate_bending_stress(moment_nm=10.0, outer_d_mm=16.0, I_mm4=1000.0)
    assert stress == 80.0
    
    # Tube Moment of Inertia: I = pi/64 * (D^4 - d^4)
    # D = 16, wall = 1 -> d = 14
    # I = pi/64 * (65536 - 38416) = pi/64 * 27120 = 1331.2
    inertia = agent._calculate_tube_moment_of_inertia(outer_d_mm=16.0, wall_t_mm=1.0)
    assert pytest.approx(inertia, abs=0.5) == 1331.2


# =====================================================================
# 3. Center of Gravity & Inertia Mappings
# =====================================================================
def test_center_of_gravity_agent(mock_llm):
    agent = CogAgent(mock_llm)
    
    # Point mass CG calculation
    components = [
        {'name': 'Motor 1', 'mass_g': 100, 'x_mm': 200, 'y_mm': 0, 'z_mm': 10},
        {'name': 'Motor 2', 'mass_g': 100, 'x_mm': -200, 'y_mm': 0, 'z_mm': 10},
        {'name': 'Battery', 'mass_g': 800, 'x_mm': 0, 'y_mm': 0, 'z_mm': -20}
    ]
    cg = agent._calculate_cg(components)
    # cg_x = (100*200 - 100*200 + 0) / 1000 = 0
    # cg_y = 0
    # cg_z = (100*10 + 100*10 - 800*20) / 1000 = (2000 - 16000) / 1000 = -14.0 mm
    assert cg[0] == 0.0
    assert cg[1] == 0.0
    assert cg[2] == -14.0
    
    # Moments of inertia (I = m * r^2)
    # Motor 1: m = 0.1kg, y = 0, z = 0.024m. x = 0.2m
    # r_x^2 = y^2 + z^2 = 0.000576. Motor 1 Ixx = 0.1 * 0.000576 = 0.0000576 kg-m^2
    # Motor 1 Izz = 0.1 * (0.2^2 + 0) = 0.1 * 0.04 = 0.004 kg-m^2
    moi = agent._calculate_moments_of_inertia(components, cg)
    assert moi[2] > 0.0  # Izz should be positive and non-zero
    
    # Verify our fixed bug: all_up_weight_kg is set correctly and matches total_mass_kg
    # Let's mock a complete design state
    mock_state = {
        'propulsion_design': PropulsionDesign(
            motors=[{'specs': {'weight_g': 100}}],
            propellers=[{'weight_g': 10}],
            escs=[{'specs': {'weight_g': 20}}],
            motor_count=4
        ),
        'structural_design': StructuralDesign(
            frame_weight_g=400,
            wheelbase_mm=500,
            arm_length_mm=250
        ),
        'power_design': PowerDesign(
            total_weight_g=600
        ),
        'electronics_design': ElectronicsDesign(
            flight_controller={'specs': {'weight_g': 50}},
            gps_module={'specs': {'weight_g': 30}},
            receiver={'specs': {'weight_g': 10}},
            telemetry_system={'specs': {'weight_g': 20}},
            pdb={'specs': {'weight_g': 20}}
        ),
        'mission_requirements': MissionRequirements(
            configuration='quadcopter_x',
            payload_mass_kg=0.2
        )
    }
    
    result = agent.analyze(
        propulsion=mock_state['propulsion_design'],
        structure=mock_state['structural_design'],
        power=mock_state['power_design'],
        electronics=mock_state['electronics_design'],
        requirements=mock_state['mission_requirements']
    )
    
    # The total mass is around 2.1 - 2.3 kg
    assert result.total_mass_kg > 1.5
    assert result.all_up_weight_kg == result.total_mass_kg
    assert result.all_up_weight_kg > 0.0  # Must be positive!


# =====================================================================
# 4. Power Agent Batteries & Safety Thresholds
# =====================================================================
def test_power_failsafes_and_thresholds(mock_llm):
    agent = PowerAgent(mock_llm)
    
    # Cell count selection
    # High KV (> 2000) should choose 4S
    cell_count_high_kv = agent._select_cell_count(motor_kv=2300, prop_size_inch=5.0)
    assert cell_count_high_kv == 4
    
    # Low KV (< 400) should choose 8S or higher
    cell_count_low_kv = agent._select_cell_count(motor_kv=380, prop_size_inch=18.0)
    assert cell_count_low_kv >= 8
    
    # Nominal voltage and safety thresholds for 4S battery
    # 4S Nominal = 4 * 3.7 = 14.8V
    # Warning = 4 * 3.5 = 14.0V
    # Cutoff = 4 * 3.3 = 13.2V
    # Let's run design to verify they are populated in safety_thresholds
    mock_prop = PropulsionDesign(
        motors=[{'specs': {'kv': 2300}}],
        propellers=[{'size_inch': 5.0}],
        motor_count=4,
        max_power_draw_w=500,
        calculations={'estimated_auw_kg': 1.0}
    )
    mock_req = MissionRequirements(endurance_min=20)
    
    result = agent.design(mock_req, mock_prop)
    assert result.total_voltage_v == 14.8
    assert result.safety_thresholds['low_voltage_warning_v'] == 14.6
    assert result.safety_thresholds['low_voltage_cutoff_v'] == 13.2


# =====================================================================
# 5. Regulatory Weight Class Compliance
# =====================================================================
def test_regulatory_weight_compliance(mock_llm):
    agent = RegulatoryAgent(mock_llm)
    
    # India DGCA classes:
    # Under 250g -> Nano
    state_nano = {
        'cog_analysis': {'all_up_weight_kg': 0.20},  # 200g
        'mission_requirements': {'max_altitude_m': 15}
    }
    comp_nano = agent._check_india_dgca(state_nano)
    assert comp_nano['category'] == 'Nano'
    assert "No registration required" in str(comp_nano['notes'])
    
    # 2kg to 25kg -> Small
    state_small = {
        'cog_analysis': {'all_up_weight_kg': 3.5},  # 3.5kg
        'mission_requirements': {'max_altitude_m': 120}
    }
    comp_small = agent._check_india_dgca(state_small)
    assert comp_small['category'] == 'Small'
    assert "Registration on Digital Sky platform" in comp_small['requirements']
    assert "UIN (Unique Identification Number)" in comp_small['requirements']


# =====================================================================
# 6. Validator Agent Safety Failsafes Check
# =====================================================================
def test_validator_failsafes(mock_llm):
    agent = ValidatorAgent(mock_llm)
    
    # Verify that when return-to-home is enabled and geofencing is enabled, no warnings are shown
    # Also verify that low battery warning warning is NOT shown when safety_thresholds is set
    state_valid = {
        'propulsion_design': {'total_thrust_n': 80.0, 'motor_count': 4},
        'power_design': {
            'battery': {'specs': {'c_rating': 45}},
            'total_capacity_mah': 5000,
            'calculations': {'max_current_a': 100.0},
            'safety_thresholds': {'low_voltage_warning_v': 14.0}
        },
        'autonomy_design': {
            'safety_features': {
                'return_to_home': {'enabled': True},
                'geofencing': {'enabled': True}
            }
        },
        'cog_analysis': {
            'all_up_weight_kg': 2.0,  # 2.0kg AUW
            'cg_within_tolerance': True
        },
        'structural_design': {
            'safety_factor': 3.0,
            'wheelbase_mm': 500
        },
        'regulatory_compliance': {
            'fully_compliant': True
        }
    }
    
    res = agent._validate_safety(state_valid)
    assert "Return-to-home is disabled" not in str(res['warnings'])
    assert "Geofencing is disabled" not in str(res['warnings'])
    assert "No low battery warning configured" not in str(res['warnings'])
    
    # Verify that when disabled, it warns correctly
    state_invalid = {
        'propulsion_design': {'total_thrust_n': 80.0, 'motor_count': 4},
        'power_design': {
            'battery': {'specs': {'c_rating': 45}},
            'total_capacity_mah': 5000,
            'calculations': {'max_current_a': 100.0},
            'safety_thresholds': {}  # empty low battery warning
        },
        'autonomy_design': {
            'safety_features': {
                'return_to_home': {'enabled': False},
                'geofencing': {'enabled': False}
            }
        },
        'cog_analysis': {
            'all_up_weight_kg': 2.0,
            'cg_within_tolerance': True
        },
        'structural_design': {
            'safety_factor': 3.0,
            'wheelbase_mm': 500
        },
        'regulatory_compliance': {
            'fully_compliant': True
        }
    }
    
    res_inv = agent._validate_safety(state_invalid)
    assert "Return-to-home is disabled" in str(res_inv['warnings'])
    assert "Geofencing is disabled" in str(res_inv['warnings'])
    assert "No low battery warning configured" in str(res_inv['warnings'])
