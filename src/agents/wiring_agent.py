"""
DroneForge AI - Wiring Diagram Agent
Generates wiring diagrams and connection specifications.
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import asdict

logger = logging.getLogger(__name__)


class WiringAgent:
    """Agent for wiring design and diagram generation"""
    
    # Wire gauge recommendations by current
    WIRE_GAUGE_BY_CURRENT = [
        (5, 22, 'AWG 22'),
        (10, 20, 'AWG 20'),
        (15, 18, 'AWG 18'),
        (25, 16, 'AWG 16'),
        (40, 14, 'AWG 14'),
        (60, 12, 'AWG 12'),
        (80, 10, 'AWG 10'),
        (120, 8, 'AWG 8'),
        (200, 6, 'AWG 6'),
    ]
    
    # Common connector types
    CONNECTORS = {
        'xt60': {'max_current_a': 60, 'suitable_for': 'battery_main'},
        'xt90': {'max_current_a': 90, 'suitable_for': 'battery_main'},
        'xt30': {'max_current_a': 30, 'suitable_for': 'low_power'},
        'jst_xh': {'max_current_a': 3, 'suitable_for': 'balance_leads'},
        'jst_ph': {'max_current_a': 2, 'suitable_for': 'signals'},
        'servo': {'max_current_a': 5, 'suitable_for': 'servos'},
        'bullet_3.5mm': {'max_current_a': 30, 'suitable_for': 'motor'},
        'bullet_4mm': {'max_current_a': 50, 'suitable_for': 'motor'},
        'bullet_5.5mm': {'max_current_a': 80, 'suitable_for': 'motor'},
    }
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _get_wire_gauge(self, current_a: float) -> Tuple[int, str]:
        """Get appropriate wire gauge for given current"""
        for max_current, awg, label in self.WIRE_GAUGE_BY_CURRENT:
            if current_a <= max_current:
                return awg, label
        return 6, 'AWG 6'
    
    def _select_connector(self, purpose: str, current_a: float) -> Dict:
        """Select appropriate connector"""
        if purpose == 'battery' and current_a > 60:
            return {'type': 'xt90', 'max_current_a': 90}
        elif purpose == 'battery':
            return {'type': 'xt60', 'max_current_a': 60}
        elif purpose == 'motor' and current_a > 30:
            return {'type': 'bullet_4mm', 'max_current_a': 50}
        elif purpose == 'motor':
            return {'type': 'bullet_3.5mm', 'max_current_a': 30}
        elif purpose == 'signal':
            return {'type': 'jst_ph', 'max_current_a': 2}
        elif purpose == 'servo':
            return {'type': 'servo', 'max_current_a': 5}
        else:
            return {'type': 'jst_xh', 'max_current_a': 3}
    
    def _build_connection_table(self, electronics: Dict, 
                                propulsion: Dict,
                                power: Dict) -> List[Dict]:
        """Build connection table for all components"""
        connections = []
        
        fc = electronics.get('flight_controller', {})
        motor_count = propulsion.get('motor_count', 4)
        
        # Battery to PDB
        max_current = power.get('calculations', {}).get('max_current_a', 50)
        awg, label = self._get_wire_gauge(max_current)
        
        connections.append({
            'id': 1,
            'from_component': 'Battery',
            'from_port': 'Main output',
            'to_component': 'PDB',
            'to_port': 'Battery input',
            'wire_type': f'Silicone {label}',
            'wire_color': 'Red (+) / Black (-)',
            'connector': 'XT60/XT90',
            'notes': 'Main power connection'
        })
        
        # PDB to ESCs
        per_motor_current = max_current / motor_count
        motor_awg, motor_label = self._get_wire_gauge(per_motor_current)
        
        for i in range(motor_count):
            connections.append({
                'id': len(connections) + 1,
                'from_component': 'PDB',
                'from_port': f'Motor output {i+1}',
                'to_component': f'ESC {i+1}',
                'to_port': 'Power input',
                'wire_type': f'Silicone {motor_label}',
                'wire_color': 'Red (+) / Black (-)',
                'connector': 'Solder',
                'notes': f'Motor {i+1} power'
            })
        
        # ESCs to Motors
        for i in range(motor_count):
            connections.append({
                'id': len(connections) + 1,
                'from_component': f'ESC {i+1}',
                'from_port': 'Motor output (3-phase)',
                'to_component': f'Motor {i+1}',
                'to_port': 'Windings',
                'wire_type': 'Silicone AWG 16',
                'wire_color': 'Any (match phase order)',
                'connector': '3.5mm bullet',
                'notes': 'Swap any 2 to reverse direction'
            })
        
        # ESC signal wires to FC
        for i in range(motor_count):
            connections.append({
                'id': len(connections) + 1,
                'from_component': f'ESC {i+1}',
                'from_port': 'Signal',
                'to_component': 'Flight Controller',
                'to_port': f'Motor {i+1}',
                'wire_type': 'Servo wire AWG 26',
                'wire_color': 'White/Yellow (signal)',
                'connector': 'JST-SH',
                'notes': 'PWM/DSHOT signal'
            })
        
        # FC to GPS
        connections.append({
            'id': len(connections) + 1,
            'from_component': 'Flight Controller',
            'from_port': 'GPS UART',
            'to_component': 'GPS Module',
            'to_port': 'Serial',
            'wire_type': 'JST-GH cable',
            'wire_color': 'Standard',
            'connector': 'JST-GH',
            'notes': 'TX/RX crossed, 5V, GND'
        })
        
        # FC to Receiver
        rx = electronics.get('receiver', {})
        rx_protocol = rx.get('protocol', 'SBUS')
        
        connections.append({
            'id': len(connections) + 1,
            'from_component': 'Receiver',
            'from_port': 'Output',
            'to_component': 'Flight Controller',
            'to_port': 'RC input',
            'wire_type': 'Servo wire',
            'wire_color': 'Signal, 5V, GND',
            'connector': 'Servo/JST',
            'notes': f'{rx_protocol} protocol'
        })
        
        # FC to Telemetry
        connections.append({
            'id': len(connections) + 1,
            'from_component': 'Flight Controller',
            'from_port': 'TELEM UART',
            'to_component': 'Telemetry Radio',
            'to_port': 'Serial',
            'wire_type': 'JST-GH cable',
            'wire_color': 'Standard',
            'connector': 'JST-GH',
            'notes': 'TX/RX, 5V, GND'
        })
        
        # PDB BEC to FC
        connections.append({
            'id': len(connections) + 1,
            'from_component': 'PDB/BEC',
            'from_port': '5V output',
            'to_component': 'Flight Controller',
            'to_port': 'Power input',
            'wire_type': 'Silicone AWG 20',
            'wire_color': 'Red (+5V) / Black (GND)',
            'connector': 'Solder/JST',
            'notes': '5V regulated power'
        })
        
        return connections
    
    def _generate_wire_list(self, connections: List[Dict]) -> List[Dict]:
        """Generate list of wires needed"""
        wire_types = {}
        
        for conn in connections:
            wire_type = conn.get('wire_type', 'Unknown')
            if wire_type not in wire_types:
                wire_types[wire_type] = {
                    'type': wire_type,
                    'count': 0,
                    'length_estimate_m': 0
                }
            wire_types[wire_type]['count'] += 1
            wire_types[wire_type]['length_estimate_m'] += 0.3  # 30cm per connection
        
        return list(wire_types.values())
    
    def _generate_connector_list(self, connections: List[Dict]) -> List[Dict]:
        """Generate list of connectors needed"""
        connectors = {}
        
        for conn in connections:
            conn_type = conn.get('connector', 'Unknown')
            if conn_type not in connectors:
                connectors[conn_type] = {
                    'type': conn_type,
                    'quantity': 0,
                    'purpose': []
                }
            connectors[conn_type]['quantity'] += 1
            connectors[conn_type]['purpose'].append(conn.get('notes', ''))
        
        return list(connectors.values())
    
    def _generate_emi_notes(self, electronics: Dict) -> List[str]:
        """Generate EMI/EMC considerations"""
        notes = []
        
        notes.append("Keep GPS module away from ESCs and power wires (minimum 10cm)")
        notes.append("Route signal wires perpendicular to power wires where they cross")
        notes.append("Use twisted pairs for long signal runs")
        notes.append("Keep receiver antenna away from carbon fiber and metal")
        notes.append("Use ferrite beads on power leads to reduce noise")
        notes.append("Keep magnetometer/compass away from current-carrying wires")
        notes.append("Shield video transmitter cables if using analog")
        
        return notes
    
    def _generate_svg_diagram(self, connections: List[Dict], 
                             motor_count: int) -> str:
        """Generate basic SVG wiring diagram"""
        # This is a simplified representation
        # A full implementation would use a proper SVG library
        
        width = 800
        height = 600
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .component {{ fill: #e0e0e0; stroke: #333; stroke-width: 2; }}
      .label {{ font-family: Arial; font-size: 12px; fill: #333; }}
      .wire-power {{ stroke: #d32f2f; stroke-width: 3; fill: none; }}
      .wire-signal {{ stroke: #1976d2; stroke-width: 2; fill: none; }}
      .wire-ground {{ stroke: #333; stroke-width: 2; fill: none; }}
    </style>
  </defs>
  
  <!-- Title -->
  <text x="400" y="30" text-anchor="middle" style="font-size: 18px; font-weight: bold;">
    DroneForge AI - Wiring Diagram
  </text>
  
  <!-- Battery -->
  <rect x="350" y="500" width="100" height="50" class="component"/>
  <text x="400" y="530" text-anchor="middle" class="label">Battery</text>
  
  <!-- PDB -->
  <rect x="350" y="380" width="100" height="50" class="component"/>
  <text x="400" y="410" text-anchor="middle" class="label">PDB</text>
  
  <!-- Battery to PDB wire -->
  <line x1="400" y1="500" x2="400" y2="430" class="wire-power"/>
  
  <!-- Flight Controller -->
  <rect x="350" y="250" width="100" height="60" class="component"/>
  <text x="400" y="285" text-anchor="middle" class="label">Flight Controller</text>
  
  <!-- GPS -->
  <rect x="500" y="180" width="80" height="40" class="component"/>
  <text x="540" y="205" text-anchor="middle" class="label">GPS</text>
  <line x1="450" y1="270" x2="500" y2="200" class="wire-signal"/>
  
  <!-- Receiver -->
  <rect x="220" y="180" width="80" height="40" class="component"/>
  <text x="260" y="205" text-anchor="middle" class="label">Receiver</text>
  <line x1="350" y1="270" x2="300" y2="200" class="wire-signal"/>
  
  <!-- Telemetry -->
  <rect x="500" y="260" width="80" height="40" class="component"/>
  <text x="540" y="285" text-anchor="middle" class="label">Telemetry</text>
  <line x1="450" y1="280" x2="500" y2="280" class="wire-signal"/>
'''
        
        # Add ESC and Motor boxes
        positions = [
            (100, 350), (700, 350),  # Front ESCs
            (100, 450), (700, 450)   # Rear ESCs
        ]
        
        for i in range(min(motor_count, 4)):
            x, y = positions[i]
            svg += f'''
  <!-- ESC {i+1} -->
  <rect x="{x-30}" y="{y}" width="60" height="30" class="component"/>
  <text x="{x}" y="{y+20}" text-anchor="middle" class="label">ESC {i+1}</text>
  
  <!-- Motor {i+1} -->
  <circle cx="{x}" cy="{y-40}" r="25" class="component"/>
  <text x="{x}" y="{y-35}" text-anchor="middle" class="label">M{i+1}</text>
  
  <!-- ESC to Motor -->
  <line x1="{x}" y1="{y}" x2="{x}" y2="{y-15}" class="wire-power"/>
  
  <!-- PDB to ESC -->
  <line x1="350" y1="405" x2="{x}" y2="{y+15}" class="wire-power"/>
  
  <!-- FC to ESC signal -->
  <line x1="{'350' if x < 400 else '450'}" y1="280" x2="{x}" y2="{y}" class="wire-signal"/>
'''
        
        svg += '''
  <!-- Legend -->
  <rect x="20" y="550" width="200" height="40" fill="#f5f5f5" stroke="#ccc"/>
  <line x1="30" y1="565" x2="60" y2="565" class="wire-power"/>
  <text x="70" y="570" class="label">Power</text>
  <line x1="30" y1="580" x2="60" y2="580" class="wire-signal"/>
  <text x="70" y="585" class="label">Signal</text>
</svg>'''
        
        return svg
    
    def design(self, propulsion: Any, power: Any, electronics: Any, structure: Any) -> Any:
        """
        Design wiring system.
        
        Args:
            propulsion: Propulsion design
            power: Power design  
            electronics: Electronics design
            structure: Structural design
            
        Returns:
            WiringDesign dataclass
        """
        logger.info("Starting wiring design")
        
        # Convert to dict if dataclass
        if hasattr(electronics, '__dict__') and not isinstance(electronics, dict):
            electronics_dict = asdict(electronics)
        else:
            electronics_dict = electronics if isinstance(electronics, dict) else {}
            
        if hasattr(propulsion, '__dict__') and not isinstance(propulsion, dict):
            propulsion_dict = asdict(propulsion)
        else:
            propulsion_dict = propulsion if isinstance(propulsion, dict) else {}
            
        if hasattr(power, '__dict__') and not isinstance(power, dict):
            power_dict = asdict(power)
        else:
            power_dict = power if isinstance(power, dict) else {}
        
        motor_count = propulsion_dict.get('motor_count', 4)
        
        # Build connection table
        connections = self._build_connection_table(electronics_dict, propulsion_dict, power_dict)
        
        # Generate wire and connector lists
        wires = self._generate_wire_list(connections)
        connectors = self._generate_connector_list(connections)
        
        # Generate EMI notes
        emi_notes = self._generate_emi_notes(electronics_dict)
        
        # Generate SVG diagram
        svg = self._generate_svg_diagram(connections, motor_count)
        
        # Build wiring design result
        from ..core.state import WiringDesign
        
        result = WiringDesign(
            connection_table=connections,
            wire_gauge_recommendations=wires,
            connector_list=connectors,
            wiring_diagram_svg=svg,
            calculations={
                'total_connections': len(connections),
                'wire_types_count': len(wires),
                'connector_types_count': len(connectors),
                'emi_notes': emi_notes,
            },
            justifications=[
                f"Total {len(connections)} connections defined",
                f"Wire gauges selected based on current requirements",
                "Wiring diagram generated as SVG"
            ]
        )
        
        logger.info("Wiring design completed")
        return result
