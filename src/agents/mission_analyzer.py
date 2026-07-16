"""
Mission Analyzer Agent
Parses natural language mission statement and extracts structured requirements.
"""

import json
import logging
import re
from typing import Any, Optional, Dict, Literal

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..core.state import (
    MissionRequirements,
    DroneType,
    MultirotorConfig,
    FixedWingConfig,
    VTOLConfig
)

logger = logging.getLogger(__name__)


MISSION_ANALYZER_PROMPT = """You are an expert drone systems engineer. Analyze the following mission statement and extract detailed requirements.

## Mission Statement:
{mission_statement}

## CAD Detail Level Requested: {cad_detail}

## Your Task:
Extract and infer ALL requirements needed to design a drone for this mission. Be specific with numbers.
If values are not explicitly stated, infer reasonable values based on the mission type.

## Output JSON Schema:
{{
    "drone_type": "multirotor|fixed_wing|vtol|hybrid",
    "configuration": "quadcopter|hexacopter|octocopter|x_config|h_config|plus_config|coaxial|conventional|flying_wing|delta|vtail|quadplane|tiltrotor|tailsitter|lift_cruise",
    "payload_capacity_kg": <number>,
    "flight_time_minutes": <number>,
    "range_km": <number>,
    "max_speed_ms": <number>,
    "cruise_speed_ms": <number>,
    "max_altitude_m": <number>,
    "operating_altitude_m": <number>,
    "wind_resistance_ms": <number>,
    "ip_rating": "IP43|IP54|IP55|IP65|IP67",
    "operating_temperature_min_c": <number>,
    "operating_temperature_max_c": <number>,
    "use_cases": ["list of use cases like agriculture, inspection, delivery, etc."],
    "autonomy_level": 0-5,
    "obstacle_avoidance": true|false,
    "return_to_home": true|false,
    "precision_landing": true|false,
    "waypoint_navigation": true|false,
    "fpv_capability": true|false,
    "camera_gimbal": true|false,
    "gps_required": true|false,
    "indoor_outdoor": "indoor|outdoor|both",
    "bvlos": true|false,
    "night_operations": true|false,
    "jurisdictions": ["list of regulatory jurisdictions like india, usa, eu"],
    "budget_usd": <number or null>,
    "cad_detail": "basic|detailed",
    "special_requirements": ["list of any special requirements mentioned"],
    "reasoning": "Brief explanation of key design decisions"
}}

Think step by step:
1. What is the primary mission/use case?
2. What drone type is best suited?
3. What are the payload and endurance requirements?
4. What environmental conditions must be handled?
5. What autonomy features are needed?
6. What regulations apply?

Respond ONLY with valid JSON, no markdown or additional text."""


class MissionAnalyzerAgent:
    """
    Agent for parsing mission statements and extracting requirements.
    Uses LLM to understand natural language and structured output for requirements.
    """
    
    def __init__(self, llm: BaseLanguageModel):
        """
        Initialize agent with LLM.
        
        Args:
            llm: Language model for analysis
        """
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_template(MISSION_ANALYZER_PROMPT)
        self.parser = JsonOutputParser()
    
    def analyze(
        self,
        mission_statement: str,
        cad_detail: Literal["basic", "detailed"] = "basic"
    ) -> MissionRequirements:
        """
        Analyze mission statement and extract requirements.
        
        Args:
            mission_statement: Natural language mission description
            cad_detail: Requested CAD detail level
            
        Returns:
            MissionRequirements dataclass with extracted requirements
        """
        logger.info("Analyzing mission statement...")
        
        # Prepare prompt
        chain = self.prompt | self.llm
        
        # Get LLM response
        response = chain.invoke({
            "mission_statement": mission_statement,
            "cad_detail": cad_detail
        })
        
        # Parse response
        try:
            # Handle different response types
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Clean response (remove markdown if present)
            response_text = self._clean_json_response(response_text)
            
            # Parse JSON
            parsed = json.loads(response_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response was: {response}")
            # Return default requirements
            return self._default_requirements(mission_statement, cad_detail)
        
        # Convert to MissionRequirements
        requirements = self._parse_to_requirements(parsed, mission_statement, cad_detail)
        
        logger.info(f"Mission analyzed: {requirements.drone_type.value} - {requirements.configuration}")
        
        return requirements
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from markdown and other artifacts"""
        # Remove markdown code blocks
        if "```json" in response:
            response = response.split("```json")[1]
            response = response.split("```")[0]
        elif "```" in response:
            response = response.split("```")[1]
            response = response.split("```")[0]
        
        # Strip whitespace
        response = response.strip()
        
        return response
    
    def _parse_to_requirements(
        self,
        parsed: Dict[str, Any],
        mission: str,
        cad_detail: str
    ) -> MissionRequirements:
        """Convert parsed JSON to MissionRequirements dataclass"""
        
        # Map drone type string to enum
        drone_type_map = {
            "multirotor": DroneType.MULTIROTOR,
            "fixed_wing": DroneType.FIXED_WING,
            "vtol": DroneType.VTOL,
            "hybrid": DroneType.HYBRID
        }
        
        drone_type = drone_type_map.get(
            parsed.get("drone_type", "multirotor").lower(),
            DroneType.MULTIROTOR
        )
        
        # Map configuration based on drone type
        config_str = parsed.get("configuration", "quadcopter").lower().replace("-", "_")
        
        if drone_type == DroneType.MULTIROTOR:
            config_map = {
                "quadcopter": MultirotorConfig.QUADCOPTER_X,
                "quadcopter_x": MultirotorConfig.QUADCOPTER_X,
                "quadcopter_plus": MultirotorConfig.QUADCOPTER_PLUS,
                "quadcopter_h": MultirotorConfig.QUADCOPTER_H,
                "hexacopter": MultirotorConfig.HEXACOPTER_X,
                "hexacopter_x": MultirotorConfig.HEXACOPTER_X,
                "hexacopter_plus": MultirotorConfig.HEXACOPTER_PLUS,
                "octocopter": MultirotorConfig.OCTOCOPTER_X,
                "octocopter_x": MultirotorConfig.OCTOCOPTER_X,
                "octocopter_plus": MultirotorConfig.OCTOCOPTER_PLUS,
                "octocopter_coax": MultirotorConfig.OCTOCOPTER_COAX,
                "tricopter": MultirotorConfig.TRICOPTER,
            }
            configuration = config_map.get(config_str, MultirotorConfig.QUADCOPTER_X).value
        elif drone_type == DroneType.FIXED_WING:
            config_map = {
                "conventional": FixedWingConfig.CONVENTIONAL,
                "flying_wing": FixedWingConfig.FLYING_WING,
                "delta": FixedWingConfig.DELTA,
                "canard": FixedWingConfig.CANARD,
                "biplane": FixedWingConfig.BIPLANE,
            }
            configuration = config_map.get(config_str, FixedWingConfig.CONVENTIONAL).value
        elif drone_type == DroneType.VTOL:
            config_map = {
                "quadplane": VTOLConfig.QUADPLANE,
                "tiltrotor": VTOLConfig.TILTROTOR_QUAD,
                "tiltrotor_quad": VTOLConfig.TILTROTOR_QUAD,
                "tiltrotor_tri": VTOLConfig.TILTROTOR_TRI,
                "tailsitter": VTOLConfig.TAILSITTER,
                "lift_cruise": VTOLConfig.LIFT_CRUISE
            }
            configuration = config_map.get(config_str, VTOLConfig.QUADPLANE).value
        else:
            configuration = config_str
        
        # Helper to get value falling back to default if value is None
        def get_val(key, default):
            val = parsed.get(key)
            return default if val is None else val

        # Map use_case from use_cases if use_case is missing
        use_cases = get_val("use_cases", [])
        use_case = get_val("use_case", None)
        if use_case is None and use_cases:
            use_case = use_cases[0]
        if use_case is None:
            use_case = "general"

        # Create requirements object
        requirements = MissionRequirements(
            drone_type=drone_type,
            configuration=configuration,
            use_case=use_case,
            payload_mass_kg=get_val("payload_capacity_kg", 0.5),
            payload_type=get_val("payload_type", "camera"),
            endurance_min=get_val("flight_time_minutes", 25),
            range_km=get_val("range_km", 5.0),
            max_speed_ms=get_val("max_speed_ms", 15.0),
            cruise_speed_ms=get_val("cruise_speed_ms", 10.0),
            max_altitude_m=get_val("max_altitude_m", 120),
            wind_resistance_ms=get_val("wind_resistance_ms", 10.0),
            temp_min_c=get_val("operating_temperature_min_c", 0),
            temp_max_c=get_val("operating_temperature_max_c", 45),
            obstacle_avoidance=get_val("obstacle_avoidance", False),
            return_to_home=get_val("return_to_home", True),
            waypoint_navigation=get_val("waypoint_navigation", True),
            geofencing=get_val("geofencing", True),
            beyond_vlos=get_val("bvlos", False),
            jurisdictions=get_val("jurisdictions", ["india_dgca"]),
            max_cost=get_val("budget_usd", None) if get_val("budget_usd", None) is not None else get_val("max_cost", 100000.0),
            currency=get_val("currency", "USD" if get_val("budget_usd", None) is not None else "INR"),
            cad_detail=cad_detail,
            assumptions=get_val("assumptions", [])
        )
        
        return requirements
    
    def _default_requirements(
        self,
        mission: str,
        cad_detail: str
    ) -> MissionRequirements:
        """Return default requirements when parsing fails with regex extraction fallback"""
        logger.warning("Using default requirements with regex fallback extraction due to parsing failure")
        
        # Regex search fallbacks
        payload = 0.5
        payload_match = re.search(r'(\d+(?:\.\d+)?)\s*k?g', mission.lower())
        if payload_match:
            try:
                payload = float(payload_match.group(1))
            except ValueError:
                pass
                
        endurance = 25
        endurance_match = re.search(r'(\d+)\s*(?:min|minute)', mission.lower())
        if endurance_match:
            try:
                endurance = int(endurance_match.group(1))
            except ValueError:
                pass
                
        budget = 100000.0
        currency = "INR"
        budget_match = re.search(r'(?:\$|usd)\s*(\d+(?:,\d+)?)', mission.lower())
        if budget_match:
            try:
                budget = float(budget_match.group(1).replace(',', ''))
                currency = "USD"
            except ValueError:
                pass
        else:
            budget_match_inr = re.search(r'(?:rs|inr|₹)\s*(\d+(?:,\d+)?)', mission.lower())
            if budget_match_inr:
                try:
                    budget = float(budget_match_inr.group(1).replace(',', ''))
                    currency = "INR"
                except ValueError:
                    pass
        
        return MissionRequirements(
            drone_type=DroneType.MULTIROTOR,
            configuration="quadcopter_x",
            use_case="general",
            payload_mass_kg=payload,
            endurance_min=endurance,
            range_km=5.0,
            max_speed_ms=15.0,
            cruise_speed_ms=10.0,
            max_altitude_m=120,
            wind_resistance_ms=10.0,
            temp_min_c=0,
            temp_max_c=45,
            obstacle_avoidance=False,
            return_to_home=True,
            waypoint_navigation=True,
            geofencing=True,
            beyond_vlos=False,
            jurisdictions=["india_dgca"],
            max_cost=budget,
            currency=currency,
            cad_detail=cad_detail,
            assumptions=["Using default values with regex extraction due to parsing failure"]
        )
    
    def validate_requirements(self, requirements: MissionRequirements) -> Dict[str, Any]:
        """
        Validate extracted requirements for consistency.
        
        Returns:
            Dict with validation status and any warnings/errors
        """
        warnings = []
        errors = []
        
        # Check physical constraints
        if requirements.payload_mass_kg > 25:
            warnings.append("Payload > 25kg may require special certifications")
        
        if requirements.max_altitude_m > 400:
            warnings.append("Altitude > 400ft (120m) typically requires special authorization")
        
        # Check logical constraints
        if requirements.range_km > 0 and requirements.endurance_min > 0:
            # Estimate if range is achievable with flight time
            min_cruise_speed_for_range = (requirements.range_km * 1000) / (requirements.endurance_min * 60)
            if min_cruise_speed_for_range > requirements.cruise_speed_ms:
                warnings.append(
                    f"Range {requirements.range_km}km may not be achievable in {requirements.endurance_min}min "
                    f"at cruise speed {requirements.cruise_speed_ms}m/s"
                )
        
        # Check BVLOS requirements
        if requirements.beyond_vlos:
            if not requirements.obstacle_avoidance:
                warnings.append("BVLOS typically requires obstacle avoidance")
        
        return {
            "valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors
        }
