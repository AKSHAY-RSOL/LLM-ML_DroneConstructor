"""
DroneForge AI - Core Package
Autonomous Drone Design System

An LLM-based multi-agent system for automated drone design.
Takes a natural language mission statement and generates a complete,
build-ready drone design with all components calculated and verified.
"""

__version__ = "1.0.0"
__author__ = "DroneForge AI Team"

from .core import DroneForgeWorkflow, DroneDesignState, LLMProviderFactory

__all__ = [
    "DroneForgeWorkflow",
    "DroneDesignState", 
    "LLMProviderFactory",
    "__version__"
]