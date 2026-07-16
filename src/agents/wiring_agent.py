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
        """Select appropriate connector using the CONNECTORS lookup table (BUG-070)"""
        if purpose == 'battery':
            if current_a > self.CONNECTORS['xt60']['max_current_a']:
                return {'type': 'xt90', 'max_current_a': self.CONNECTORS['xt90']['max_current_a']}
            return {'type': 'xt60', 'max_current_a': self.CONNECTORS['xt60']['max_current_a']}
        elif purpose == 'motor':
            if current_a > self.CONNECTORS['bullet_3.5mm']['max_current_a']:
                return {'type': 'bullet_4mm', 'max_current_a': self.CONNECTORS['bullet_4mm']['max_current_a']}
            return {'type': 'bullet_3.5mm', 'max_current_a': self.CONNECTORS['bullet_3.5mm']['max_current_a']}
        elif purpose == 'signal':
            return {'type': 'jst_ph', 'max_current_a': self.CONNECTORS['jst_ph']['max_current_a']}
        elif purpose == 'servo':
            return {'type': 'servo', 'max_current_a': self.CONNECTORS['servo']['max_current_a']}
        else:
            return {'type': 'jst_xh', 'max_current_a': self.CONNECTORS['jst_xh']['max_current_a']}
    
    def _build_connection_table(self, electronics: Dict, 
                                propulsion: Dict,
                                power: Dict) -> List[Dict]:
        """Build connection table for all components with electrical validation (BUG-022)"""
        connections = []
        
        fc = electronics.get('flight_controller', {})
        motor_count = propulsion.get('motor_count', 4)
        
        # Battery to PDB
        max_current = power.get('calculations', {}).get('max_current_a', 50)
        if max_current == 0:
            max_current = power.get('calculations', {}).get('power_budget', {}).get('total_max_w', 500) / max(
                power.get('total_voltage_v', 22.2), 1.0)
        awg, label = self._get_wire_gauge(max_current)
        
        # BUG-022: validate battery connector rating
        batt_connector_ok = max_current <= (90 if max_current > 60 else 60)
        batt_connector_type = 'XT90' if max_current > 60 else 'XT60'
        batt_connector_warning = '' if batt_connector_ok else (
            f'⚠ {max_current:.0f}A exceeds XT90 (90A) rating — use AS150 or parallel connectors'
        )
        
        connections.append({
            'id': 1,
            'from_component': 'Battery',
            'from_port': 'Main output',
            'to_component': 'PDB',
            'to_port': 'Battery input',
            'wire_type': f'Silicone {label}',
            'wire_awg': awg,
            'wire_color': 'Red (+) / Black (-)',
            'connector': batt_connector_type,
            'max_current_a': max_current,
            'notes': f'Main power connection [{max_current:.0f}A]{" | " + batt_connector_warning if batt_connector_warning else ""}'
        })
        
        # PDB to ESCs
        per_motor_current = max_current / motor_count
        motor_awg, motor_label = self._get_wire_gauge(per_motor_current)
        
        # BUG-022: validate motor bullet connector rating
        motor_bullet_rating = 80 if per_motor_current > 50 else (50 if per_motor_current > 30 else 30)
        motor_bullet_type = ('bullet_5.5mm' if per_motor_current > 50
                             else ('bullet_4mm' if per_motor_current > 30 else 'bullet_3.5mm'))
        motor_connector_warning = ''
        if per_motor_current > motor_bullet_rating:
            motor_connector_warning = (
                f'⚠ {per_motor_current:.0f}A/motor exceeds {motor_bullet_type} ({motor_bullet_rating}A) — use larger bullets'
            )
        
        for i in range(motor_count):
            connections.append({
                'id': len(connections) + 1,
                'from_component': 'PDB',
                'from_port': f'Motor output {i+1}',
                'to_component': f'ESC {i+1}',
                'to_port': 'Power input',
                'wire_type': f'Silicone {motor_label}',
                'wire_awg': motor_awg,
                'wire_color': 'Red (+) / Black (-)',
                'connector': 'Solder',
                'max_current_a': per_motor_current,
                'notes': f'Motor {i+1} power [{per_motor_current:.0f}A]'
            })
        
        # ESCs to Motors
        for i in range(motor_count):
            connections.append({
                'id': len(connections) + 1,
                'from_component': f'ESC {i+1}',
                'from_port': 'Motor output (3-phase)',
                'to_component': f'Motor {i+1}',
                'to_port': 'Windings',
                'wire_type': f'Silicone {motor_label}',
                'wire_awg': motor_awg,
                'wire_color': 'Any (match phase order)',
                'connector': motor_bullet_type.replace('bullet_', 'bullet '),
                'max_current_a': per_motor_current,
                'notes': f'Swap any 2 to reverse direction{" | " + motor_connector_warning if motor_connector_warning else ""}'
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
                'wire_awg': 26,
                'wire_color': 'White/Yellow (signal)',
                'connector': 'JST-SH',
                'max_current_a': 0.1,
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
            'wire_awg': 28,
            'wire_color': 'Standard',
            'connector': 'JST-GH',
            'max_current_a': 0.1,
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
            'wire_awg': 26,
            'wire_color': 'Signal, 5V, GND',
            'connector': 'Servo/JST',
            'max_current_a': 0.2,
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
            'wire_awg': 28,
            'wire_color': 'Standard',
            'connector': 'JST-GH',
            'max_current_a': 0.2,
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
            'wire_awg': 20,
            'wire_color': 'Red (+5V) / Black (GND)',
            'connector': 'Solder/JST',
            'max_current_a': 3.0,
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
        """Generate SVG wiring diagram with computed AWG labels (BUG-023)"""
        
        width = 800
        height = 660
        
        # Extract wire specs from connection table for annotation
        batt_awg = next((c.get('wire_awg', 10) for c in connections
                         if c.get('from_component') == 'Battery'), 10)
        motor_awg = next((c.get('wire_awg', 14) for c in connections
                          if 'ESC' in c.get('from_component', '')
                          and 'Motor' in c.get('to_component', '')), 14)
        batt_max_a = next((c.get('max_current_a', 50) for c in connections
                           if c.get('from_component') == 'Battery'), 50)
        per_motor_a = batt_max_a / max(motor_count, 1)
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .component {{ fill: #e0e0e0; stroke: #333; stroke-width: 2; }}
      .label {{ font-family: Arial; font-size: 12px; fill: #333; }}
      .awg-label {{ font-family: Arial; font-size: 9px; fill: #555; font-style: italic; }}
      .wire-power {{ stroke: #d32f2f; stroke-width: 3; fill: none; }}
      .wire-signal {{ stroke: #1976d2; stroke-width: 2; fill: none; }}
      .wire-ground {{ stroke: #333; stroke-width: 2; fill: none; }}
      .warning {{ fill: #ff6f00; font-size: 10px; }}
    </style>
  </defs>
  
  <!-- Title -->
  <text x="400" y="30" text-anchor="middle" style="font-size: 18px; font-weight: bold;">
    DroneForge AI - Wiring Diagram
  </text>
  
  <!-- Wire spec summary -->
  <text x="400" y="50" text-anchor="middle" class="awg-label">
    Main power: AWG {batt_awg} ({batt_max_a:.0f}A) | Per-motor: AWG {motor_awg} ({per_motor_a:.0f}A)
  </text>
  
  <!-- Battery -->
  <rect x="350" y="520" width="100" height="50" class="component"/>
  <text x="400" y="548" text-anchor="middle" class="label">Battery</text>
  
  <!-- PDB -->
  <rect x="350" y="400" width="100" height="50" class="component"/>
  <text x="400" y="428" text-anchor="middle" class="label">PDB</text>
  
  <!-- Battery to PDB wire with AWG label -->
  <line x1="400" y1="520" x2="400" y2="450" class="wire-power"/>
  <text x="410" y="490" class="awg-label">AWG {batt_awg}</text>
  
  <!-- Flight Controller -->
  <rect x="350" y="265" width="100" height="60" class="component"/>
  <text x="400" y="298" text-anchor="middle" class="label">Flight Controller</text>
  
  <!-- GPS -->
  <rect x="500" y="195" width="80" height="40" class="component"/>
  <text x="540" y="220" text-anchor="middle" class="label">GPS</text>
  <line x1="450" y1="285" x2="500" y2="215" class="wire-signal"/>
  
  <!-- Receiver -->
  <rect x="220" y="195" width="80" height="40" class="component"/>
  <text x="260" y="220" text-anchor="middle" class="label">Receiver</text>
  <line x1="350" y1="285" x2="300" y2="215" class="wire-signal"/>
  
  <!-- Telemetry -->
  <rect x="500" y="275" width="80" height="40" class="component"/>
  <text x="540" y="298" text-anchor="middle" class="label">Telemetry</text>
  <line x1="450" y1="295" x2="500" y2="295" class="wire-signal"/>
'''
        
        # Add ESC and Motor boxes with AWG labels on power wires
        positions = [
            (100, 370), (700, 370),  # Front ESCs
            (100, 460), (700, 460)   # Rear ESCs
        ]
        
        for i in range(min(motor_count, 4)):
            x, y = positions[i]
            svg += f'''
  <!-- ESC {i+1} -->
  <rect x="{x-30}" y="{y}" width="60" height="30" class="component"/>
  <text x="{x}" y="{y+20}" text-anchor="middle" class="label">ESC {i+1}</text>
  
  <!-- Motor {i+1} -->
  <circle cx="{x}" cy="{y-50}" r="25" class="component"/>
  <text x="{x}" y="{y-45}" text-anchor="middle" class="label">M{i+1}</text>
  
  <!-- ESC to Motor (AWG {motor_awg}) -->
  <line x1="{x}" y1="{y}" x2="{x}" y2="{y-25}" class="wire-power"/>
  <text x="{x+3}" y="{y-10}" class="awg-label">AWG {motor_awg}</text>
  
  <!-- PDB to ESC (AWG {motor_awg}) -->
  <line x1="350" y1="425" x2="{x}" y2="{y+15}" class="wire-power"/>
  
  <!-- FC to ESC signal (DSHOT) -->
  <line x1="{"350" if x < 400 else "450"}" y1="295" x2="{x}" y2="{y}" class="wire-signal"/>
'''
        
        svg += f'''
  <!-- Legend -->
  <rect x="20" y="580" width="350" height="70" fill="#f5f5f5" stroke="#ccc"/>
  <text x="30" y="597" class="label" font-weight="bold">Legend</text>
  <line x1="30" y1="610" x2="70" y2="610" class="wire-power"/>
  <text x="80" y="615" class="label">Power wire (AWG {batt_awg} main / AWG {motor_awg} motor)</text>
  <line x1="30" y1="630" x2="70" y2="630" class="wire-signal"/>
  <text x="80" y="635" class="label">Signal wire (AWG 26-28)</text>
  <text x="30" y="645" class="awg-label">Total system current: {batt_max_a:.0f}A | Per-motor: {per_motor_a:.0f}A</text>
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
            emi_notes=emi_notes,  # BUG-055: Map to top-level field
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
