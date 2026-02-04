"""
DroneForge AI - Main Workflow Engine
LangGraph-based multi-agent workflow for drone design automation.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Literal
from pathlib import Path

from langgraph.graph import StateGraph, END

from .state import (
    DroneDesignState,
    create_initial_state,
    MissionRequirements,
    PropulsionDesign,
    PowerDesign,
    ElectronicsDesign,
    StructuralDesign,
    AerodynamicsAnalysis,
    CenterOfGravity,
    AutonomyDesign,
    SoftwareConfig,
    WiringDesign,
    CADDesign,
    RegulatoryCompliance,
    ValidationResult,
    OptimizationResult,
    BillOfMaterials
)
from .llm_providers import LLMProviderFactory, LLMProvider

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DroneForgeWorkflow:
    """
    Main workflow orchestrator for drone design.
    Uses LangGraph to manage multi-agent workflow.
    """
    
    def __init__(
        self,
        llm_provider: str = "ollama",
        model: Optional[str] = None,
        temperature: float = 0.1,
        output_dir: str = "./output",
        **provider_kwargs
    ):
        """
        Initialize the workflow.
        
        Args:
            llm_provider: LLM provider name (ollama, openai, anthropic, google, azure)
            model: Model name (provider-specific)
            temperature: LLM temperature
            output_dir: Output directory for generated files
            **provider_kwargs: Additional provider-specific arguments
        """
        self.llm_provider_name = llm_provider
        self.model = model
        self.temperature = temperature
        self.output_dir = output_dir
        
        # Initialize LLM provider
        self.provider = LLMProviderFactory.create(
            llm_provider,
            temperature=temperature,
            **provider_kwargs
        )
        
        # Get LLM instances
        self.llm = self.provider.get_llm(model=model) if model else self.provider.get_llm()
        self.small_llm = self.provider.get_small_llm()
        
        # Build the workflow graph
        self.graph = self._build_graph()
        self.app = self.graph.compile()
        
        logger.info(f"DroneForge Workflow initialized with {llm_provider}")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create state graph
        graph = StateGraph(DroneDesignState)
        
        # Add nodes (agents)
        graph.add_node("mission_analyzer", self._mission_analyzer_node)
        graph.add_node("frame_topology", self._frame_topology_node)
        graph.add_node("propulsion", self._propulsion_node)
        graph.add_node("aerodynamics", self._aerodynamics_node)
        graph.add_node("structural", self._structural_node)
        graph.add_node("power", self._power_node)
        graph.add_node("electronics", self._electronics_node)
        graph.add_node("cog_analysis", self._cog_node)
        graph.add_node("autonomy", self._autonomy_node)
        graph.add_node("software", self._software_node)
        graph.add_node("wiring", self._wiring_node)
        graph.add_node("cad", self._cad_node)
        graph.add_node("regulatory", self._regulatory_node)
        graph.add_node("validator", self._validator_node)
        graph.add_node("optimizer", self._optimizer_node)
        graph.add_node("bom_generator", self._bom_generator_node)
        graph.add_node("documentation", self._documentation_node)
        
        # Set entry point
        graph.set_entry_point("mission_analyzer")
        
        # Add edges (workflow flow)
        graph.add_edge("mission_analyzer", "frame_topology")
        graph.add_edge("frame_topology", "propulsion")
        graph.add_edge("propulsion", "aerodynamics")
        graph.add_edge("aerodynamics", "structural")
        graph.add_edge("structural", "power")
        graph.add_edge("power", "electronics")
        graph.add_edge("electronics", "cog_analysis")
        graph.add_edge("cog_analysis", "autonomy")
        graph.add_edge("autonomy", "software")
        graph.add_edge("software", "wiring")
        graph.add_edge("wiring", "cad")
        graph.add_edge("cad", "regulatory")
        graph.add_edge("regulatory", "validator")
        
        # Conditional edge from validator
        graph.add_conditional_edges(
            "validator",
            self._should_optimize,
            {
                "optimize": "optimizer",
                "regenerate": "propulsion",  # Go back if major issues
                "continue": "bom_generator"
            }
        )
        
        graph.add_edge("optimizer", "bom_generator")
        graph.add_edge("bom_generator", "documentation")
        graph.add_edge("documentation", END)
        
        return graph
    
    def _should_optimize(self, state: DroneDesignState) -> str:
        """Decide whether to optimize, regenerate, or continue"""
        validation = state.get("validation_result", ValidationResult())
        
        if validation.critical_issues:
            logger.warning(f"Critical issues found: {validation.critical_issues}")
            iteration = state.get("iteration", 0)
            if iteration < 3:  # Max 3 iterations
                return "regenerate"
        
        if not validation.all_valid:
            return "optimize"
        
        return "continue"
    
    # ========================================================================
    # Agent Nodes
    # ========================================================================
    
    def _mission_analyzer_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Parse mission statement and extract requirements"""
        logger.info("🎯 Mission Analyzer Agent running...")
        
        mission_statement = state.get("mission_statement", "")
        cad_detail = state.get("cad_detail_level", "basic")
        
        # Import the agent
        from ..agents.mission_analyzer import MissionAnalyzerAgent
        
        agent = MissionAnalyzerAgent(self.llm)
        requirements = agent.analyze(mission_statement, cad_detail)
        
        return {
            "mission_requirements": requirements,
            "current_agent": "frame_topology"
        }
    
    def _frame_topology_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Determine frame topology based on requirements"""
        logger.info("🔧 Frame Topology Agent running...")
        
        from ..agents.frame_topology import FrameTopologyAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        agent = FrameTopologyAgent(self.llm)
        topology = agent.determine_topology(requirements)
        
        # Update requirements with topology
        requirements.configuration = topology.get("configuration", requirements.configuration)
        
        return {
            "mission_requirements": requirements,
            "current_agent": "propulsion"
        }
    
    def _propulsion_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Design propulsion system"""
        logger.info("🚀 Propulsion Agent running...")
        
        from ..agents.propulsion_agent import PropulsionAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        agent = PropulsionAgent(self.llm)
        propulsion = agent.design(requirements)
        
        return {
            "propulsion_design": propulsion,
            "current_agent": "aerodynamics"
        }
    
    def _aerodynamics_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Analyze aerodynamics"""
        logger.info("💨 Aerodynamics Agent running...")
        
        from ..agents.aerodynamics_agent import AerodynamicsAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        propulsion = state.get("propulsion_design", PropulsionDesign())
        
        agent = AerodynamicsAgent(self.llm)
        aero = agent.analyze(requirements, propulsion)
        
        return {
            "aerodynamics_analysis": aero,
            "current_agent": "structural"
        }
    
    def _structural_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Design structure"""
        logger.info("🏗️ Structural Agent running...")
        
        from ..agents.structural_agent import StructuralAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        propulsion = state.get("propulsion_design", PropulsionDesign())
        
        agent = StructuralAgent(self.llm)
        structure = agent.design(requirements, propulsion)
        
        return {
            "structural_design": structure,
            "current_agent": "power"
        }
    
    def _power_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Design power system"""
        logger.info("🔋 Power Agent running...")
        
        from ..agents.power_agent import PowerAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        propulsion = state.get("propulsion_design", PropulsionDesign())
        
        agent = PowerAgent(self.llm)
        power = agent.design(requirements, propulsion)
        
        return {
            "power_design": power,
            "current_agent": "electronics"
        }
    
    def _electronics_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Select electronics"""
        logger.info("⚡ Electronics Agent running...")
        
        from ..agents.electronics_agent import ElectronicsAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        propulsion = state.get("propulsion_design", PropulsionDesign())
        power = state.get("power_design", PowerDesign())
        
        agent = ElectronicsAgent(self.llm)
        electronics = agent.select(requirements, propulsion, power)
        
        return {
            "electronics_design": electronics,
            "current_agent": "cog_analysis"
        }
    
    def _cog_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Calculate center of gravity"""
        logger.info("⚖️ CoG Analysis Agent running...")
        
        from ..agents.cog_agent import CogAgent
        
        propulsion = state.get("propulsion_design", PropulsionDesign())
        structure = state.get("structural_design", StructuralDesign())
        power = state.get("power_design", PowerDesign())
        electronics = state.get("electronics_design", ElectronicsDesign())
        requirements = state.get("mission_requirements", MissionRequirements())
        
        agent = CogAgent(self.small_llm)
        cog = agent.analyze(propulsion, structure, power, electronics, requirements)
        
        return {
            "cog_analysis": cog,
            "current_agent": "autonomy"
        }
    
    def _autonomy_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Design autonomy features"""
        logger.info("🤖 Autonomy Agent running...")
        
        from ..agents.autonomy_agent import AutonomyAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        electronics = state.get("electronics_design", ElectronicsDesign())
        
        agent = AutonomyAgent(self.llm)
        autonomy = agent.design(requirements, electronics)
        
        return {
            "autonomy_design": autonomy,
            "current_agent": "software"
        }
    
    def _software_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Configure software/firmware"""
        logger.info("💻 Software Agent running...")
        
        from ..agents.software_agent import SoftwareAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        electronics = state.get("electronics_design", ElectronicsDesign())
        propulsion = state.get("propulsion_design", PropulsionDesign())
        autonomy = state.get("autonomy_design", AutonomyDesign())
        cog = state.get("cog_analysis", CenterOfGravity())
        
        agent = SoftwareAgent(self.llm)
        software = agent.configure(requirements, electronics, propulsion, autonomy, cog)
        
        return {
            "software_config": software,
            "current_agent": "wiring"
        }
    
    def _wiring_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Design wiring"""
        logger.info("🔌 Wiring Agent running...")
        
        from ..agents.wiring_agent import WiringAgent
        
        propulsion = state.get("propulsion_design", PropulsionDesign())
        power = state.get("power_design", PowerDesign())
        electronics = state.get("electronics_design", ElectronicsDesign())
        structure = state.get("structural_design", StructuralDesign())
        
        agent = WiringAgent(self.llm)
        wiring = agent.design(propulsion, power, electronics, structure)
        
        return {
            "wiring_design": wiring,
            "current_agent": "cad"
        }
    
    def _cad_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Generate CAD models"""
        logger.info("📐 CAD Agent running...")
        
        from ..agents.cad_agent import CADAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        structure = state.get("structural_design", StructuralDesign())
        propulsion = state.get("propulsion_design", PropulsionDesign())
        
        agent = CADAgent(self.llm)
        cad = agent.generate(
            requirements, 
            structure, 
            propulsion,
            detail_level=requirements.cad_detail
        )
        
        return {
            "cad_design": cad,
            "current_agent": "regulatory"
        }
    
    def _regulatory_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Check regulatory compliance"""
        logger.info("📋 Regulatory Agent running...")
        
        from ..agents.regulatory_agent import RegulatoryAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        cog = state.get("cog_analysis", CenterOfGravity())
        autonomy = state.get("autonomy_design", AutonomyDesign())
        electronics = state.get("electronics_design", ElectronicsDesign())
        
        agent = RegulatoryAgent(self.llm)
        compliance = agent.check_compliance(
            requirements,
            total_weight_kg=cog.all_up_weight_kg,
            autonomy=autonomy,
            electronics=electronics
        )
        
        return {
            "regulatory_compliance": compliance,
            "current_agent": "validator"
        }
    
    def _validator_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Validate entire design"""
        logger.info("✅ Validator Agent running...")
        
        from ..agents.validator_agent import ValidatorAgent
        
        agent = ValidatorAgent(self.llm)
        validation = agent.validate(state)
        
        iteration = state.get("iteration", 0) + 1
        
        return {
            "validation_result": validation,
            "iteration": iteration,
            "current_agent": "optimizer" if not validation.all_valid else "bom_generator"
        }
    
    def _optimizer_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Optimize design"""
        logger.info("🎯 Optimizer Agent running...")
        
        from ..agents.optimizer_agent import OptimizerAgent
        
        requirements = state.get("mission_requirements", MissionRequirements())
        validation = state.get("validation_result", ValidationResult())
        
        agent = OptimizerAgent(self.llm)
        optimization = agent.optimize(state, requirements, validation)
        
        return {
            "optimization_result": optimization,
            "current_agent": "bom_generator"
        }
    
    def _bom_generator_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Generate bill of materials"""
        logger.info("📦 BOM Generator running...")
        
        from ..agents.documentation_agent import DocumentationAgent
        
        agent = DocumentationAgent(self.small_llm)
        result = agent.generate(state)
        
        return {
            "bill_of_materials": result.get("bill_of_materials", {}),
            "documentation": result.get("documentation", {}),
            "current_agent": "documentation"
        }
    
    def _documentation_node(self, state: DroneDesignState) -> Dict[str, Any]:
        """Generate all documentation and save all output files"""
        logger.info("📄 Documentation Generator running...")
        
        from ..agents.documentation_agent import DocumentationAgent
        from pathlib import Path
        from dataclasses import asdict
        import json
        
        def to_dict(obj):
            """Convert dataclass to dict safely"""
            if obj is None:
                return {}
            if isinstance(obj, dict):
                return obj
            if hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return {}
        
        output_dir = state.get("output_directory", self.output_dir)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organized output
        cad_dir = Path(output_dir) / "cad"
        cad_dir.mkdir(exist_ok=True)
        
        software_dir = Path(output_dir) / "software"
        software_dir.mkdir(exist_ok=True)
        
        wiring_dir = Path(output_dir) / "wiring"
        wiring_dir.mkdir(exist_ok=True)
        
        # Get documentation from state
        documentation = state.get("documentation", {})
        if hasattr(documentation, '__dataclass_fields__'):
            documentation = to_dict(documentation)
        
        # Write build guide markdown
        build_guide = documentation.get("build_guide_md", "")
        if build_guide:
            guide_path = Path(output_dir) / "build_guide.md"
            with open(guide_path, 'w', encoding='utf-8') as f:
                f.write(build_guide)
            logger.info(f"Build guide saved to: {guide_path}")
        
        # Export BOM as JSON
        bom = state.get("bill_of_materials", {})
        if bom:
            bom_dict = to_dict(bom)
            bom_path = Path(output_dir) / "bom.json"
            with open(bom_path, 'w', encoding='utf-8') as f:
                json.dump(bom_dict, f, indent=2, default=str)
            logger.info(f"BOM saved to: {bom_path}")
        
        # ====== SAVE CAD FILES ======
        cad_design = state.get("cad_design")
        if cad_design:
            cad_dict = to_dict(cad_design)
            
            # Save OpenSCAD code
            cad_code = cad_dict.get("cad_code", {})
            if cad_code.get("openscad"):
                scad_path = cad_dir / "drone_frame.scad"
                with open(scad_path, 'w', encoding='utf-8') as f:
                    f.write(cad_code["openscad"])
                logger.info(f"OpenSCAD file saved to: {scad_path}")
            
            # Save CadQuery code
            if cad_code.get("cadquery"):
                cadquery_path = cad_dir / "drone_frame_cadquery.py"
                with open(cadquery_path, 'w', encoding='utf-8') as f:
                    f.write(cad_code["cadquery"])
                logger.info(f"CadQuery file saved to: {cadquery_path}")
            
            # Save frame parameters as JSON
            params = cad_dict.get("frame_parameters", {})
            if params:
                params_path = cad_dir / "frame_parameters.json"
                with open(params_path, 'w', encoding='utf-8') as f:
                    json.dump(params, f, indent=2)
                logger.info(f"Frame parameters saved to: {params_path}")
            
            # Save print settings
            print_settings = cad_dict.get("print_settings", {})
            if print_settings:
                print_path = cad_dir / "3d_print_settings.json"
                with open(print_path, 'w', encoding='utf-8') as f:
                    json.dump(print_settings, f, indent=2)
                logger.info(f"3D print settings saved to: {print_path}")
            
            # Save assembly notes
            assembly_notes = cad_dict.get("assembly_notes", [])
            if assembly_notes:
                notes_path = cad_dir / "assembly_notes.txt"
                with open(notes_path, 'w', encoding='utf-8') as f:
                    f.write("DRONE FRAME ASSEMBLY NOTES\n")
                    f.write("=" * 40 + "\n\n")
                    for note in assembly_notes:
                        f.write(f"• {note}\n")
                logger.info(f"Assembly notes saved to: {notes_path}")
        
        # ====== SAVE WIRING DIAGRAM ======
        wiring_design = state.get("wiring_design")
        if wiring_design:
            wiring_dict = to_dict(wiring_design)
            
            # Save SVG wiring diagram
            svg = wiring_dict.get("wiring_diagram_svg", "")
            if svg:
                svg_path = wiring_dir / "wiring_diagram.svg"
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg)
                logger.info(f"Wiring diagram saved to: {svg_path}")
            
            # Save connection table as JSON
            connections = wiring_dict.get("connection_table", [])
            if connections:
                conn_path = wiring_dir / "connection_table.json"
                with open(conn_path, 'w', encoding='utf-8') as f:
                    json.dump(connections, f, indent=2)
                logger.info(f"Connection table saved to: {conn_path}")
            
            # Save wire list
            wires = wiring_dict.get("wire_gauge_recommendations", [])
            if wires:
                wire_path = wiring_dir / "wire_list.json"
                with open(wire_path, 'w', encoding='utf-8') as f:
                    json.dump(wires, f, indent=2)
                logger.info(f"Wire list saved to: {wire_path}")
            
            # Save connector list
            connectors = wiring_dict.get("connector_list", [])
            if connectors:
                conn_list_path = wiring_dir / "connector_list.json"
                with open(conn_list_path, 'w', encoding='utf-8') as f:
                    json.dump(connectors, f, indent=2)
                logger.info(f"Connector list saved to: {conn_list_path}")
        
        # ====== SAVE SOFTWARE CONFIG ======
        software_config = state.get("software_config")
        if software_config:
            sw_dict = to_dict(software_config)
            
            # Save config files (ArduPilot params, PX4 params, Betaflight CLI)
            config_files = sw_dict.get("config_files", {})
            for name, content in config_files.items():
                if content:
                    # Determine extension based on firmware type
                    firmware = sw_dict.get("firmware_type", "ardupilot").lower()
                    if "betaflight" in firmware:
                        ext = ".txt"
                    else:
                        ext = ".param"
                    config_path = software_dir / f"{name}{ext}"
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Config file saved to: {config_path}")
            
            # Save PID values
            pids = sw_dict.get("pid_values", {})
            if pids:
                pid_path = software_dir / "pid_values.json"
                with open(pid_path, 'w', encoding='utf-8') as f:
                    json.dump(pids, f, indent=2)
                logger.info(f"PID values saved to: {pid_path}")
            
            # Save flight modes
            modes = sw_dict.get("flight_modes", [])
            if modes:
                modes_path = software_dir / "flight_modes.json"
                with open(modes_path, 'w', encoding='utf-8') as f:
                    json.dump(modes, f, indent=2)
                logger.info(f"Flight modes saved to: {modes_path}")
            
            # Save failsafe config
            failsafe = sw_dict.get("failsafe_config", {})
            if failsafe:
                failsafe_path = software_dir / "failsafe_config.json"
                with open(failsafe_path, 'w', encoding='utf-8') as f:
                    json.dump(failsafe, f, indent=2)
                logger.info(f"Failsafe config saved to: {failsafe_path}")
            
            # Save complete software config summary
            summary_path = software_dir / "software_config_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(sw_dict, f, indent=2, default=str)
            logger.info(f"Software config summary saved to: {summary_path}")
        
        # ====== SAVE COMPLETE STATE ======
        # Save complete design state as JSON for reference
        try:
            full_state = {}
            for key, value in state.items():
                full_state[key] = to_dict(value) if not isinstance(value, (str, int, float, bool, list, type(None))) else value
            
            state_path = Path(output_dir) / "complete_design.json"
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(full_state, f, indent=2, default=str)
            logger.info(f"Complete design saved to: {state_path}")
        except Exception as e:
            logger.warning(f"Could not save complete state: {e}")
        
        # ====== GENERATE ENGINEERING JUSTIFICATION REPORT ======
        try:
            from ..agents.report_generator import ReportGenerator
            
            report_gen = ReportGenerator()
            report_md = report_gen.generate_full_report(full_state)
            
            report_path = Path(output_dir) / "ENGINEERING_JUSTIFICATION_REPORT.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_md)
            logger.info(f"Engineering Justification Report saved to: {report_path}")
        except Exception as e:
            logger.warning(f"Could not generate engineering report: {e}")
        
        logger.info(f"✅ All documentation generated at: {output_dir}")
        
        return {
            "current_agent": "complete"
        }
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def run(
        self,
        mission: str,
        cad_detail: Literal["basic", "detailed"] = "basic",
        jurisdictions: Optional[List[str]] = None,
        output_dir: Optional[str] = None
    ) -> DroneDesignState:
        """
        Run the complete drone design workflow.
        
        Args:
            mission: Natural language mission statement
            cad_detail: CAD detail level ("basic" or "detailed")
            jurisdictions: List of regulatory jurisdictions to check
            output_dir: Output directory (overrides default)
            
        Returns:
            Final DroneDesignState with complete design
        """
        # Create initial state
        out_dir = output_dir or self.output_dir
        state = create_initial_state(
            mission_statement=mission,
            cad_detail=cad_detail,
            llm_provider=self.llm_provider_name,
            llm_model=self.model or "",
            output_dir=out_dir
        )
        
        # Add jurisdictions if provided
        if jurisdictions:
            state["mission_requirements"].jurisdictions = jurisdictions
        
        # Create output directory
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info("=" * 60)
        logger.info("🚁 DroneForge AI - Starting Design Workflow")
        logger.info("=" * 60)
        logger.info(f"Mission: {mission[:100]}...")
        logger.info(f"CAD Detail: {cad_detail}")
        logger.info(f"Output: {out_dir}")
        logger.info("=" * 60)
        
        # Run workflow
        final_state = self.app.invoke(state)
        
        logger.info("=" * 60)
        logger.info("✅ DroneForge AI - Design Complete!")
        logger.info("=" * 60)
        
        return final_state
    
    def run_agent(
        self,
        agent_name: str,
        state: DroneDesignState
    ) -> DroneDesignState:
        """Run a single agent for testing/debugging"""
        agent_methods = {
            "mission_analyzer": self._mission_analyzer_node,
            "frame_topology": self._frame_topology_node,
            "propulsion": self._propulsion_node,
            "aerodynamics": self._aerodynamics_node,
            "structural": self._structural_node,
            "power": self._power_node,
            "electronics": self._electronics_node,
            "cog_analysis": self._cog_node,
            "autonomy": self._autonomy_node,
            "software": self._software_node,
            "wiring": self._wiring_node,
            "cad": self._cad_node,
            "regulatory": self._regulatory_node,
            "validator": self._validator_node,
            "optimizer": self._optimizer_node,
            "bom_generator": self._bom_generator_node,
            "documentation": self._documentation_node,
        }
        
        if agent_name not in agent_methods:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        result = agent_methods[agent_name](state)
        state.update(result)
        return state
    
    def export_state(self, state: DroneDesignState, filepath: str) -> None:
        """Export state to JSON file"""
        # Convert dataclasses to dicts
        export_data = {}
        for key, value in state.items():
            if hasattr(value, "__dict__"):
                export_data[key] = value.__dict__
            else:
                export_data[key] = value
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"State exported to: {filepath}")
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get information about the workflow"""
        return {
            "llm_provider": self.llm_provider_name,
            "model": self.model,
            "output_dir": self.output_dir,
            "agents": [
                "mission_analyzer",
                "frame_topology", 
                "propulsion",
                "aerodynamics",
                "structural",
                "power",
                "electronics",
                "cog_analysis",
                "autonomy",
                "software",
                "wiring",
                "cad",
                "regulatory",
                "validator",
                "optimizer",
                "bom_generator",
                "documentation"
            ]
        }
