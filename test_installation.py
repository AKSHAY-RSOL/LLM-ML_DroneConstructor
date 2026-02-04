#!/usr/bin/env python
"""
DroneForge AI - Installation Test
Verifies that all components are properly installed and accessible.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test all module imports"""
    print("🔍 Testing imports...")
    errors = []
    
    # Core modules
    try:
        from src.core.state import DroneDesignState, create_initial_state
        print("  ✅ src.core.state")
    except ImportError as e:
        errors.append(f"  ❌ src.core.state: {e}")
    
    try:
        from src.core.llm_providers import LLMProviderFactory
        print("  ✅ src.core.llm_providers")
    except ImportError as e:
        errors.append(f"  ❌ src.core.llm_providers: {e}")
    
    # Agent modules (test a few)
    agent_tests = [
        ("src.agents.mission_analyzer", "MissionAnalyzerAgent"),
        ("src.agents.propulsion_agent", "PropulsionAgent"),
        ("src.agents.power_agent", "PowerAgent"),
        ("src.agents.validator_agent", "ValidatorAgent"),
        ("src.agents.documentation_agent", "DocumentationAgent"),
    ]
    
    for module_name, class_name in agent_tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
        except ImportError as e:
            errors.append(f"  ❌ {module_name}: {e}")
    
    # Simulation modules
    try:
        from src.simulation.standalone import StandaloneSimulator
        print("  ✅ src.simulation.standalone")
    except ImportError as e:
        errors.append(f"  ❌ src.simulation.standalone: {e}")
    
    try:
        from src.simulation.matlab_interface import MatlabInterface
        print("  ✅ src.simulation.matlab_interface")
    except ImportError as e:
        errors.append(f"  ❌ src.simulation.matlab_interface: {e}")
    
    return errors


def test_databases():
    """Test database file existence"""
    print("\n🗄️ Testing databases...")
    
    db_path = Path(__file__).parent / "databases"
    databases = [
        "motors/motor_database.json",
        "propellers/propeller_database.json",
        "batteries/battery_database.json",
        "escs/esc_database.json",
        "flight_controllers/fc_database.json",
        "gps/gps_database.json",
        "frames/frame_database.json",
        "communication/communication_database.json",
        "materials/materials_database.json",
    ]
    
    errors = []
    for db in databases:
        db_file = db_path / db
        if db_file.exists():
            print(f"  ✅ {db}")
        else:
            errors.append(f"  ❌ {db} not found")
    
    return errors


def test_configs():
    """Test configuration file existence"""
    print("\n⚙️ Testing configuration files...")
    
    config_path = Path(__file__).parent / "config"
    configs = [
        "settings.yaml",
        "llm_config.yaml",
        "regulations/india_dgca.yaml",
        "regulations/usa_faa.yaml",
        "regulations/eu_easa.yaml",
    ]
    
    errors = []
    for cfg in configs:
        cfg_file = config_path / cfg
        if cfg_file.exists():
            print(f"  ✅ {cfg}")
        else:
            errors.append(f"  ❌ {cfg} not found")
    
    return errors


def test_dependencies():
    """Test critical dependencies"""
    print("\n📦 Testing dependencies...")
    
    deps = [
        ("numpy", "numpy"),
        ("yaml", "pyyaml"),
        ("flask", "flask"),
        ("json", "json (builtin)"),
    ]
    
    errors = []
    warnings = []
    
    for module_name, package_name in deps:
        try:
            __import__(module_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            errors.append(f"  ❌ {package_name} - pip install {package_name}")
    
    # Optional LLM dependencies
    optional = [
        ("langchain", "langchain"),
        ("langgraph", "langgraph"),
        ("langchain_community", "langchain-community"),
    ]
    
    for module_name, package_name in optional:
        try:
            __import__(module_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            warnings.append(f"  ⚠️ {package_name} - pip install {package_name} (required for LLM features)")
    
    return errors, warnings


def run_quick_test():
    """Run a quick functionality test"""
    print("\n🧪 Running quick functionality test...")
    
    errors = []
    
    try:
        from src.core.state import create_initial_state
        
        state = create_initial_state(
            mission_statement="Test drone for photography",
            cad_detail="basic",
            llm_provider="ollama",
            llm_model="llama3",
            output_dir="./test_output"
        )
        
        if state.get("mission_statement") == "Test drone for photography":
            print("  ✅ State creation works")
        else:
            errors.append("  ❌ State creation failed")
            
    except Exception as e:
        errors.append(f"  ❌ State creation error: {e}")
    
    try:
        from src.simulation.standalone import DroneConfig, StandaloneSimulator
        
        config = DroneConfig()
        sim = StandaloneSimulator(config)
        sim.reset()
        
        # Step a few times
        for _ in range(10):
            sim.step(throttle=0.5)
        
        print("  ✅ Simulator works")
        
    except Exception as e:
        errors.append(f"  ❌ Simulator error: {e}")
    
    return errors


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("       DroneForge AI - Installation Test")
    print("=" * 60)
    
    all_errors = []
    all_warnings = []
    
    # Run tests
    all_errors.extend(test_imports())
    all_errors.extend(test_databases())
    all_errors.extend(test_configs())
    
    dep_errors, dep_warnings = test_dependencies()
    all_errors.extend(dep_errors)
    all_warnings.extend(dep_warnings)
    
    all_errors.extend(run_quick_test())
    
    # Summary
    print("\n" + "=" * 60)
    print("                    Summary")
    print("=" * 60)
    
    if all_errors:
        print(f"\n❌ {len(all_errors)} errors found:")
        for err in all_errors:
            print(err)
    
    if all_warnings:
        print(f"\n⚠️ {len(all_warnings)} warnings:")
        for warn in all_warnings:
            print(warn)
    
    if not all_errors and not all_warnings:
        print("\n✅ All tests passed! DroneForge AI is ready to use.")
        print("\nQuick start:")
        print("  python main.py              # Interactive CLI")
        print("  python main.py --web        # Start web interface")
        print("  python main.py --help       # Show all options")
    elif not all_errors:
        print("\n✅ Core tests passed! Some optional dependencies missing.")
        print("\nTo install all dependencies:")
        print("  pip install -r requirements.txt")
    else:
        print("\n❌ Some tests failed. Please fix the errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
