"""
DroneForge AI - Frame Topology Agent
Determines optimal frame configuration based on mission requirements.
"""

import logging
from typing import Dict, Any
from dataclasses import asdict

logger = logging.getLogger(__name__)


MULTIROTOR_CONFIGS = {
    "tricopter": {
        "motor_count": 3,
        "stability": 0.7,
        "efficiency": 0.85,
        "payload_capacity": "low",
        "complexity": "high",
        "yaw_mechanism": "servo",
        "description": "3 motors with tilting rear for yaw"
    },
    "quadcopter_x": {
        "motor_count": 4,
        "stability": 0.85,
        "efficiency": 0.8,
        "payload_capacity": "medium",
        "complexity": "low",
        "yaw_mechanism": "differential",
        "description": "4 motors in X configuration - most common"
    },
    "quadcopter_plus": {
        "motor_count": 4,
        "stability": 0.8,
        "efficiency": 0.8,
        "payload_capacity": "medium",
        "complexity": "low",
        "yaw_mechanism": "differential",
        "description": "4 motors in + configuration - better for FPV"
    },
    "quadcopter_h": {
        "motor_count": 4,
        "stability": 0.85,
        "efficiency": 0.75,
        "payload_capacity": "medium-high",
        "complexity": "medium",
        "yaw_mechanism": "differential",
        "description": "4 motors in H frame - good for payload"
    },
    "hexacopter_x": {
        "motor_count": 6,
        "stability": 0.9,
        "efficiency": 0.7,
        "payload_capacity": "high",
        "complexity": "medium",
        "yaw_mechanism": "differential",
        "description": "6 motors - redundancy and higher payload"
    },
    "hexacopter_plus": {
        "motor_count": 6,
        "stability": 0.88,
        "efficiency": 0.7,
        "payload_capacity": "high",
        "complexity": "medium",
        "yaw_mechanism": "differential",
        "description": "6 motors in + configuration"
    },
    "octocopter_x": {
        "motor_count": 8,
        "stability": 0.95,
        "efficiency": 0.6,
        "payload_capacity": "very_high",
        "complexity": "high",
        "yaw_mechanism": "differential",
        "description": "8 motors - maximum payload and redundancy"
    },
    "octocopter_coax": {
        "motor_count": 8,
        "stability": 0.93,
        "efficiency": 0.55,
        "payload_capacity": "very_high",
        "complexity": "high",
        "yaw_mechanism": "differential",
        "description": "8 motors coaxial - compact footprint"
    }
}

FIXED_WING_CONFIGS = {
    "conventional": {
        "stability": 0.9,
        "efficiency": 0.9,
        "payload_capacity": "medium",
        "complexity": "medium",
        "description": "Traditional wing + tail configuration"
    },
    "flying_wing": {
        "stability": 0.7,
        "efficiency": 0.85,
        "payload_capacity": "low",
        "complexity": "low",
        "description": "No tail - compact and efficient"
    },
    "canard": {
        "stability": 0.75,
        "efficiency": 0.88,
        "payload_capacity": "medium",
        "complexity": "high",
        "description": "Front control surfaces"
    },
    "delta": {
        "stability": 0.72,
        "efficiency": 0.82,
        "payload_capacity": "low",
        "complexity": "low",
        "description": "Delta wing configuration"
    }
}

VTOL_CONFIGS = {
    "quadplane": {
        "motor_count": 5,
        "stability": 0.85,
        "efficiency": 0.75,
        "payload_capacity": "medium",
        "complexity": "high",
        "description": "Fixed-wing with 4 VTOL motors"
    },
    "tiltrotor_quad": {
        "motor_count": 4,
        "stability": 0.8,
        "efficiency": 0.8,
        "payload_capacity": "medium",
        "complexity": "very_high",
        "description": "4 tilting rotors"
    },
    "tiltrotor_tri": {
        "motor_count": 3,
        "stability": 0.75,
        "efficiency": 0.82,
        "payload_capacity": "low",
        "complexity": "very_high",
        "description": "3 tilting rotors"
    },
    "tailsitter": {
        "motor_count": 2,
        "stability": 0.65,
        "efficiency": 0.85,
        "payload_capacity": "low",
        "complexity": "medium",
        "description": "Lands on tail, transitions to horizontal"
    },
    "lift_cruise": {
        "motor_count": 6,
        "stability": 0.88,
        "efficiency": 0.7,
        "payload_capacity": "high",
        "complexity": "high",
        "description": "Separate lift and cruise motors"
    }
}


class FrameTopologyAgent:
    """Agent for determining frame topology"""
    
    def __init__(self, llm_provider: Any = None):
        self.llm = llm_provider
    
    def determine_topology(self, requirements: Any) -> Dict[str, Any]:
        """
        Determine optimal frame topology based on requirements.
        
        Args:
            requirements: MissionRequirements object
            
        Returns:
            Dictionary with topology details
        """
        # Convert to dict if dataclass
        if hasattr(requirements, '__dict__'):
            req = asdict(requirements) if hasattr(requirements, '__dataclass_fields__') else vars(requirements)
        else:
            req = dict(requirements) if requirements else {}
        
        drone_type = str(req.get('drone_type', 'multirotor')).lower()
        payload_kg = req.get('payload_mass_kg', 0)
        endurance_min = req.get('endurance_min', 20)
        range_km = req.get('range_km', 5)
        max_speed_ms = req.get('max_speed_ms', 15)
        use_case = str(req.get('use_case', '')).lower()
        beyond_vlos = req.get('beyond_vlos', False)
        obstacle_avoidance = req.get('obstacle_avoidance', False)
        
        # Select based on drone type
        if 'multirotor' in drone_type:
            config = self._select_multirotor_config(
                payload_kg, endurance_min, use_case, obstacle_avoidance
            )
            config_type = "multirotor"
        elif 'fixed_wing' in drone_type or 'fixed-wing' in drone_type:
            config = self._select_fixed_wing_config(
                range_km, max_speed_ms, payload_kg, use_case
            )
            config_type = "fixed_wing"
        elif 'vtol' in drone_type:
            config = self._select_vtol_config(
                range_km, payload_kg, use_case, beyond_vlos
            )
            config_type = "vtol"
        else:
            # Default to quadcopter
            config = "quadcopter_x"
            config_type = "multirotor"
        
        # Get config details
        if config_type == "multirotor":
            details = MULTIROTOR_CONFIGS.get(config, MULTIROTOR_CONFIGS["quadcopter_x"])
        elif config_type == "fixed_wing":
            details = FIXED_WING_CONFIGS.get(config, FIXED_WING_CONFIGS["conventional"])
        else:
            details = VTOL_CONFIGS.get(config, VTOL_CONFIGS["quadplane"])
        
        logger.info(f"Selected topology: {config} ({config_type})")
        
        return {
            "configuration": config,
            "type": config_type,
            "motor_count": details.get("motor_count", 4),
            "stability_rating": details.get("stability", 0.8),
            "efficiency_rating": details.get("efficiency", 0.8),
            "payload_class": details.get("payload_capacity", "medium"),
            "complexity": details.get("complexity", "medium"),
            "description": details.get("description", ""),
            "reasoning": self._generate_reasoning(config, details, req)
        }
    
    def _select_multirotor_config(
        self, 
        payload_kg: float, 
        endurance_min: float,
        use_case: str,
        obstacle_avoidance: bool
    ) -> str:
        """Select multirotor configuration"""
        
        # Heavy payload needs more motors
        if payload_kg > 5:
            return "octocopter_x"
        elif payload_kg > 2:
            return "hexacopter_x"
        
        # Long endurance favors efficiency
        if endurance_min > 45:
            return "hexacopter_x"  # Better motor redundancy for long flights
        
        # Racing/FPV
        if 'racing' in use_case or 'fpv' in use_case or 'acrobat' in use_case:
            return "quadcopter_x"
        
        # Inspection/mapping with obstacle avoidance
        if obstacle_avoidance and ('inspect' in use_case or 'indoor' in use_case):
            return "quadcopter_h"  # Good visibility
        
        # Photography/cinematography
        if 'photo' in use_case or 'video' in use_case or 'cinema' in use_case:
            return "hexacopter_x"  # Redundancy for expensive payloads
        
        # Agriculture/spraying
        if 'agri' in use_case or 'spray' in use_case:
            return "hexacopter_x"
        
        # Default
        return "quadcopter_x"
    
    def _select_fixed_wing_config(
        self,
        range_km: float,
        max_speed_ms: float,
        payload_kg: float,
        use_case: str
    ) -> str:
        """Select fixed-wing configuration"""
        
        # Long range mapping
        if range_km > 50:
            return "conventional"
        
        # Compact requirement
        if 'compact' in use_case or 'portable' in use_case:
            return "flying_wing"
        
        # High speed
        if max_speed_ms > 30:
            return "delta"
        
        # Standard mapping/survey
        if 'mapping' in use_case or 'survey' in use_case:
            return "conventional"
        
        return "conventional"
    
    def _select_vtol_config(
        self,
        range_km: float,
        payload_kg: float,
        use_case: str,
        beyond_vlos: bool
    ) -> str:
        """Select VTOL configuration"""
        
        # Long range BVLOS
        if beyond_vlos and range_km > 30:
            return "lift_cruise"
        
        # Heavy payload
        if payload_kg > 3:
            return "lift_cruise"
        
        # Standard applications
        if 'delivery' in use_case:
            return "quadplane"
        
        if 'survey' in use_case or 'mapping' in use_case:
            return "quadplane"
        
        # Compact
        if 'compact' in use_case:
            return "tailsitter"
        
        return "quadplane"
    
    def _generate_reasoning(
        self, 
        config: str, 
        details: Dict, 
        requirements: Dict
    ) -> str:
        """Generate reasoning for topology selection"""
        
        payload = requirements.get('payload_mass_kg', 0)
        use_case = requirements.get('use_case', 'general')
        
        reasons = []
        
        if 'octo' in config:
            reasons.append(f"Octocopter selected for heavy payload ({payload:.1f}kg) and maximum redundancy")
        elif 'hexa' in config:
            reasons.append(f"Hexacopter provides good balance of payload capacity and motor redundancy")
        elif 'quad' in config:
            reasons.append(f"Quadcopter is optimal for payload under 2kg with good efficiency")
        
        if details.get('efficiency', 0) > 0.8:
            reasons.append("High efficiency configuration for extended flight time")
        
        if details.get('stability', 0) > 0.9:
            reasons.append("Excellent stability for precision operations")
        
        if not reasons:
            reasons.append(f"Selected {config} for {use_case} application")
        
        return ". ".join(reasons)
