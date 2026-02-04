<p align="center">
  <img src="https://img.shields.io/badge/DroneForge-AI-blue?style=for-the-badge&logo=drone" alt="DroneForge AI"/>
</p>

<h1 align="center">🚁 DroneForge AI</h1>

<p align="center">
  <strong>Multi-Agent LLM-Based System for Automated UAV Design</strong>
</p>

<p align="center">
  <a href="#features"><img src="https://img.shields.io/badge/Agents-17-green?style=flat-square" alt="17 Agents"/></a>
  <a href="#llm-providers"><img src="https://img.shields.io/badge/LLM-Ollama%20|%20OpenAI%20|%20Anthropic-orange?style=flat-square" alt="LLM Providers"/></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python" alt="Python 3.10+"/></a>
  <a href="https://python.langchain.com/docs/langgraph/"><img src="https://img.shields.io/badge/Framework-LangGraph-purple?style=flat-square" alt="LangGraph"/></a>
</p>

<p align="center">
  <em>Transform natural language mission requirements into complete, build-ready drone designs with physics-validated engineering specifications.</em>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Agent Details](#-agent-details)
- [Configuration](#-configuration)
- [Output Examples](#-output-examples)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**DroneForge AI** is an intelligent, multi-agent system that automates the entire UAV (drone) design process. Using Large Language Models (LLMs) orchestrated through LangGraph, it transforms natural language mission requirements into comprehensive, physics-validated drone designs.

### The Problem

Traditional drone design requires:
- **Multi-domain expertise**: Aerodynamics, propulsion, structural mechanics, power electronics, flight control
- **Weeks of engineering time**: Component selection, calculations, validation, documentation
- **Expensive prototyping cycles**: Design-build-test iterations

### The Solution

DroneForge AI provides:
- **End-to-end automation**: From mission statement to build-ready documentation
- **Physics-grounded design**: Embedded engineering calculations prevent hallucination
- **Complete deliverables**: CAD models, wiring diagrams, BOM, flight controller configs

---

## ✨ Key Features

### 🤖 17 Specialized AI Agents

| Phase | Agents | Description |
|-------|--------|-------------|
| **Requirements** | Mission Analyzer, Frame Topology | Parse natural language, select configuration |
| **Design** | Propulsion, Aerodynamics, Structural, Power, Electronics | Core engineering calculations |
| **Integration** | CoG, Autonomy, Software, Wiring, CAD, Regulatory | System integration & compliance |
| **Validation** | Validator, Optimizer, BOM, Documentation | Quality assurance & outputs |

### 🔬 Physics-Based Calculations

- **Thrust equations**: $T = C_T \cdot \rho \cdot n^2 \cdot D^4$
- **Structural analysis**: Beam bending, safety factors
- **Power budgeting**: Energy consumption, flight time estimation
- **Aerodynamic analysis**: Drag coefficients, stability margins

### 📦 Complete Output Generation

- ✅ **Parametric CAD models** (OpenSCAD, CadQuery)
- ✅ **Wiring diagrams** (SVG with connection tables)
- ✅ **Bill of Materials** with pricing and sources
- ✅ **Flight controller configuration** (ArduPilot/PX4 parameters)
- ✅ **Engineering justification report**
- ✅ **Regulatory compliance checklist**

### 🔄 Validation-Optimization Loop

Automatic design iteration until all validation criteria pass:
- Thrust-to-weight ratio ≥ 2.0
- Structural safety factor ≥ 2.0
- Flight time meets requirements
- CG within tolerance

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DRONEFORGE AI WORKFLOW                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│   │   Mission    │───▶│    Frame     │───▶│  Propulsion  │             │
│   │   Analyzer   │    │   Topology   │    │    Agent     │             │
│   └──────────────┘    └──────────────┘    └──────┬───────┘             │
│                                                   │                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐             │
│   │   Structural │◀───│  Aerodynamics│◀───│    Power     │             │
│   │    Agent     │    │    Agent     │    │    Agent     │             │
│   └──────┬───────┘    └──────────────┘    └──────────────┘             │
│          │                                                              │
│   ┌──────▼───────┐    ┌──────────────┐    ┌──────────────┐             │
│   │  Electronics │───▶│     CoG      │───▶│   Autonomy   │             │
│   │    Agent     │    │   Analysis   │    │    Agent     │             │
│   └──────────────┘    └──────────────┘    └──────┬───────┘             │
│                                                   │                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────▼───────┐             │
│   │  Regulatory  │◀───│     CAD      │◀───│   Software   │             │
│   │    Agent     │    │    Agent     │    │    Agent     │             │
│   └──────┬───────┘    └──────────────┘    └──────────────┘             │
│          │                                                              │
│   ┌──────▼───────┐    ┌──────────────┐    ┌──────────────┐             │
│   │  Validator   │───▶│  Optimizer   │───▶│     BOM      │             │
│   │    Agent     │    │    Agent     │    │   Generator  │             │
│   └──────┬───────┘    └──────────────┘    └──────┬───────┘             │
│          │                                        │                     │
│          │         ┌──────────────┐              │                     │
│          │         │ Feedback to  │◀─────────────┘                     │
│          └────────▶│ Propulsion   │ (if issues)                        │
│                    └──────────────┘                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 💻 Installation

### Prerequisites

- **Python 3.10+** (tested up to Python 3.14)
- **Ollama** (for local LLM inference) - [Install Ollama](https://ollama.com/download)
- **Git** (for version control)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/droneforge-ai.git
cd droneforge-ai
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install minimal dependencies for basic usage
pip install langgraph langchain langchain-community langchain-ollama numpy pyyaml flask
```

### Step 4: Setup Ollama (Local LLM)

```bash
# Pull the Llama 3.1 8B model (recommended)
ollama pull llama3.1:8b

# Or use a smaller model for faster inference
ollama pull llama3.2:3b
```

### Step 5: Verify Installation

```bash
python test_installation.py
```

Expected output:
```
✅ All tests passed! DroneForge AI is ready to use.
```

---

## 🚀 Quick Start

### Interactive CLI

```bash
python main.py
```

### Web Interface

```bash
python main.py --web
# Open http://localhost:5000 in your browser
```

### Programmatic Usage

```python
from src.core.workflow import DroneForgeWorkflow

# Initialize the workflow
workflow = DroneForgeWorkflow(llm_provider="ollama", model_name="llama3.1:8b")

# Define mission requirements
mission = """
Design a hexacopter drone for wildfire detection.
Requirements:
- Flight time: 2 hours minimum
- Payload: Thermal camera (500g) + RGB camera (200g)
- Operating altitude: 100-500m AGL
- Wind resistance: Up to 25 km/h
- Budget: Under ₹50,000
- Compliance: Indian DGCA regulations
- Features: GPS waypoint navigation, return-to-home
"""

# Generate the design
result = workflow.run(mission)

# Access outputs
print(f"Configuration: {result['frame_topology']['configuration']}")
print(f"Total Weight: {result['cog_analysis']['total_mass_kg']:.2f} kg")
print(f"Flight Time: {result['power_design']['estimated_flight_time_minutes']:.1f} min")
print(f"Estimated Cost: ₹{result['bom']['total_cost_inr']:,.0f}")
```

---

## 📖 Usage

### Command Line Options

```bash
python main.py [OPTIONS]

Options:
  --web                 Start web interface (default: CLI mode)
  --port PORT           Web server port (default: 5000)
  --llm PROVIDER        LLM provider: ollama, openai, anthropic (default: ollama)
  --model MODEL         Model name (default: llama3.1:8b)
  --output DIR          Output directory (default: ./output)
  --verbose             Enable verbose logging
  --help                Show help message
```

### Example Mission Statements

**Agricultural Drone:**
```
Design a quadcopter for precision agriculture.
Payload: 10L liquid tank for spraying
Flight time: 15 minutes per sortie
Coverage: 1 hectare per flight
Spray width: 4 meters
Budget: ₹1,50,000
Comply with Indian DGCA regulations
```

**Inspection Drone:**
```
Create a compact quadcopter for infrastructure inspection.
Payload: 4K camera gimbal (300g)
Endurance: 30 minutes
Max speed: 50 km/h
Obstacle avoidance required
Foldable design preferred
Budget: ₹80,000
```

**Long-Range Surveillance:**
```
Design an octocopter for border surveillance.
Payload: EO/IR camera system (2kg)
Endurance: 90 minutes
Operating range: 10km
All-weather operation
Encrypted communication
Budget: ₹5,00,000
```

---

## 📁 Project Structure

```
droneforge-ai/
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
├── test_installation.py        # Installation verification
├── test_run.py                 # Quick functionality test
│
├── src/                        # Source code
│   ├── __init__.py
│   ├── core/                   # Core framework
│   │   ├── state.py            # State dataclasses
│   │   ├── workflow.py         # LangGraph workflow
│   │   └── llm_providers.py    # LLM provider abstraction
│   │
│   ├── agents/                 # 17 specialized agents
│   │   ├── mission_analyzer.py
│   │   ├── frame_topology.py
│   │   ├── propulsion_agent.py
│   │   ├── aerodynamics_agent.py
│   │   ├── structural_agent.py
│   │   ├── power_agent.py
│   │   ├── electronics_agent.py
│   │   ├── cog_agent.py
│   │   ├── autonomy_agent.py
│   │   ├── software_agent.py
│   │   ├── wiring_agent.py
│   │   ├── cad_agent.py
│   │   ├── regulatory_agent.py
│   │   ├── validator_agent.py
│   │   ├── optimizer_agent.py
│   │   ├── report_generator.py
│   │   └── documentation_agent.py
│   │
│   └── simulation/             # Flight simulation
│       ├── standalone.py       # Python-based simulator
│       └── matlab_interface.py # MATLAB integration
│
├── config/                     # Configuration files
│   ├── settings.yaml           # General settings
│   ├── llm_config.yaml         # LLM provider config
│   └── regulations/            # Regulatory databases
│       ├── india_dgca.yaml
│       ├── usa_faa.yaml
│       └── eu_easa.yaml
│
├── databases/                  # Component databases
│   ├── motors/
│   ├── propellers/
│   ├── batteries/
│   ├── escs/
│   ├── flight_controllers/
│   ├── gps/
│   ├── frames/
│   ├── communication/
│   └── materials/
│
├── examples/                   # Example mission files
│   ├── photography_drone.json
│   ├── agricultural_sprayer.json
│   └── survey_fixed_wing.json
│
├── output/                     # Generated outputs
│   ├── complete_design.json
│   ├── bom.json
│   ├── cad/
│   ├── wiring/
│   └── software/
│
├── cli/                        # Command-line interface
│   └── main.py
│
└── web/                        # Web interface
    ├── app.py
    └── templates/
```

---

## 🤖 Agent Details

### Phase 1: Requirements Analysis

| Agent | Input | Output | Key Calculations |
|-------|-------|--------|------------------|
| **Mission Analyzer** | Natural language | Structured requirements | NLP parsing, constraint extraction |
| **Frame Topology** | Requirements | Configuration (quad/hexa/octo) | Motor count, wheelbase estimation |

### Phase 2: Core Design

| Agent | Input | Output | Key Calculations |
|-------|-------|--------|------------------|
| **Propulsion** | AUW, T/W ratio | Motors, props, ESCs | $T = C_T \rho n^2 D^4$, motor-prop matching |
| **Aerodynamics** | Configuration, speed | Drag analysis | $F_D = \frac{1}{2}\rho v^2 C_D A$ |
| **Structural** | AUW, dimensions | Frame design, materials | $\sigma = \frac{Mr}{I}$, safety factor |
| **Power** | Power consumption | Battery sizing | $E = P \cdot t$, C-rating check |
| **Electronics** | Requirements | FC, GPS, receiver | Component selection, compatibility |

### Phase 3: Integration

| Agent | Input | Output | Key Calculations |
|-------|-------|--------|------------------|
| **CoG Analysis** | All components | Mass properties | $\bar{x} = \frac{\sum m_i x_i}{\sum m_i}$, inertia tensor |
| **Autonomy** | Mission profile | Flight planning | Waypoints, geofencing |
| **Software** | FC selection | Parameters | ArduPilot/PX4 configuration |
| **Wiring** | All electronics | Wiring diagram | Wire gauge, connector selection |
| **CAD** | Frame design | 3D models | OpenSCAD, CadQuery generation |
| **Regulatory** | Jurisdiction | Compliance | DGCA/FAA/EASA requirements |

### Phase 4: Validation

| Agent | Input | Output | Key Calculations |
|-------|-------|--------|------------------|
| **Validator** | Complete design | Pass/fail, issues | Physics validation, compatibility checks |
| **Optimizer** | Validation issues | Adjusted design | Parameter optimization |
| **BOM Generator** | All components | Bill of Materials | Cost aggregation, vendor links |
| **Documentation** | Complete design | Reports | Engineering justification |

---

## ⚙️ Configuration

### LLM Configuration (`config/llm_config.yaml`)

```yaml
# Default provider
default_provider: ollama

# Ollama settings
ollama:
  base_url: http://localhost:11434
  model: llama3.1:8b
  temperature: 0.1
  timeout: 120

# OpenAI settings (requires API key)
openai:
  model: gpt-4
  temperature: 0.1
  api_key: ${OPENAI_API_KEY}

# Anthropic settings (requires API key)
anthropic:
  model: claude-3-sonnet
  temperature: 0.1
  api_key: ${ANTHROPIC_API_KEY}
```

### Safety Margins (`config/settings.yaml`)

```yaml
safety_margins:
  thrust_to_weight_min: 1.5
  thrust_to_weight_recommended: 2.0
  structural_safety_factor: 2.0
  battery_c_rating_margin: 1.2
  max_motor_temp_c: 80
  max_esc_temp_c: 85
```

---

## 📊 Output Examples

### Complete Design JSON

```json
{
  "mission_requirements": {
    "use_case": "fire_detection",
    "payload_kg": 0.7,
    "endurance_minutes": 120,
    "max_altitude_m": 500
  },
  "frame_topology": {
    "configuration": "hexacopter_x",
    "motor_count": 6,
    "wheelbase_mm": 960
  },
  "propulsion_design": {
    "motor": "EMAX RS2205 2300KV",
    "propeller": "Gemfan 5043",
    "esc": "T-Motor F55A Pro II"
  },
  "power_design": {
    "battery": "6S 40000mAh LiPo",
    "estimated_flight_time_minutes": 109.8
  },
  "validation_result": {
    "all_valid": true,
    "thrust_to_weight": 2.0,
    "safety_factor": 17.35
  },
  "bom": {
    "total_cost_inr": 138666,
    "components": [...]
  }
}
```

### Generated CAD (OpenSCAD)

```openscad
// DroneForge AI Generated - Hexacopter Frame
wheelbase = 960;  // mm
arm_length = 678.8;
arm_diameter = 25;

module arm() {
    difference() {
        cylinder(h=arm_length, d=arm_diameter);
        cylinder(h=arm_length+1, d=arm_diameter-4);
    }
}

module frame() {
    for(i=[0:5]) {
        rotate([0,0,i*60])
        rotate([0,90,0])
        arm();
    }
}

frame();
```

---

## 🔌 API Reference

### DroneForgeWorkflow

```python
class DroneForgeWorkflow:
    def __init__(
        self,
        llm_provider: str = "ollama",
        model_name: str = "llama3.1:8b",
        output_dir: str = "./output"
    )

    def run(self, mission_statement: str) -> dict:
        """Execute the full design workflow."""

    def run_partial(self, mission_statement: str, stop_after: str) -> dict:
        """Run workflow until specified agent."""

    def export_outputs(self, result: dict, format: str = "all") -> None:
        """Export design outputs to files."""
```

### State Classes

```python
@dataclass
class DroneDesignState:
    mission_statement: str
    mission_requirements: MissionRequirements
    frame_topology: FrameTopology
    propulsion_design: PropulsionDesign
    aerodynamics_analysis: AerodynamicsAnalysis
    structural_design: StructuralDesign
    power_design: PowerDesign
    electronics_design: ElectronicsDesign
    cog_analysis: CogAnalysis
    autonomy_config: AutonomyConfig
    software_config: SoftwareConfig
    wiring_design: WiringDesign
    cad_output: CadOutput
    regulatory_compliance: RegulatoryCompliance
    validation_result: ValidationResult
    optimization_result: OptimizationResult
    bom: BillOfMaterials
    documentation: Documentation
    iteration: int
```

---

## 🧪 Testing

```bash
# Run installation tests
python test_installation.py

# Run quick functionality test
python test_run.py

# Run full test suite (requires pytest)
pytest tests/ -v
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run code formatting
black src/
isort src/

# Run type checking
mypy src/
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangChain](https://www.langchain.com/) for the LLM framework
- [LangGraph](https://python.langchain.com/docs/langgraph/) for the agent orchestration
- [Ollama](https://ollama.com/) for local LLM inference
- [ArduPilot](https://ardupilot.org/) and [PX4](https://px4.io/) for flight controller references

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/droneforge-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/droneforge-ai/discussions)
- **Email**: your.email@example.com

---

<p align="center">
  <strong>Built with ❤️ for the drone community</strong>
</p>

<p align="center">
  <sub>DroneForge AI - Transforming ideas into flying machines</sub>
</p>
