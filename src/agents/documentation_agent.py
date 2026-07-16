"""
DroneForge AI - Documentation Agent
Generates comprehensive build documentation and BOM.
"""

import json
import logging
from typing import Dict, Any, List
from dataclasses import asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentationAgent:
    """Agent for documentation generation"""
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
    
    def _to_dict(self, obj):
        """Convert dataclass to dict"""
        if hasattr(obj, '__dict__') and not isinstance(obj, dict):
            return asdict(obj)
        return obj if isinstance(obj, dict) else {}
    
    def _generate_bom(self, state: Dict[str, Any]) -> Dict:
        """Generate complete Bill of Materials"""
        items = []
        
        propulsion = self._to_dict(state.get('propulsion_design', {}))
        power = self._to_dict(state.get('power_design', {}))
        electronics = self._to_dict(state.get('electronics_design', {}))
        structural = self._to_dict(state.get('structural_design', {}))
        
        motor_count = propulsion.get('motor_count', 4)
        
        # Price and brand helper functions (BUG-057 / BUG-058)
        def get_price(item, default):
            if not item: return default
            if 'price_usd' in item: return item['price_usd']
            specs = item.get('specs', {})
            if 'price_usd' in specs: return specs['price_usd']
            price_obj = item.get('price', {})
            if isinstance(price_obj, dict): return price_obj.get('usd', default)
            if isinstance(price_obj, (int, float)): return price_obj
            return default

        def get_item_name(item, default_model):
            if not item: return default_model
            brand = item.get('brand', item.get('manufacturer', ''))
            model = item.get('model', default_model)
            if brand:
                return f"{brand} {model}".strip()
            return model

        # Motors
        motors = propulsion.get('motors', [])
        if motors:
            motor = motors[0]
            unit_price = get_price(motor, 30)
            items.append({
                'category': 'Propulsion',
                'item': get_item_name(motor, 'Motor'),
                'specification': f"{motor.get('specs', {}).get('kv', '')}KV",
                'quantity': motor_count,
                'unit_price': unit_price,
                'total_price': unit_price * motor_count,
                'source': motor.get('id', ''),
                'notes': ''
            })
        
        # Propellers
        props = propulsion.get('propellers', [])
        if props:
            prop = props[0]
            qty = motor_count * 2  # Include spares
            unit_price = get_price(prop, 5)
            items.append({
                'category': 'Propulsion',
                'item': get_item_name(prop, 'Propeller'),
                'specification': f"{prop.get('size_inch', '')}x{prop.get('pitch_inch', '')}",
                'quantity': qty,
                'unit_price': unit_price,
                'total_price': unit_price * qty,
                'source': prop.get('id', ''),
                'notes': 'Includes spare set'
            })
        
        # ESCs
        escs = propulsion.get('escs', [])
        if escs:
            esc = escs[0]
            unit_price = get_price(esc, 20)
            items.append({
                'category': 'Propulsion',
                'item': get_item_name(esc, 'ESC'),
                'specification': f"{esc.get('specs', {}).get('current_rating_a', '')}A",
                'quantity': motor_count,
                'unit_price': unit_price,
                'total_price': unit_price * motor_count,
                'source': esc.get('id', ''),
                'notes': ''
            })
        
        # Battery
        battery = power.get('battery', {})
        if battery:
            specs = battery.get('specs', {})
            unit_price = get_price(battery, 100)
            
            items.append({
                'category': 'Power',
                'item': get_item_name(battery, 'Battery'),
                'specification': f"{specs.get('cell_count', 6)}S {specs.get('capacity_mah', 5000)}mAh",
                'quantity': 1,
                'unit_price': unit_price,
                'total_price': unit_price,
                'source': battery.get('id', ''),
                'notes': 'Consider buying spare'
            })
        
        # Flight Controller
        fc = electronics.get('flight_controller', {})
        if fc:
            unit_price = get_price(fc, 100)
            
            items.append({
                'category': 'Electronics',
                'item': get_item_name(fc, 'FC'),
                'specification': fc.get('specs', {}).get('processor', ''),
                'quantity': 1,
                'unit_price': unit_price,
                'total_price': unit_price,
                'source': fc.get('id', ''),
                'notes': ''
            })
        
        # GPS
        gps = electronics.get('gps_module', {}) or electronics.get('gps', {})
        if gps:
            unit_price = get_price(gps, 50)
            items.append({
                'category': 'Electronics',
                'item': get_item_name(gps, 'GPS'),
                'specification': gps.get('specs', {}).get('chipset', ''),
                'quantity': 1,
                'unit_price': unit_price,
                'total_price': unit_price,
                'source': gps.get('id', ''),
                'notes': ''
            })
        
        # Receiver
        rx = electronics.get('receiver', {})
        if rx:
            unit_price = get_price(rx, 30)
            items.append({
                'category': 'Electronics',
                'item': get_item_name(rx, 'Receiver'),
                'specification': rx.get('protocol', ''),
                'quantity': 1,
                'unit_price': unit_price,
                'total_price': unit_price,
                'source': rx.get('id', ''),
                'notes': ''
            })
        
        # Telemetry
        telem = electronics.get('telemetry_system', {}) or electronics.get('telemetry', {})
        if telem:
            unit_price = get_price(telem, 50)
            items.append({
                'category': 'Electronics',
                'item': get_item_name(telem, 'Telemetry'),
                'specification': f"{telem.get('specs', {}).get('frequency_mhz', '')}MHz",
                'quantity': 1,
                'unit_price': unit_price,
                'total_price': unit_price,
                'source': telem.get('id', ''),
                'notes': 'Air + Ground pair'
            })
        
        # PDB
        pdb = electronics.get('pdb', {})
        if pdb:
            unit_price = get_price(pdb, 30)
            items.append({
                'category': 'Electronics',
                'item': get_item_name(pdb, 'PDB'),
                'specification': f"{pdb.get('specs', {}).get('max_current_a', '')}A",
                'quantity': 1,
                'unit_price': unit_price,
                'total_price': unit_price,
                'source': pdb.get('id', ''),
                'notes': ''
            })
        
        # Additional sensors
        sensors = electronics.get('additional_sensors', [])
        for sensor in sensors:
            qty = sensor.get('quantity', 1)
            items.append({
                'category': 'Electronics',
                'item': f"{sensor.get('brand', '')} {sensor.get('model', '')}",
                'specification': sensor.get('type', ''),
                'quantity': qty,
                'unit_price': sensor.get('price_usd', 0),
                'total_price': sensor.get('price_usd', 0) * qty,
                'source': sensor.get('id', ''),
                'notes': ''
            })
        
        # Companion computer
        companion = electronics.get('companion_computer')
        if companion:
            items.append({
                'category': 'Electronics',
                'item': f"{companion.get('brand', '')} {companion.get('model', '')}",
                'specification': companion.get('specs', {}).get('cpu', ''),
                'quantity': 1,
                'unit_price': companion.get('price_usd', 0),
                'total_price': companion.get('price_usd', 0),
                'source': companion.get('id', ''),
                'notes': 'For autonomous features'
            })
        
        # LEDs
        leds = electronics.get('led_system', {})
        items.append({
            'category': 'Electronics',
            'item': 'LED Kit',
            'specification': 'Navigation and strobe',
            'quantity': 1,
            'unit_price': leds.get('total_price_usd', 25),
            'total_price': leds.get('total_price_usd', 25),
            'source': '',
            'notes': 'Anti-collision strobe required for night ops'
        })
        
        # Frame
        frame = structural.get('frame_selection')
        if frame:
            items.append({
                'category': 'Frame',
                'item': f"{frame.get('brand', '')} {frame.get('model', '')}",
                'specification': f"{frame.get('specs', {}).get('wheelbase_mm', '')}mm",
                'quantity': 1,
                'unit_price': frame.get('price_usd', 100),
                'total_price': frame.get('price_usd', 100),
                'source': frame.get('id', ''),
                'notes': ''
            })
        else:
            # Custom frame
            bom = structural.get('structural_bom', [])
            for item in bom:
                qty = item.get('quantity', 1)
                items.append({
                    'category': 'Frame',
                    'item': item.get('item', ''),
                    'specification': '',
                    'quantity': qty,
                    'unit_price': item.get('unit_price', 0),
                    'total_price': item.get('unit_price', 0) * qty,
                    'source': item.get('source', 'custom'),
                    'notes': ''
                })
        
        # Wiring and misc
        items.append({
            'category': 'Misc',
            'item': 'Wiring Kit',
            'specification': 'Silicone wires, connectors, heatshrink',
            'quantity': 1,
            'unit_price': 30,
            'total_price': 30,
            'source': '',
            'notes': ''
        })
        
        items.append({
            'category': 'Misc',
            'item': 'Hardware Kit',
            'specification': 'Screws, nuts, standoffs, dampers',
            'quantity': 1,
            'unit_price': 15,
            'total_price': 15,
            'source': '',
            'notes': ''
        })
        
        items.append({
            'category': 'Misc',
            'item': 'Battery Straps',
            'specification': '',
            'quantity': 2,
            'unit_price': 3,
            'total_price': 6,
            'source': '',
            'notes': ''
        })
        
        # Calculate totals
        total_cost = sum(item['total_price'] for item in items)
        
        # Group by category
        by_category = {}
        for item in items:
            cat = item['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)
        
        return {
            'items': items,
            'total_cost': total_cost,
            'currency': 'USD',
            'by_category': by_category,
            'purchase_summary': self._generate_purchase_summary(items)
        }
    
    def _generate_purchase_summary(self, items: List[Dict]) -> List[Dict]:
        """Generate purchase summary with recommended vendors"""
        # Group items and suggest vendors
        summary = []
        
        categories = {}
        for item in items:
            cat = item['category']
            if cat not in categories:
                categories[cat] = {
                    'category': cat,
                    'items_count': 0,
                    'subtotal': 0
                }
            categories[cat]['items_count'] += 1
            categories[cat]['subtotal'] += item['total_price']
        
        for cat, data in categories.items():
            data['recommended_vendors'] = self._get_vendors_for_category(cat)
            summary.append(data)
        
        return summary
    
    def _get_vendors_for_category(self, category: str) -> List[str]:
        """Get recommended vendors for category"""
        vendors = {
            'Propulsion': ['GetFPV', 'RaceDayQuads', 'Banggood', 'AliExpress'],
            'Power': ['HobbyKing', 'GetFPV', 'Amazon'],
            'Electronics': ['Holybro', 'GetFPV', 'RobotShop', 'Unmanned Tech'],
            'Frame': ['GetFPV', 'RaceDayQuads', 'AliExpress', 'Banggood'],
            'Misc': ['Amazon', 'Banggood', 'Local electronics store']
        }
        return vendors.get(category, ['Amazon', 'AliExpress'])
    
    def _generate_specifications_summary(self, state: Dict[str, Any]) -> Dict:
        """Generate specifications summary"""
        mission_req = self._to_dict(state.get('mission_requirements', {}))
        propulsion = self._to_dict(state.get('propulsion_design', {}))
        power = self._to_dict(state.get('power_design', {}))
        cog = self._to_dict(state.get('cog_analysis', {}))
        aero = self._to_dict(state.get('aerodynamics_analysis', {}))
        autonomy = self._to_dict(state.get('autonomy_design', {}))
        structural = self._to_dict(state.get('structural_design', {}))
        
        return {
            'general': {
                'drone_type': str(mission_req.get('drone_type', '')),
                'configuration': mission_req.get('configuration', ''),
                'use_case': mission_req.get('use_case', ''),
                'motor_count': propulsion.get('motor_count', 4)
            },
            'dimensions': {
                'wheelbase_mm': structural.get('wheelbase_mm', 0),
                'arm_length_mm': structural.get('arm_length_mm', 0),
                'prop_diameter_inch': propulsion.get('propellers', [{}])[0].get('size_inch', 0) if propulsion.get('propellers') else 0
            },
            'weight': {
                'all_up_weight_kg': cog.get('all_up_weight_kg', 0),
                'payload_capacity_kg': mission_req.get('payload_mass_kg', 0),
                'battery_weight_g': power.get('total_weight_g', 0)
            },
            'performance': {
                'max_thrust_n': propulsion.get('total_thrust_n', 0),
                'thrust_to_weight': propulsion.get('thrust_to_weight', 0),
                'max_speed_ms': mission_req.get('max_speed_ms', 0),
                'cruise_speed_ms': mission_req.get('cruise_speed_ms', 0),
                'max_wind_ms': aero.get('max_wind_speed_ms', 0)
            },
            'power': {
                'battery_config': f"{power.get('battery', {}).get('specs', {}).get('cell_count', 6)}S",
                'capacity_mah': power.get('total_capacity_mah', 0),
                'flight_time_min': power.get('usable_flight_time_min', 0),
                'max_current_a': power.get('calculations', {}).get('max_current_a', 0)
            },
            'autonomy': {
                'firmware': autonomy.get('firmware', ''),
                'waypoint_capable': autonomy.get('waypoint_capability', False),
                'obstacle_avoidance': autonomy.get('obstacle_avoidance_type', 'None'),
                'rtl_enabled': autonomy.get('return_to_home', True)
            }
        }
    
    def _generate_build_guide_markdown(self, state: Dict[str, Any]) -> str:
        """Generate complete build guide in Markdown format"""
        specs = self._generate_specifications_summary(state)
        bom = self._generate_bom(state)
        cad = self._to_dict(state.get('cad_design', {}))
        wiring = self._to_dict(state.get('wiring_design', {}))
        software = self._to_dict(state.get('software_config', {}))
        regulatory = self._to_dict(state.get('regulatory_compliance', {}))
        optimization = self._to_dict(state.get('optimization_result', {}))
        
        guide = f'''# DroneForge AI - Drone Build Guide
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 1. Specifications Summary

### General
- **Type:** {specs['general']['drone_type']}
- **Configuration:** {specs['general']['configuration']}
- **Use Case:** {specs['general']['use_case']}
- **Motors:** {specs['general']['motor_count']}

### Dimensions
- **Wheelbase:** {specs['dimensions']['wheelbase_mm']}mm
- **Arm Length:** {specs['dimensions']['arm_length_mm']}mm
- **Propeller:** {specs['dimensions']['prop_diameter_inch']}"

### Weight
- **All-Up Weight:** {specs['weight']['all_up_weight_kg']:.2f}kg
- **Payload Capacity:** {specs['weight']['payload_capacity_kg']:.2f}kg
- **Battery Weight:** {specs['weight']['battery_weight_g']:.0f}g

### Performance
- **Max Thrust:** {specs['performance']['max_thrust_n']:.1f}N
- **Thrust-to-Weight:** {specs['performance']['thrust_to_weight']:.2f}
- **Max Speed:** {specs['performance']['max_speed_ms']:.1f}m/s
- **Wind Resistance:** {specs['performance']['max_wind_ms']:.1f}m/s

### Power
- **Battery:** {specs['power']['battery_config']} {specs['power']['capacity_mah']}mAh
- **Flight Time:** {specs['power']['flight_time_min']:.1f} minutes
- **Max Current:** {specs['power']['max_current_a']:.0f}A

### Autonomy
- **Firmware:** {specs['autonomy']['firmware']}
- **Waypoints:** {'Yes' if specs['autonomy']['waypoint_capable'] else 'No'}
- **Obstacle Avoidance:** {specs['autonomy']['obstacle_avoidance']}

---

## 2. Bill of Materials

### Summary
**Total Estimated Cost: ${bom['total_cost']:.2f}**

'''
        # Add BOM table
        guide += "| Category | Item | Spec | Qty | Unit Price | Total |\n"
        guide += "|----------|------|------|-----|------------|-------|\n"
        
        for item in bom['items']:
            guide += f"| {item['category']} | {item['item']} | {item['specification']} | {item['quantity']} | ${item['unit_price']:.2f} | ${item['total_price']:.2f} |\n"
        
        guide += f"\n**Total: ${bom['total_cost']:.2f}**\n\n"
        
        # Assembly instructions
        guide += '''---

## 3. Assembly Instructions

'''
        for note in cad.get('assembly_notes', []):
            guide += f"{note}\n"
        
        # Wiring
        guide += '''
---

## 4. Wiring Guide

### Connection Table
'''
        guide += "| # | From | Port | To | Port | Wire | Notes |\n"
        guide += "|---|------|------|-----|------|------|-------|\n"
        
        for conn in wiring.get('connection_table', [])[:15]:  # Limit for readability
            guide += f"| {conn.get('id', '')} | {conn.get('from_component', '')} | {conn.get('from_port', '')} | {conn.get('to_component', '')} | {conn.get('to_port', '')} | {conn.get('wire_type', '')} | {conn.get('notes', '')} |\n"
        
        guide += '''
### EMI Considerations
'''
        for note in wiring.get('emi_notes', []):
            guide += f"- {note}\n"
        
        # Software configuration
        guide += f'''
---

## 5. Software Configuration

### Firmware: {software.get('firmware_type', 'ArduPilot')}

### PID Values
'''
        pids = software.get('pid_values', {})
        for axis, values in pids.items():
            guide += f"- **{axis.upper()}:** P={values.get('P', 0)}, I={values.get('I', 0)}, D={values.get('D', 0)}\n"
        
        guide += '''
### Flight Modes
'''
        for mode in software.get('flight_modes', []):
            guide += f"- **Switch {mode.get('switch_position', '')}:** {mode.get('name', '')}\n"
        
        # Regulatory
        guide += '''
---

## 6. Regulatory Compliance

'''
        for jurisdiction, status in regulatory.get('compliance_status', {}).items():
            guide += f"### {jurisdiction}\n"
            guide += f"- **Category:** {status.get('category', 'N/A')}\n"
            guide += f"- **Compliant:** {'Yes' if status.get('compliant', False) else 'No'}\n"
            if status.get('requirements'):
                guide += "- **Requirements:**\n"
                for req in status.get('requirements', []):
                    guide += f"  - {req}\n"
            guide += "\n"
        
        # Performance score
        guide += f'''
---

## 7. Design Score

**Performance Score: {optimization.get('optimized_performance_score', 0):.0f}/100**

'''
        for note in optimization.get('optimization_notes', []):
            guide += f"- {note}\n"
        
        # Footer
        guide += '''
---

## 8. Pre-Flight Checklist

- [ ] All screws tight
- [ ] Props secure and correct rotation
- [ ] Battery fully charged
- [ ] RC transmitter bound
- [ ] GPS lock acquired
- [ ] Failsafes configured
- [ ] Compass calibrated
- [ ] Accelerometer calibrated
- [ ] Motor direction verified
- [ ] CG balanced

---

*Generated by DroneForge AI*
'''
        
        return guide
    
    def generate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate documentation and BOM.
        
        Args:
            state: Complete workflow state
            
        Returns:
            Dict with bill_of_materials and documentation
        """
        logger.info("Starting documentation generation")
        
        # Generate BOM
        bom = self._generate_bom(state)
        
        # Generate build guide
        build_guide = self._generate_build_guide_markdown(state)
        
        # Return documentation dict
        result = {
            'bill_of_materials': bom,
            'documentation': {
                'build_guide_md': build_guide,
                'specifications': self._generate_specifications_summary(state),
                'generated_at': datetime.now().isoformat()
            }
        }
        
        logger.info("Documentation generation completed")
        return result
