"""
DroneForge AI - Standalone Simulation
Physics-based drone flight simulation without external dependencies.
"""

import numpy as np
import json
import logging
import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DroneState:
    """Current state of the simulated drone"""
    # Position (NED frame, meters)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # Down is positive
    
    # Velocity (m/s)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    
    # Attitude (radians)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    
    # Angular rates (rad/s)
    p: float = 0.0
    q: float = 0.0
    r: float = 0.0
    
    # Motor outputs (0-1)
    motor_outputs: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    
    # Battery state
    battery_voltage: float = 22.2  # 6S nominal
    battery_soc: float = 100.0  # State of charge %
    
    # Time
    time: float = 0.0


@dataclass
class DroneConfig:
    """Drone physical configuration"""
    mass_kg: float = 2.0
    arm_length_m: float = 0.25
    motor_count: int = 4
    
    # Inertia tensor (kg*m^2)
    Ixx: float = 0.02
    Iyy: float = 0.02
    Izz: float = 0.04
    
    # Motor parameters
    max_thrust_per_motor_n: float = 15.0
    motor_kv: float = 920
    prop_diameter_m: float = 0.254  # 10 inch
    
    # Drag coefficients
    Cd_xy: float = 0.5
    Cd_z: float = 1.0
    frontal_area_m2: float = 0.04
    
    # Battery
    battery_capacity_mah: float = 5000
    battery_voltage_full: float = 25.2
    battery_voltage_empty: float = 19.2
    
    # Config type
    config_type: str = "quadcopter_x"


class StandaloneSimulator:
    """
    Physics-based drone flight simulator.
    Simulates multirotor dynamics without external dependencies.
    """
    
    # Constants
    GRAVITY = 9.81  # m/s^2
    AIR_DENSITY = 1.225  # kg/m^3
    
    def __init__(
        self,
        config: Optional[DroneConfig] = None,
        dt: float = 0.001  # 1000 Hz simulation
    ):
        """
        Initialize simulator.
        
        Args:
            config: Drone configuration
            dt: Simulation time step in seconds
        """
        self.config = config or DroneConfig()
        self.dt = dt
        self.state = DroneState()
        self.history: List[Dict] = []
        
        # Pre-compute motor mixing matrix
        self.mixing_matrix = self._compute_mixing_matrix()
        
        logger.info(f"Simulator initialized: {self.config.motor_count} motors, dt={dt*1000:.1f}ms")
    
    def _compute_mixing_matrix(self) -> np.ndarray:
        """
        Compute motor mixing matrix for X configuration.
        Maps [thrust, roll, pitch, yaw] to motor outputs.
        """
        L = self.config.arm_length_m
        
        if self.config.config_type == "quadcopter_x":
            # X configuration: motors at 45, 135, 225, 315 degrees
            # Motor order: front-right, rear-right, rear-left, front-left
            # CW: 1, 3; CCW: 2, 4
            return np.array([
                [1,  1,  1, -1],  # Motor 1: FR (CW)
                [1, -1,  1,  1],  # Motor 2: RR (CCW)
                [1, -1, -1, -1],  # Motor 3: RL (CW)
                [1,  1, -1,  1],  # Motor 4: FL (CCW)
            ]) / 4.0
        
        elif self.config.config_type == "quadcopter_plus":
            return np.array([
                [1,  0,  1, -1],  # Motor 1: Front (CW)
                [1, -1,  0,  1],  # Motor 2: Right (CCW)
                [1,  0, -1, -1],  # Motor 3: Rear (CW)
                [1,  1,  0,  1],  # Motor 4: Left (CCW)
            ]) / 4.0
        
        elif self.config.config_type == "hexacopter_x":
            return np.array([
                [1,  0.5,   1, -1],  # Motor 1
                [1, -0.5,   1,  1],  # Motor 2
                [1, -1,     0, -1],  # Motor 3
                [1, -0.5,  -1,  1],  # Motor 4
                [1,  0.5,  -1, -1],  # Motor 5
                [1,  1,     0,  1],  # Motor 6
            ]) / 6.0
        
        else:
            # Default quad X
            return np.array([
                [1,  1,  1, -1],
                [1, -1,  1,  1],
                [1, -1, -1, -1],
                [1,  1, -1,  1],
            ]) / 4.0
    
    @classmethod
    def from_design_state(cls, design_state: Dict[str, Any]) -> 'StandaloneSimulator':
        """
        Create simulator from DroneForge design state.
        
        Args:
            design_state: Complete drone design state
            
        Returns:
            Configured simulator
        """
        propulsion = design_state.get('propulsion_design', {})
        power = design_state.get('power_design', {})
        cog = design_state.get('cog_analysis', {})
        structural = design_state.get('structural_design', {})
        mission = design_state.get('mission_requirements', {})
        
        # Get motor count
        motor_count = propulsion.get('motor_count', 4)
        
        # Get mass
        mass_kg = cog.get('all_up_weight_kg', 2.0)
        
        # Get arm length
        arm_length_mm = structural.get('arm_length_mm', 250)
        arm_length_m = arm_length_mm / 1000.0
        
        # Get propeller size
        props = propulsion.get('propellers', [])
        if props:
            prop_inch = props[0].get('size_inch', 10)
        else:
            prop_inch = 10
        prop_diameter_m = prop_inch * 0.0254
        
        # Get motor KV
        motors = propulsion.get('motors', [])
        if motors:
            motor_kv = motors[0].get('specs', {}).get('kv', 920)
            max_thrust_g = motors[0].get('specs', {}).get('max_thrust_g', 1500)
            max_thrust_n = max_thrust_g * 0.00981
        else:
            motor_kv = 920
            max_thrust_n = 15.0
        
        # Get battery
        battery = power.get('battery', {})
        battery_capacity = battery.get('specs', {}).get('capacity_mah', 5000)
        cell_count = battery.get('specs', {}).get('cell_count', 6)
        battery_voltage_full = cell_count * 4.2
        battery_voltage_empty = cell_count * 3.2
        
        # Get inertia
        inertia = cog.get('moments_of_inertia', {})
        Ixx = inertia.get('Ixx', 0.02)
        Iyy = inertia.get('Iyy', 0.02)
        Izz = inertia.get('Izz', 0.04)
        
        # Get configuration
        if hasattr(mission, 'configuration'):
            config_type = mission.configuration
        elif isinstance(mission, dict):
            config_type = mission.get('configuration', 'quadcopter_x')
        else:
            config_type = 'quadcopter_x'
        
        config = DroneConfig(
            mass_kg=mass_kg,
            arm_length_m=arm_length_m,
            motor_count=motor_count,
            Ixx=Ixx,
            Iyy=Iyy,
            Izz=Izz,
            max_thrust_per_motor_n=max_thrust_n,
            motor_kv=motor_kv,
            prop_diameter_m=prop_diameter_m,
            battery_capacity_mah=battery_capacity,
            battery_voltage_full=battery_voltage_full,
            battery_voltage_empty=battery_voltage_empty,
            config_type=config_type
        )
        
        return cls(config)
    
    def reset(self) -> DroneState:
        """Reset simulation to initial state"""
        self.state = DroneState()
        self.state.motor_outputs = [0.0] * self.config.motor_count
        self.state.battery_voltage = self.config.battery_voltage_full
        self.state.battery_soc = 100.0
        self.history = []
        return self.state
    
    def compute_motor_outputs(
        self,
        throttle: float,
        roll_cmd: float,
        pitch_cmd: float,
        yaw_cmd: float
    ) -> np.ndarray:
        """
        Compute motor outputs from control commands.
        
        Args:
            throttle: 0-1 collective throttle
            roll_cmd: -1 to 1 roll command
            pitch_cmd: -1 to 1 pitch command
            yaw_cmd: -1 to 1 yaw command
            
        Returns:
            Array of motor outputs (0-1)
        """
        commands = np.array([throttle, roll_cmd * 0.3, pitch_cmd * 0.3, yaw_cmd * 0.3])
        motor_outputs = self.mixing_matrix @ commands
        
        # Clip to valid range
        motor_outputs = np.clip(motor_outputs, 0, 1)
        
        return motor_outputs
    
    def compute_forces_moments(
        self,
        motor_outputs: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute forces and moments from motor outputs.
        
        Args:
            motor_outputs: Array of motor outputs (0-1)
            
        Returns:
            Tuple of (forces [N], moments [N*m]) in body frame
        """
        # Thrust from each motor
        thrusts = motor_outputs * self.config.max_thrust_per_motor_n
        total_thrust = np.sum(thrusts)
        
        # Forces in body frame (thrust along -z body axis)
        forces = np.array([0, 0, -total_thrust])
        
        # Moments from motor thrust differences (BUG-062)
        L = self.config.arm_length_m
        
        roll_moment = 0.0
        pitch_moment = 0.0
        yaw_moment = 0.0
        kQ = 0.01  # Torque coefficient
        
        if self.config.config_type == "quadcopter_x":
            L_eff = L * math.cos(math.pi/4)
            roll_moment = L_eff * (thrusts[0] + thrusts[1] - thrusts[2] - thrusts[3])
            pitch_moment = L_eff * (thrusts[0] + thrusts[3] - thrusts[1] - thrusts[2])
            yaw_moment = kQ * (-thrusts[0] + thrusts[1] - thrusts[2] + thrusts[3])
        elif self.config.config_type == "quadcopter_plus":
            roll_moment = L * (thrusts[3] - thrusts[1])
            pitch_moment = L * (thrusts[0] - thrusts[2])
            yaw_moment = kQ * (-thrusts[0] + thrusts[1] - thrusts[2] + thrusts[3])
        elif self.config.config_type == "hexacopter_x":
            # 6-motor geometry: FR, R, RR, RL, L, FL
            roll_moment = L * (0.5 * thrusts[0] + thrusts[1] + 0.5 * thrusts[2] - 0.5 * thrusts[3] - thrusts[4] - 0.5 * thrusts[5])
            pitch_moment = L * (thrusts[0] - thrusts[2] - thrusts[3] + thrusts[5])
            yaw_moment = kQ * (-thrusts[0] + thrusts[1] - thrusts[2] + thrusts[3] - thrusts[4] + thrusts[5])
        else:
            # Generic loop over all motors (BUG-062)
            num_motors = len(thrusts)
            for i in range(num_motors):
                angle = math.radians(i * (360.0 / num_motors))
                cw_ccw = -1 if i % 2 == 0 else 1
                roll_moment += thrusts[i] * L * math.sin(angle)
                pitch_moment += -thrusts[i] * L * math.cos(angle)
                yaw_moment += thrusts[i] * kQ * cw_ccw
                
        moments = np.array([roll_moment, pitch_moment, yaw_moment])
        
        return forces, moments
    
    def compute_drag(self) -> np.ndarray:
        """Compute aerodynamic drag forces"""
        velocity = np.array([self.state.vx, self.state.vy, self.state.vz])
        speed = np.linalg.norm(velocity)
        
        if speed < 0.1:
            return np.zeros(3)
        
        # Drag force magnitude
        Cd = self.config.Cd_xy
        A = self.config.frontal_area_m2
        drag_magnitude = 0.5 * self.AIR_DENSITY * Cd * A * speed**2
        
        # Drag direction (opposite to velocity)
        drag_direction = -velocity / speed
        drag_force = drag_magnitude * drag_direction
        
        return drag_force
    
    def rotation_matrix(self, roll: float, pitch: float, yaw: float) -> np.ndarray:
        """Compute rotation matrix from Euler angles (ZYX convention)"""
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)
        
        R = np.array([
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr],
            [-sp,   cp*sr,            cp*cr]
        ])
        
        return R
    
    def step(
        self,
        throttle: float = 0.0,
        roll_cmd: float = 0.0,
        pitch_cmd: float = 0.0,
        yaw_cmd: float = 0.0
    ) -> DroneState:
        """
        Advance simulation by one time step.
        
        Args:
            throttle: 0-1 collective throttle
            roll_cmd: -1 to 1 roll command
            pitch_cmd: -1 to 1 pitch command  
            yaw_cmd: -1 to 1 yaw command
            
        Returns:
            Updated drone state
        """
        # Compute motor outputs
        motor_outputs = self.compute_motor_outputs(throttle, roll_cmd, pitch_cmd, yaw_cmd)
        self.state.motor_outputs = motor_outputs.tolist()
        
        # Compute forces and moments in body frame
        forces_body, moments_body = self.compute_forces_moments(motor_outputs)
        
        # Rotation matrix from body to world frame
        R = self.rotation_matrix(self.state.roll, self.state.pitch, self.state.yaw)
        
        # Transform thrust to world frame
        forces_world = R @ forces_body
        
        # Add gravity and drag
        gravity = np.array([0, 0, self.config.mass_kg * self.GRAVITY])
        drag = self.compute_drag()
        
        total_forces = forces_world + gravity + drag
        
        # Linear acceleration
        acceleration = total_forces / self.config.mass_kg
        
        # Update velocities
        self.state.vx += acceleration[0] * self.dt
        self.state.vy += acceleration[1] * self.dt
        self.state.vz += acceleration[2] * self.dt
        
        # Update positions
        self.state.x += self.state.vx * self.dt
        self.state.y += self.state.vy * self.dt
        self.state.z += self.state.vz * self.dt
        
        # Ground constraint
        if self.state.z > 0:
            self.state.z = 0
            self.state.vz = min(0, self.state.vz)
        
        # Angular acceleration
        I = np.diag([self.config.Ixx, self.config.Iyy, self.config.Izz])
        omega = np.array([self.state.p, self.state.q, self.state.r])
        
        # Euler's equation: I * omega_dot = M - omega x (I * omega)
        gyroscopic = np.cross(omega, I @ omega)
        angular_acc = np.linalg.solve(I, moments_body - gyroscopic)
        
        # Update angular rates
        self.state.p += angular_acc[0] * self.dt
        self.state.q += angular_acc[1] * self.dt
        self.state.r += angular_acc[2] * self.dt
        
        # Update Euler angles
        # Euler rate to body rate transformation
        self.state.roll += (self.state.p + 
                           np.sin(self.state.roll) * np.tan(self.state.pitch) * self.state.q +
                           np.cos(self.state.roll) * np.tan(self.state.pitch) * self.state.r) * self.dt
        self.state.pitch += (np.cos(self.state.roll) * self.state.q - 
                            np.sin(self.state.roll) * self.state.r) * self.dt
        self.state.yaw += (np.sin(self.state.roll) / np.cos(self.state.pitch) * self.state.q +
                          np.cos(self.state.roll) / np.cos(self.state.pitch) * self.state.r) * self.dt
        
        # Wrap yaw to -pi to pi
        self.state.yaw = np.arctan2(np.sin(self.state.yaw), np.cos(self.state.yaw))
        
        # Update battery
        current_draw = np.sum(motor_outputs) * 20  # Rough estimate: 20A per motor at full throttle
        capacity_used = current_draw * (self.dt / 3600) * 1000  # mAh
        self.state.battery_soc -= capacity_used / self.config.battery_capacity_mah * 100
        self.state.battery_soc = max(0, self.state.battery_soc)
        
        voltage_range = self.config.battery_voltage_full - self.config.battery_voltage_empty
        self.state.battery_voltage = self.config.battery_voltage_empty + voltage_range * (self.state.battery_soc / 100)
        
        # Update time
        self.state.time += self.dt
        
        return self.state
    
    def run_simulation(
        self,
        duration_s: float,
        control_callback: Optional[callable] = None,
        record_interval: float = 0.01
    ) -> List[Dict]:
        """
        Run simulation for specified duration.
        
        Args:
            duration_s: Simulation duration in seconds
            control_callback: Function that returns (throttle, roll, pitch, yaw) given state
            record_interval: How often to record state (seconds)
            
        Returns:
            List of recorded states
        """
        self.reset()
        records = []
        last_record_time = 0
        
        steps = int(duration_s / self.dt)
        
        for _ in range(steps):
            # Get control commands
            if control_callback:
                throttle, roll, pitch, yaw = control_callback(self.state)
            else:
                # Default: hover
                throttle = self.config.mass_kg * self.GRAVITY / (
                    self.config.motor_count * self.config.max_thrust_per_motor_n
                )
                roll, pitch, yaw = 0, 0, 0
            
            # Step simulation
            self.step(throttle, roll, pitch, yaw)
            
            # Record state
            if self.state.time - last_record_time >= record_interval:
                records.append({
                    'time': self.state.time,
                    'x': self.state.x,
                    'y': self.state.y,
                    'z': self.state.z,
                    'vx': self.state.vx,
                    'vy': self.state.vy,
                    'vz': self.state.vz,
                    'roll': np.degrees(self.state.roll),
                    'pitch': np.degrees(self.state.pitch),
                    'yaw': np.degrees(self.state.yaw),
                    'battery_soc': self.state.battery_soc
                })
                last_record_time = self.state.time
        
        self.history = records
        return records
    
    def hover_test(self, duration_s: float = 10.0) -> Dict:
        """
        Run hover stability test.
        
        Returns:
            Test results including max deviations
        """
        logger.info("Running hover test...")
        
        def hover_controller(state):
            # Simple hover with minimal corrections
            g = self.GRAVITY
            m = self.config.mass_kg
            n = self.config.motor_count
            T_max = self.config.max_thrust_per_motor_n
            
            # Throttle for hover
            throttle = (m * g) / (n * T_max)
            
            # PD attitude control
            Kp = 0.5
            Kd = 0.1
            
            roll_cmd = -Kp * state.roll - Kd * state.p
            pitch_cmd = -Kp * state.pitch - Kd * state.q
            yaw_cmd = -Kd * state.r
            
            return throttle, roll_cmd, pitch_cmd, yaw_cmd
        
        records = self.run_simulation(duration_s, hover_controller)
        
        # Analyze results
        z_values = [r['z'] for r in records]
        roll_values = [r['roll'] for r in records]
        pitch_values = [r['pitch'] for r in records]
        
        results = {
            'duration_s': duration_s,
            'max_altitude_deviation_m': max(abs(z) for z in z_values),
            'max_roll_deg': max(abs(r) for r in roll_values),
            'max_pitch_deg': max(abs(p) for p in pitch_values),
            'final_altitude_m': -z_values[-1] if z_values else 0,
            'battery_used_percent': 100 - self.state.battery_soc,
            'stable': max(abs(r) for r in roll_values) < 10 and max(abs(p) for p in pitch_values) < 10
        }
        
        logger.info(f"Hover test complete: stable={results['stable']}")
        return results
    
    def waypoint_test(
        self,
        waypoints: List[Tuple[float, float, float]],
        speed_ms: float = 5.0
    ) -> Dict:
        """
        Run waypoint navigation test.
        
        Args:
            waypoints: List of (x, y, z) waypoints in meters
            speed_ms: Target speed
            
        Returns:
            Test results
        """
        logger.info(f"Running waypoint test with {len(waypoints)} waypoints...")
        
        current_wp_idx = 0
        
        def waypoint_controller(state):
            nonlocal current_wp_idx
            
            if current_wp_idx >= len(waypoints):
                # Hover at last waypoint
                return 0.5, 0, 0, 0
            
            target = waypoints[current_wp_idx]
            
            # Position error
            ex = target[0] - state.x
            ey = target[1] - state.y
            ez = target[2] - (-state.z)  # Convert from NED
            
            distance = np.sqrt(ex**2 + ey**2 + ez**2)
            
            # Check if reached waypoint
            if distance < 1.0:
                current_wp_idx += 1
                logger.info(f"Reached waypoint {current_wp_idx}")
            
            # Simple position controller
            Kp_pos = 0.3
            Kp_alt = 0.5
            Kd = 0.2
            
            # Desired velocities
            vx_des = Kp_pos * ex
            vy_des = Kp_pos * ey
            
            # Limit speed
            speed = np.sqrt(vx_des**2 + vy_des**2)
            if speed > speed_ms:
                vx_des = vx_des / speed * speed_ms
                vy_des = vy_des / speed * speed_ms
            
            # Velocity error
            vx_err = vx_des - state.vx
            vy_err = vy_des - state.vy
            
            # Convert to pitch/roll commands (simplified)
            pitch_cmd = np.clip(0.1 * vx_err, -0.5, 0.5)
            roll_cmd = np.clip(-0.1 * vy_err, -0.5, 0.5)
            
            # Altitude control (BUG-064: correct NED damping sign)
            g = self.GRAVITY
            m = self.config.mass_kg
            n = self.config.motor_count
            T_max = self.config.max_thrust_per_motor_n
            
            throttle = (m * g) / (n * T_max) + Kp_alt * ez + Kd * state.vz
            throttle = np.clip(throttle, 0, 1)
            
            return throttle, roll_cmd, pitch_cmd, 0
        
        # Estimate duration based on total distance
        total_distance = 0
        prev = (0, 0, 0)
        for wp in waypoints:
            total_distance += np.sqrt(sum((a-b)**2 for a, b in zip(wp, prev)))
            prev = wp
        
        duration = total_distance / speed_ms * 2  # 2x for safety margin
        duration = max(duration, 30)
        
        records = self.run_simulation(duration, waypoint_controller)
        
        results = {
            'waypoints_total': len(waypoints),
            'waypoints_reached': current_wp_idx,
            'total_distance_m': total_distance,
            'duration_s': self.state.time,
            'battery_used_percent': 100 - self.state.battery_soc,
            'success': current_wp_idx >= len(waypoints)
        }
        
        logger.info(f"Waypoint test complete: {current_wp_idx}/{len(waypoints)} waypoints reached")
        return results
    
    def export_results(self, filepath: str) -> None:
        """Export simulation history to JSON file"""
        data = {
            'config': {
                'mass_kg': self.config.mass_kg,
                'motor_count': self.config.motor_count,
                'arm_length_m': self.config.arm_length_m
            },
            'history': self.history
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Results exported to: {filepath}")


def main():
    """Test the simulator"""
    print("DroneForge AI - Standalone Simulator Test")
    print("=" * 50)
    
    # Create default simulator
    sim = StandaloneSimulator()
    
    # Run hover test
    hover_results = sim.hover_test(duration_s=5.0)
    print("\nHover Test Results:")
    for key, value in hover_results.items():
        print(f"  {key}: {value}")
    
    # Run waypoint test
    waypoints = [
        (10, 0, 10),   # Forward 10m, up 10m
        (10, 10, 10),  # Right 10m
        (0, 10, 10),   # Back 10m
        (0, 0, 10),    # Left 10m (square complete)
    ]
    
    wp_results = sim.waypoint_test(waypoints, speed_ms=3.0)
    print("\nWaypoint Test Results:")
    for key, value in wp_results.items():
        print(f"  {key}: {value}")
    
    # Export
    sim.export_results("simulation_results.json")
    print("\nResults exported to simulation_results.json")


if __name__ == "__main__":
    main()
