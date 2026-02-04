#!/usr/bin/env python
"""
DroneForge AI - Main Entry Point
LLM-based multi-agent drone design automation system.

Usage:
    python main.py                      # Interactive CLI mode
    python main.py --web                # Start web server
    python main.py -m "mission..."      # Direct CLI with mission
    python main.py --help               # Show help

Author: DroneForge AI Team
License: MIT
"""

import sys
import argparse
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DroneForge AI - LLM-based Drone Design Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           DroneForge AI                                      ║
║                                                                              ║
║   An AI-powered multi-agent system that takes a natural language mission    ║
║   statement and generates a complete, build-ready drone design including:   ║
║                                                                              ║
║   • Propulsion system (motors, props, ESCs)                                 ║
║   • Frame design with stress analysis                                       ║
║   • Power system with battery sizing                                        ║
║   • Electronics selection (FC, GPS, telemetry)                              ║
║   • Software/firmware configuration                                         ║
║   • CAD models (OpenSCAD/CadQuery)                                          ║
║   • Wiring diagrams                                                         ║
║   • Regulatory compliance check                                             ║
║   • Complete BOM with pricing                                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Examples:
    # Start interactive CLI
    python main.py
    
    # Start web interface
    python main.py --web
    python main.py --web --port 8080
    
    # Direct design from command line
    python main.py -m "Agricultural survey drone with 45min flight time, 500g camera payload"
    
    # Use specific LLM provider
    python main.py -m "..." --provider openai --model gpt-4
    
    # Detailed CAD with specific jurisdiction
    python main.py -m "..." --cad-detail detailed -j usa_faa eu_easa
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--web",
        action="store_true",
        help="Start web interface instead of CLI"
    )
    mode_group.add_argument(
        "-m", "--mission",
        type=str,
        help="Mission statement for direct design (skip interactive mode)"
    )
    mode_group.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Force interactive CLI mode"
    )
    
    # Web server options
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Web server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web server port (default: 5000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for web server"
    )
    
    # LLM options
    parser.add_argument(
        "-p", "--provider",
        type=str,
        default="ollama",
        choices=["ollama", "openai", "anthropic", "google", "azure"],
        help="LLM provider (default: ollama)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="LLM model name"
    )
    
    # Design options
    parser.add_argument(
        "--cad-detail",
        type=str,
        default="basic",
        choices=["basic", "detailed"],
        help="CAD detail level (default: basic)"
    )
    parser.add_argument(
        "-j", "--jurisdictions",
        type=str,
        nargs="+",
        default=["india_dgca"],
        help="Regulatory jurisdictions (default: india_dgca)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output directory"
    )
    
    # Info options
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available LLM providers"
    )
    parser.add_argument(
        "--list-jurisdictions",
        action="store_true",
        help="List supported regulatory jurisdictions"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="DroneForge AI v1.0.0"
    )
    
    args = parser.parse_args()
    
    # Handle info flags
    if args.list_providers:
        from cli.main import print_providers
        print_providers()
        return
    
    if args.list_jurisdictions:
        from cli.main import print_jurisdictions
        print_jurisdictions()
        return
    
    # Web mode
    if args.web:
        from web.app import run_server
        run_server(host=args.host, port=args.port, debug=args.debug)
        return
    
    # CLI mode
    from cli.main import main as cli_main, interactive_mode, run_design, print_banner
    from datetime import datetime
    
    if args.mission:
        # Direct design mode
        output_dir = args.output or f"./output/drone_design_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        config = {
            "mission": args.mission,
            "provider": args.provider,
            "model": args.model or ("llama3" if args.provider == "ollama" else "gpt-4"),
            "cad_detail": args.cad_detail,
            "jurisdictions": args.jurisdictions,
            "output_dir": output_dir
        }
        
        print_banner()
        run_design(config)
    else:
        # Interactive mode
        config = interactive_mode()
        if config:
            run_design(config)


if __name__ == "__main__":
    main()
