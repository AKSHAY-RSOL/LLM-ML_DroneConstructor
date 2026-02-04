"""
DroneForge AI - MATLAB Interface
Interface for drone simulation in MATLAB/Simulink.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MatlabInterface:
    """
    Interface for exporting drone design to MATLAB/Simulink.
    Generates .m scripts and Simulink model initialization files.
    """
    
    def __init__(self, output_dir: str = "./matlab_export"):
        """
        Initialize MATLAB interface.
        
        Args:
            output_dir: Directory for exported MATLAB files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_parameters(self, design_state: Dict[str, Any]) -> str:
        """
        Export drone parameters to MATLAB .m file.
        
        Args:
            design_state: Complete drone design state
            
        Returns:
            Path to generated file
        """
        propulsion = design_state.get('propulsion_design', {})
        power = design_state.get('power_design', {})
        cog = design_state.get('cog_analysis', {})
        structural = design_state.get('structural_design', {})
        aero = design_state.get('aerodynamics_analysis', {})
        mission = design_state.get('mission_requirements', {})
        
        # Convert dataclass to dict if needed
        if hasattr(mission, '__dict__'):
            mission = vars(mission)
        
        # Extract values
        motor_count = propulsion.get('motor_count', 4)
        mass_kg = cog.get('all_up_weight_kg', 2.0)
        arm_length_m = structural.get('arm_length_mm', 250) / 1000
        
        # Propeller
        props = propulsion.get('propellers', [])
        prop_diameter_m = props[0].get('size_inch', 10) * 0.0254 if props else 0.254
        prop_pitch_m = props[0].get('pitch_inch', 4.5) * 0.0254 if props else 0.1143
        
        # Motor
        motors = propulsion.get('motors', [])
        if motors:
            motor_kv = motors[0].get('specs', {}).get('kv', 920)
            max_thrust_g = motors[0].get('specs', {}).get('max_thrust_g', 1500)
        else:
            motor_kv = 920
            max_thrust_g = 1500
        
        # Battery
        battery = power.get('battery', {})
        battery_capacity = battery.get('specs', {}).get('capacity_mah', 5000)
        cell_count = battery.get('specs', {}).get('cell_count', 6)
        
        # Inertia
        inertia = cog.get('moments_of_inertia', {})
        Ixx = inertia.get('Ixx', 0.02)
        Iyy = inertia.get('Iyy', 0.02)
        Izz = inertia.get('Izz', 0.04)
        
        # Aerodynamics
        Cd = aero.get('drag_coefficient', 0.5)
        frontal_area = aero.get('frontal_area_m2', 0.04)
        
        # Generate MATLAB script
        matlab_code = f'''%% DroneForge AI - Drone Parameters
% Generated drone parameters for MATLAB/Simulink simulation
% 
% Usage:
%   Run this script to load all parameters into workspace
%   Then use with Simulink drone models

%% Physical Parameters
drone.mass = {mass_kg};              % Total mass [kg]
drone.g = 9.81;                       % Gravity [m/s^2]
drone.arm_length = {arm_length_m};   % Arm length [m]
drone.motor_count = {motor_count};   % Number of motors

%% Inertia Tensor [kg*m^2]
drone.Ixx = {Ixx};
drone.Iyy = {Iyy};
drone.Izz = {Izz};
drone.I = diag([drone.Ixx, drone.Iyy, drone.Izz]);

%% Motor Parameters
motor.Kv = {motor_kv};                           % Motor Kv [RPM/V]
motor.max_thrust = {max_thrust_g / 1000};        % Max thrust per motor [kg]
motor.max_thrust_N = motor.max_thrust * 9.81;    % Max thrust [N]
motor.Kt = 60 / (2 * pi * motor.Kv);             % Torque constant [Nm/A]

%% Propeller Parameters
prop.diameter = {prop_diameter_m};    % Diameter [m]
prop.pitch = {prop_pitch_m};          % Pitch [m]
prop.Ct = 0.1;                        % Thrust coefficient
prop.Cq = 0.01;                       % Torque coefficient

%% Battery Parameters  
battery.capacity = {battery_capacity};           % Capacity [mAh]
battery.cells = {cell_count};                    % Cell count
battery.voltage_full = {cell_count * 4.2};       % Full voltage [V]
battery.voltage_empty = {cell_count * 3.2};      % Empty voltage [V]
battery.voltage_nominal = {cell_count * 3.7};    % Nominal voltage [V]
battery.internal_resistance = 0.02 * battery.cells;  % Internal resistance [Ohm]

%% Aerodynamic Parameters
aero.Cd = {Cd};                       % Drag coefficient
aero.frontal_area = {frontal_area};   % Frontal area [m^2]
aero.rho = 1.225;                     % Air density [kg/m^3]

%% Control Gains (Default PID)
% These should be tuned for your specific application
control.Kp_roll = 5.0;
control.Ki_roll = 0.5;
control.Kd_roll = 0.5;

control.Kp_pitch = 5.0;
control.Ki_pitch = 0.5;
control.Kd_pitch = 0.5;

control.Kp_yaw = 2.0;
control.Ki_yaw = 0.1;
control.Kd_yaw = 0.2;

control.Kp_altitude = 1.0;
control.Ki_altitude = 0.1;
control.Kd_altitude = 0.5;

%% Motor Mixing Matrix
% For X configuration quadcopter
% Motor order: FR, RR, RL, FL (front-right, rear-right, rear-left, front-left)
% Columns: [Thrust, Roll, Pitch, Yaw]
'''
        
        if motor_count == 4:
            matlab_code += '''mixing.matrix = [
    1,  1,  1, -1;   % Motor 1: FR (CW)
    1, -1,  1,  1;   % Motor 2: RR (CCW)
    1, -1, -1, -1;   % Motor 3: RL (CW)
    1,  1, -1,  1;   % Motor 4: FL (CCW)
] / 4;
'''
        elif motor_count == 6:
            matlab_code += '''mixing.matrix = [
    1,  0.5,   1, -1;   % Motor 1
    1, -0.5,   1,  1;   % Motor 2
    1, -1,     0, -1;   % Motor 3
    1, -0.5,  -1,  1;   % Motor 4
    1,  0.5,  -1, -1;   % Motor 5
    1,  1,     0,  1;   % Motor 6
] / 6;
'''
        elif motor_count == 8:
            matlab_code += '''mixing.matrix = [
    1,  0.38,  0.92, -1;   % Motor 1
    1, -0.38,  0.92,  1;   % Motor 2
    1, -0.92,  0.38, -1;   % Motor 3
    1, -0.92, -0.38,  1;   % Motor 4
    1, -0.38, -0.92, -1;   % Motor 5
    1,  0.38, -0.92,  1;   % Motor 6
    1,  0.92, -0.38, -1;   % Motor 7
    1,  0.92,  0.38,  1;   % Motor 8
] / 8;
'''
        
        matlab_code += f'''
%% Simulation Parameters
sim.dt = 0.001;           % Simulation time step [s]
sim.t_end = 60;           % Simulation end time [s]

%% Initial Conditions
init.position = [0; 0; 0];          % [x; y; z] in NED frame [m]
init.velocity = [0; 0; 0];          % [vx; vy; vz] [m/s]
init.attitude = [0; 0; 0];          % [roll; pitch; yaw] [rad]
init.angular_rate = [0; 0; 0];      % [p; q; r] [rad/s]

%% Limits
limits.max_angle = deg2rad(45);     % Max roll/pitch angle [rad]
limits.max_rate = deg2rad(200);     % Max angular rate [rad/s]
limits.max_throttle = 1.0;          % Max throttle command
limits.min_throttle = 0.0;          % Min throttle command

%% Environment
env.gravity = [0; 0; 9.81];         % Gravity vector [m/s^2]
env.wind = [0; 0; 0];               % Wind velocity [m/s]

fprintf('DroneForge AI parameters loaded successfully!\\n');
fprintf('Drone: {motor_count} motors, %.2f kg, %.0f mm arms\\n', drone.mass, drone.arm_length*1000);
'''
        
        # Write file
        filepath = self.output_dir / "drone_parameters.m"
        with open(filepath, 'w') as f:
            f.write(matlab_code)
        
        logger.info(f"MATLAB parameters exported to: {filepath}")
        return str(filepath)
    
    def export_simulink_init(self, design_state: Dict[str, Any]) -> str:
        """
        Generate Simulink initialization script.
        
        Args:
            design_state: Complete drone design state
            
        Returns:
            Path to generated file
        """
        init_code = '''%% DroneForge AI - Simulink Initialization
% Run this script before starting Simulink simulation

% Load drone parameters
drone_parameters;

% Create bus objects for Simulink
% Drone State Bus
DroneState = Simulink.Bus;
DroneState.Elements = [
    Simulink.BusElement; % position
    Simulink.BusElement; % velocity
    Simulink.BusElement; % attitude
    Simulink.BusElement; % angular_rate
    Simulink.BusElement; % motor_commands
];
DroneState.Elements(1).Name = 'position';
DroneState.Elements(1).Dimensions = [3 1];
DroneState.Elements(2).Name = 'velocity';
DroneState.Elements(2).Dimensions = [3 1];
DroneState.Elements(3).Name = 'attitude';
DroneState.Elements(3).Dimensions = [3 1];
DroneState.Elements(4).Name = 'angular_rate';
DroneState.Elements(4).Dimensions = [3 1];
DroneState.Elements(5).Name = 'motor_commands';
DroneState.Elements(5).Dimensions = [drone.motor_count 1];

% Create lookup tables for motor performance
motor_rpm_table = linspace(0, 10000, 100);
motor_thrust_table = (motor_rpm_table / max(motor_rpm_table)).^2 * motor.max_thrust_N;

% Create ground truth data structure
ground_truth.position = timeseries();
ground_truth.velocity = timeseries();
ground_truth.attitude = timeseries();

fprintf('Simulink initialization complete!\\n');
'''
        
        filepath = self.output_dir / "simulink_init.m"
        with open(filepath, 'w') as f:
            f.write(init_code)
        
        logger.info(f"Simulink init script exported to: {filepath}")
        return str(filepath)
    
    def export_dynamics_function(self, design_state: Dict[str, Any]) -> str:
        """
        Generate MATLAB function for drone dynamics.
        
        Args:
            design_state: Complete drone design state
            
        Returns:
            Path to generated file
        """
        dynamics_code = '''function [state_dot] = drone_dynamics(t, state, u, drone, aero, env)
%DRONE_DYNAMICS Computes drone state derivatives
%   state = [x; y; z; vx; vy; vz; phi; theta; psi; p; q; r]
%   u = motor commands (normalized 0-1)
%   
%   Returns state_dot = derivative of state

    % Extract state
    pos = state(1:3);
    vel = state(4:6);
    euler = state(7:9);
    omega = state(10:12);
    
    phi = euler(1);   % roll
    theta = euler(2); % pitch
    psi = euler(3);   % yaw
    
    p = omega(1);
    q = omega(2);
    r = omega(3);
    
    % Rotation matrix (body to world)
    R = [cos(psi)*cos(theta), cos(psi)*sin(theta)*sin(phi)-sin(psi)*cos(phi), cos(psi)*sin(theta)*cos(phi)+sin(psi)*sin(phi);
         sin(psi)*cos(theta), sin(psi)*sin(theta)*sin(phi)+cos(psi)*cos(phi), sin(psi)*sin(theta)*cos(phi)-cos(psi)*sin(phi);
         -sin(theta),         cos(theta)*sin(phi),                            cos(theta)*cos(phi)];
    
    % Motor thrusts
    motor_thrusts = u .* motor.max_thrust_N;
    total_thrust = sum(motor_thrusts);
    
    % Thrust vector in body frame (along -z axis)
    F_thrust_body = [0; 0; -total_thrust];
    
    % Transform to world frame
    F_thrust_world = R * F_thrust_body;
    
    % Gravity
    F_gravity = drone.mass * env.gravity;
    
    % Drag
    speed = norm(vel);
    if speed > 0.1
        F_drag = -0.5 * aero.rho * aero.Cd * aero.frontal_area * speed * vel;
    else
        F_drag = [0; 0; 0];
    end
    
    % Total forces
    F_total = F_thrust_world + F_gravity + F_drag;
    
    % Linear acceleration
    acc = F_total / drone.mass;
    
    % Moments from motor thrusts
    L = drone.arm_length;
    if length(u) == 4  % Quadcopter X
        L_eff = L * cos(pi/4);
        roll_moment = L_eff * (motor_thrusts(1) + motor_thrusts(2) - motor_thrusts(3) - motor_thrusts(4));
        pitch_moment = L_eff * (motor_thrusts(1) + motor_thrusts(4) - motor_thrusts(2) - motor_thrusts(3));
        kQ = 0.01;  % Torque coefficient
        yaw_moment = kQ * (-motor_thrusts(1) + motor_thrusts(2) - motor_thrusts(3) + motor_thrusts(4));
    else
        % Generic
        roll_moment = 0;
        pitch_moment = 0;
        yaw_moment = 0;
    end
    
    M = [roll_moment; pitch_moment; yaw_moment];
    
    % Angular acceleration (Euler's equation)
    I = drone.I;
    omega_cross_I_omega = cross(omega, I * omega);
    omega_dot = I \\ (M - omega_cross_I_omega);
    
    % Euler angle derivatives
    euler_dot = [1, sin(phi)*tan(theta), cos(phi)*tan(theta);
                 0, cos(phi),            -sin(phi);
                 0, sin(phi)/cos(theta),  cos(phi)/cos(theta)] * omega;
    
    % State derivative
    state_dot = [vel; acc; euler_dot; omega_dot];
end
'''
        
        filepath = self.output_dir / "drone_dynamics.m"
        with open(filepath, 'w') as f:
            f.write(dynamics_code)
        
        logger.info(f"Dynamics function exported to: {filepath}")
        return str(filepath)
    
    def export_controller_function(self) -> str:
        """
        Generate MATLAB function for PID controller.
        
        Returns:
            Path to generated file
        """
        controller_code = '''function [u, debug] = drone_controller(state, setpoint, control, drone, mixing)
%DRONE_CONTROLLER PID attitude and altitude controller
%   state = current drone state [x;y;z;vx;vy;vz;phi;theta;psi;p;q;r]
%   setpoint = desired [x;y;z;yaw]
%   control = control gains structure
%   drone = drone parameters structure
%   mixing = motor mixing matrix
%
%   Returns:
%   u = motor commands (normalized 0-1)
%   debug = debug information

    persistent integral_roll integral_pitch integral_yaw integral_alt
    if isempty(integral_roll)
        integral_roll = 0;
        integral_pitch = 0;
        integral_yaw = 0;
        integral_alt = 0;
    end
    
    % Extract current state
    x = state(1); y = state(2); z = state(3);
    vx = state(4); vy = state(5); vz = state(6);
    phi = state(7); theta = state(8); psi = state(9);
    p = state(10); q = state(11); r = state(12);
    
    % Setpoint
    z_des = setpoint(3);
    yaw_des = setpoint(4);
    
    % Altitude control
    z_error = z_des - z;
    integral_alt = integral_alt + z_error * 0.001;
    integral_alt = max(min(integral_alt, 10), -10);  % Anti-windup
    
    throttle = 0.5 + control.Kp_altitude * z_error ...
                   + control.Ki_altitude * integral_alt ...
                   - control.Kd_altitude * vz;
    
    % Yaw control
    yaw_error = wrapToPi(yaw_des - psi);
    integral_yaw = integral_yaw + yaw_error * 0.001;
    integral_yaw = max(min(integral_yaw, 1), -1);
    
    yaw_cmd = control.Kp_yaw * yaw_error ...
            + control.Ki_yaw * integral_yaw ...
            - control.Kd_yaw * r;
    
    % Roll control (to hover, maintain zero roll)
    roll_error = 0 - phi;
    integral_roll = integral_roll + roll_error * 0.001;
    integral_roll = max(min(integral_roll, 0.5), -0.5);
    
    roll_cmd = control.Kp_roll * roll_error ...
             + control.Ki_roll * integral_roll ...
             - control.Kd_roll * p;
    
    % Pitch control (to hover, maintain zero pitch)
    pitch_error = 0 - theta;
    integral_pitch = integral_pitch + pitch_error * 0.001;
    integral_pitch = max(min(integral_pitch, 0.5), -0.5);
    
    pitch_cmd = control.Kp_pitch * pitch_error ...
              + control.Ki_pitch * integral_pitch ...
              - control.Kd_pitch * q;
    
    % Mix commands to motor outputs
    commands = [throttle; roll_cmd; pitch_cmd; yaw_cmd];
    u = mixing.matrix * commands;
    
    % Saturate
    u = max(min(u, 1), 0);
    
    % Debug output
    debug.throttle = throttle;
    debug.roll_cmd = roll_cmd;
    debug.pitch_cmd = pitch_cmd;
    debug.yaw_cmd = yaw_cmd;
    debug.z_error = z_error;
end

function angle = wrapToPi(angle)
    while angle > pi
        angle = angle - 2*pi;
    end
    while angle < -pi
        angle = angle + 2*pi;
    end
end
'''
        
        filepath = self.output_dir / "drone_controller.m"
        with open(filepath, 'w') as f:
            f.write(controller_code)
        
        logger.info(f"Controller function exported to: {filepath}")
        return str(filepath)
    
    def export_simulation_script(self) -> str:
        """
        Generate MATLAB simulation script.
        
        Returns:
            Path to generated file
        """
        sim_code = '''%% DroneForge AI - Drone Simulation
% Run this script to simulate drone flight

clear; clc; close all;

% Load parameters
drone_parameters;

% Simulation setup
dt = sim.dt;
t_end = sim.t_end;
t = 0:dt:t_end;
N = length(t);

% State vector: [x;y;z;vx;vy;vz;phi;theta;psi;p;q;r]
state = zeros(12, N);
state(:,1) = [init.position; init.velocity; init.attitude; init.angular_rate];

% Setpoint (hover at 10m altitude)
setpoint = [0; 0; -10; 0];  % [x, y, z (NED), yaw]

% Motor commands history
u_history = zeros(drone.motor_count, N);

% Simulate
fprintf('Simulating %.0f seconds...\\n', t_end);
tic;

for k = 1:N-1
    % Get current state
    current_state = state(:,k);
    
    % Controller
    [u, ~] = drone_controller(current_state, setpoint, control, drone, mixing);
    u_history(:,k) = u;
    
    % Dynamics (RK4 integration)
    k1 = drone_dynamics(t(k), current_state, u, drone, aero, env);
    k2 = drone_dynamics(t(k)+dt/2, current_state+dt/2*k1, u, drone, aero, env);
    k3 = drone_dynamics(t(k)+dt/2, current_state+dt/2*k2, u, drone, aero, env);
    k4 = drone_dynamics(t(k)+dt, current_state+dt*k3, u, drone, aero, env);
    
    state(:,k+1) = current_state + dt/6 * (k1 + 2*k2 + 2*k3 + k4);
    
    % Ground constraint
    if state(3,k+1) > 0
        state(3,k+1) = 0;
        state(6,k+1) = min(0, state(6,k+1));
    end
end

elapsed = toc;
fprintf('Simulation complete in %.2f seconds (%.1fx real-time)\\n', elapsed, t_end/elapsed);

%% Plot Results
figure('Name', 'DroneForge AI Simulation Results', 'Position', [100 100 1200 800]);

% 3D Trajectory
subplot(2,3,1);
plot3(state(1,:), state(2,:), -state(3,:), 'b-', 'LineWidth', 1.5);
hold on;
plot3(state(1,1), state(2,1), -state(3,1), 'go', 'MarkerSize', 10, 'LineWidth', 2);
plot3(state(1,end), state(2,end), -state(3,end), 'ro', 'MarkerSize', 10, 'LineWidth', 2);
grid on;
xlabel('X [m]'); ylabel('Y [m]'); zlabel('Altitude [m]');
title('3D Trajectory');
legend('Path', 'Start', 'End');

% Altitude
subplot(2,3,2);
plot(t, -state(3,:), 'b-', 'LineWidth', 1.5);
hold on;
yline(-setpoint(3), 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time [s]'); ylabel('Altitude [m]');
title('Altitude');
legend('Actual', 'Setpoint');

% Attitude
subplot(2,3,3);
plot(t, rad2deg(state(7,:)), 'r-', 'LineWidth', 1.5);
hold on;
plot(t, rad2deg(state(8,:)), 'g-', 'LineWidth', 1.5);
plot(t, rad2deg(state(9,:)), 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time [s]'); ylabel('Angle [deg]');
title('Attitude');
legend('Roll', 'Pitch', 'Yaw');

% Velocity
subplot(2,3,4);
plot(t, state(4,:), 'r-', 'LineWidth', 1.5);
hold on;
plot(t, state(5,:), 'g-', 'LineWidth', 1.5);
plot(t, state(6,:), 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time [s]'); ylabel('Velocity [m/s]');
title('Velocity');
legend('Vx', 'Vy', 'Vz');

% Motor commands
subplot(2,3,5);
for m = 1:drone.motor_count
    plot(t, u_history(m,:), 'LineWidth', 1);
    hold on;
end
grid on;
xlabel('Time [s]'); ylabel('Command');
title('Motor Commands');
legend(arrayfun(@(x) sprintf('M%d', x), 1:drone.motor_count, 'UniformOutput', false));

% Angular rates
subplot(2,3,6);
plot(t, rad2deg(state(10,:)), 'r-', 'LineWidth', 1.5);
hold on;
plot(t, rad2deg(state(11,:)), 'g-', 'LineWidth', 1.5);
plot(t, rad2deg(state(12,:)), 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time [s]'); ylabel('Rate [deg/s]');
title('Angular Rates');
legend('p', 'q', 'r');

sgtitle('DroneForge AI - Simulation Results');

fprintf('\\nFinal State:\\n');
fprintf('  Position: [%.2f, %.2f, %.2f] m\\n', state(1,end), state(2,end), -state(3,end));
fprintf('  Velocity: [%.2f, %.2f, %.2f] m/s\\n', state(4,end), state(5,end), state(6,end));
fprintf('  Attitude: [%.1f, %.1f, %.1f] deg\\n', rad2deg(state(7,end)), rad2deg(state(8,end)), rad2deg(state(9,end)));
'''
        
        filepath = self.output_dir / "run_simulation.m"
        with open(filepath, 'w') as f:
            f.write(sim_code)
        
        logger.info(f"Simulation script exported to: {filepath}")
        return str(filepath)
    
    def export_all(self, design_state: Dict[str, Any]) -> Dict[str, str]:
        """
        Export all MATLAB files.
        
        Args:
            design_state: Complete drone design state
            
        Returns:
            Dictionary of file types to paths
        """
        logger.info("Exporting all MATLAB files...")
        
        files = {
            'parameters': self.export_parameters(design_state),
            'simulink_init': self.export_simulink_init(design_state),
            'dynamics': self.export_dynamics_function(design_state),
            'controller': self.export_controller_function(),
            'simulation': self.export_simulation_script()
        }
        
        # Create README
        readme = '''# DroneForge AI - MATLAB Export

This folder contains MATLAB/Simulink files for drone simulation.

## Files

- `drone_parameters.m` - Physical drone parameters
- `simulink_init.m` - Simulink initialization script  
- `drone_dynamics.m` - Dynamics function for simulation
- `drone_controller.m` - PID controller function
- `run_simulation.m` - Main simulation script

## Usage

1. Open MATLAB
2. Navigate to this folder
3. Run `run_simulation.m`

Or for Simulink:
1. Run `drone_parameters.m` to load parameters
2. Run `simulink_init.m` to create bus objects
3. Open your Simulink model

## Notes

- Default simulation is 60 seconds hover test
- Modify setpoint in run_simulation.m for different maneuvers
- Tune PID gains in drone_parameters.m as needed

Generated by DroneForge AI
'''
        
        readme_path = self.output_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme)
        files['readme'] = str(readme_path)
        
        logger.info(f"All MATLAB files exported to: {self.output_dir}")
        return files


def main():
    """Test MATLAB export"""
    print("DroneForge AI - MATLAB Interface Test")
    print("=" * 50)
    
    # Sample design state
    design_state = {
        'mission_requirements': {
            'drone_type': 'multirotor',
            'configuration': 'quadcopter_x'
        },
        'propulsion_design': {
            'motor_count': 4,
            'motors': [{'specs': {'kv': 920, 'max_thrust_g': 1500}}],
            'propellers': [{'size_inch': 10, 'pitch_inch': 4.5}]
        },
        'power_design': {
            'battery': {'specs': {'capacity_mah': 5000, 'cell_count': 6}}
        },
        'cog_analysis': {
            'all_up_weight_kg': 2.5,
            'moments_of_inertia': {'Ixx': 0.025, 'Iyy': 0.025, 'Izz': 0.05}
        },
        'structural_design': {
            'arm_length_mm': 250
        },
        'aerodynamics_analysis': {
            'drag_coefficient': 0.5,
            'frontal_area_m2': 0.04
        }
    }
    
    interface = MatlabInterface("./test_matlab_export")
    files = interface.export_all(design_state)
    
    print("\nExported files:")
    for name, path in files.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
