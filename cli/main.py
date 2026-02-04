"""
DroneForge AI - Command Line Interface
Interactive CLI for drone design automation.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _to_dict(obj):
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


def print_banner():
    """Print the DroneForge AI banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     DRONE  DRONE  DRONE  DRONE  DRONE  DRONE  DRONE          ║
║     DRONE  DRONE  DRONE  DRONE  DRONE  DRONE  DRONE          ║
║     DRONE  DRONE  DRONE  DRONE  DRONE  DRONE  DRONE          ║
║     DRONE  DRONE  DRONE  DRONE  DRONE  DRONE  DRONE          ║
║     DRONE  DRONE  DRONE  DRONE  DRONE  DRONE  DRONE          ║
║     DRONE  DRONE  DRONE  DRONE  DRONE  DRONE  DRONE          ║
║                                                              ║
║     FORGE  FORGE  FORGE  FORGE  FORGE  FORGE  FORGE          ║
║     FORGE  FORGE  FORGE  FORGE  FORGE  FORGE  FORGE          ║
║     FORGE  FORGE  FORGE  FORGE  FORGE  FORGE  FORGE          ║
║     FORGE  FORGE  FORGE  FORGE  FORGE  FORGE  FORGE          ║
║     FORGE  FORGE  FORGE  FORGE  FORGE  FORGE  FORGE          ║
║     FORGE  FORGE  FORGE  FORGE  FORGE  FORGE  FORGE          ║
║                                                              ║
║          AI-Powered Drone Design System                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    try:
        # Try to encode with UTF-8 for better terminal support
        print(banner.encode('utf-8', errors='replace').decode('utf-8'))
    except Exception:
        # Fallback to simple ASCII-safe output
        print("=" * 60)
        print("DroneForge AI - AI-Powered Drone Design System")
        print("=" * 60)


def print_providers():
    """Print available LLM providers"""
    providers = {
        "ollama": "Local LLM (free, requires Ollama installed)",
        "openai": "OpenAI API (requires OPENAI_API_KEY)",
        "anthropic": "Anthropic Claude (requires ANTHROPIC_API_KEY)",
        "google": "Google Gemini (requires GOOGLE_API_KEY)",
        "azure": "Azure OpenAI (requires AZURE_OPENAI_API_KEY)"
    }
    
    print("\n📡 Available LLM Providers:")
    print("=" * 50)
    for name, desc in providers.items():
        print(f"  • {name}: {desc}")
    print()


def print_jurisdictions():
    """Print supported regulatory jurisdictions"""
    jurisdictions = {
        "india_dgca": "India - DGCA regulations",
        "usa_faa": "USA - FAA Part 107",
        "eu_easa": "European Union - EASA regulations"
    }
    
    print("\n🌍 Supported Regulatory Jurisdictions:")
    print("=" * 50)
    for code, desc in jurisdictions.items():
        print(f"  • {code}: {desc}")
    print()


def interactive_mode(
    provider: str = "ollama",
    model: Optional[str] = None,
    cad_detail: str = "basic",
    jurisdictions: list = None
) -> Dict[str, Any]:
    """
    Run interactive CLI mode with guided prompts.
    
    Returns:
        Configuration dict for the design
    """
    print_banner()
    
    print("\n[*] Welcome to DroneForge AI Interactive Mode!")
    print("=" * 60)
    print("\nI'll guide you through designing your custom drone.")
    print("Just answer a few questions and I'll generate a complete design.\n")
    
    # Get mission statement
    print("[*] Describe your drone mission in natural language.")
    print("   Include details like:")
    print("   - Type of drone (quadcopter, hexacopter, fixed-wing, etc.)")
    print("   - Payload requirements (camera, sensors, sprayer, etc.)")
    print("   - Flight time needed")
    print("   - Operating conditions")
    print("   - Budget (optional)")
    print()
    
    mission = input("Your mission: ").strip()
    
    if not mission:
        print("[X] Mission statement is required!")
        return None
    
    # Confirm settings
    print(f"\n[=] Design Settings:")
    print(f"   Provider: {provider}")
    print(f"   Model: {model or 'default'}")
    print(f"   CAD Detail: {cad_detail}")
    print(f"   Jurisdictions: {jurisdictions or ['india_dgca']}")
    
    confirm = input("\nProceed with design? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Design cancelled.")
        return None
    
    return {
        "mission": mission,
        "provider": provider,
        "model": model,
        "cad_detail": cad_detail,
        "jurisdictions": jurisdictions or ["india_dgca"]
    }


def run_design(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the drone design workflow.
    
    Args:
        config: Configuration dict with mission, provider, etc.
        
    Returns:
        Design result dict
    """
    from src.core.workflow import DroneForgeWorkflow
    
    print("\n" + "=" * 60)
    print("🚀 Starting Drone Design Workflow...")
    print("=" * 60 + "\n")
    
    # Create workflow
    workflow = DroneForgeWorkflow(
        llm_provider=config.get("provider", "ollama"),
        model=config.get("model"),
        output_dir=config.get("output_dir", "./output")
    )
    
    # Run design
    try:
        result = workflow.run(
            mission=config["mission"],
            cad_detail=config.get("cad_detail", "basic"),
            jurisdictions=config.get("jurisdictions", ["india_dgca"])
        )
        
        print("\n" + "=" * 60)
        print("[+] Design Complete!")
        print("=" * 60)
        
        # Print summary
        if result.get("bill_of_materials"):
            bom = _to_dict(result["bill_of_materials"])
            print(f"\n📦 Bill of Materials:")
            print(f"   Total Cost: {bom.get('total_cost', 'N/A')} {bom.get('currency', 'INR')}")
            print(f"   Total Weight: {bom.get('total_weight_g', 'N/A')}g")
            
        if result.get("validation_result"):
            validation = _to_dict(result["validation_result"])
            status = "[+] PASSED" if validation.get("passed") else "[X] FAILED"
            print(f"\n🔍 Validation: {status}")
            
        output_dir = config.get("output_dir", "./output")
        print(f"\n📁 Output saved to: {output_dir}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Design failed: {str(e)}")
        raise


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="DroneForge AI - CLI Interface"
    )
    
    parser.add_argument(
        "-m", "--mission",
        help="Mission statement for direct design"
    )
    
    parser.add_argument(
        "-p", "--provider",
        default="ollama",
        choices=["ollama", "openai", "anthropic", "google", "azure"],
        help="LLM provider"
    )
    
    parser.add_argument(
        "--model",
        help="LLM model name"
    )
    
    parser.add_argument(
        "--cad-detail",
        default="basic",
        choices=["basic", "detailed"],
        help="CAD detail level"
    )
    
    parser.add_argument(
        "-j", "--jurisdictions",
        nargs="+",
        default=["india_dgca"],
        help="Regulatory jurisdictions"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory"
    )
    
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available providers"
    )
    
    parser.add_argument(
        "--list-jurisdictions",
        action="store_true",
        help="List supported jurisdictions"
    )
    
    args = parser.parse_args()
    
    # Handle list commands
    if args.list_providers:
        print_providers()
        return
        
    if args.list_jurisdictions:
        print_jurisdictions()
        return
    
    # Direct mission mode
    if args.mission:
        config = {
            "mission": args.mission,
            "provider": args.provider,
            "model": args.model,
            "cad_detail": args.cad_detail,
            "jurisdictions": args.jurisdictions,
            "output_dir": args.output
        }
        run_design(config)
        return
    
    # Interactive mode
    config = interactive_mode(
        provider=args.provider,
        model=args.model,
        cad_detail=args.cad_detail,
        jurisdictions=args.jurisdictions
    )
    
    if config:
        config["output_dir"] = args.output
        run_design(config)


if __name__ == "__main__":
    main()
