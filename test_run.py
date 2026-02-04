#!/usr/bin/env python3
"""Test script to run the design workflow non-interactively"""

import sys
sys.path.insert(0, '.')

from src.core.workflow import DroneForgeWorkflow

# Initialize workflow with Ollama
workflow = DroneForgeWorkflow('ollama', model='llama3.1:8b')

# Run design
print("Starting drone design workflow...")
result = workflow.run(
    mission="hexacopter for photography with 1 hour flight time in INR 50000 according to DGCA regulations",
    cad_detail="basic",
    jurisdictions=["india_dgca"]
)

print("\n[SUCCESS] Design workflow completed!")
print(f"Output directory: {result.get('output_dir', 'output')}")
