"""
DroneForge AI - Regulatory Compliance Agent
Checks regulatory compliance for multiple jurisdictions.
"""

import json
import logging
import yaml
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class RegulatoryAgent:
    """Agent for regulatory compliance checking"""
    
    def __init__(self, llm_provider: Any):
        self.llm = llm_provider
        self.regulations = self._load_regulations()
    
    def _load_regulations(self) -> Dict[str, Dict]:
        """Load all regulatory databases"""
        regulations = {}
        reg_path = Path(__file__).parent.parent.parent / "config" / "regulations"
        
        if reg_path.exists():
            for file in reg_path.glob("*.yaml"):
                try:
                    with open(file, 'r') as f:
                        data = yaml.safe_load(f)
                        jurisdiction = file.stem.replace('_', ' ').upper()
                        regulations[jurisdiction] = data
                except Exception as e:
                    logger.warning(f"Could not load {file}: {e}")
        
        return regulations
    
    def _check_weight_category(self, auw_kg: float, jurisdiction: str) -> Dict:
        """Check weight category and requirements"""
        regs = self.regulations.get(jurisdiction, {})
        weight_cats = regs.get('weight_categories', {})
        
        auw_g = auw_kg * 1000
        
        category = None
        requirements = []
        restrictions = []
        
        for cat_name, cat_data in weight_cats.items():
            if isinstance(cat_data, dict):
                max_weight = cat_data.get('max_weight_g', float('inf'))
                min_weight = cat_data.get('min_weight_g', 0)
                
                if min_weight <= auw_g <= max_weight:
                    category = cat_name
                    requirements = cat_data.get('requirements', [])
                    restrictions = cat_data.get('restrictions', [])
                    break
        
        return {
            'jurisdiction': jurisdiction,
            'weight_category': category,
            'auw_kg': auw_kg,
            'requirements': requirements,
            'restrictions': restrictions
        }
    
    def _check_india_dgca(self, state: Dict[str, Any]) -> Dict:
        """Check DGCA (India) compliance (BUG-067)"""
        cog = state.get('cog_analysis', {})
        auw_kg = cog.get('all_up_weight_kg', 0)
        mission_req = state.get('mission_requirements', {})
        
        if hasattr(mission_req, '__dict__'):
            mission_req = asdict(mission_req)
        
        compliance = {
            'jurisdiction': 'India DGCA',
            'compliant': True,
            'issues': [],
            'requirements': [],
            'notes': []
        }
        
        auw_g = auw_kg * 1000
        
        # Load categories from regulations YAML
        regs = self.regulations.get('INDIA DGCA', {})
        weight_cats = regs.get('weight_categories', {})
        
        category_name = "Large"
        category_matched = False
        
        for cat_key, cat_data in weight_cats.items():
            min_w = cat_data.get('min_weight_kg', 0) * 1000
            max_w = cat_data.get('max_weight_kg', float('inf')) * 1000
            if min_w <= auw_g <= max_w:
                category_name = cat_data.get('name', cat_key.capitalize())
                category_matched = True
                if cat_data.get('registration_required', False):
                    compliance['requirements'].append("Registration on Digital Sky platform")
                if cat_data.get('uin_required', False):
                    compliance['requirements'].append("UIN (Unique Identification Number)")
                if cat_data.get('pilot_license_required', False):
                    compliance['requirements'].append("Remote Pilot License")
                if cat_data.get('insurance_required', False):
                    compliance['requirements'].append("Third-party liability insurance")
                
                if cat_key == 'nano':
                    compliance['notes'].append("Nano category: No registration required")
                    compliance['notes'].append("No pilot license required")
                elif cat_key == 'micro':
                    compliance['notes'].append("Can fly in Green zones without permission")
                elif cat_key == 'small':
                    compliance['requirements'].append("NPNT (No Permission No Takeoff) compliant")
                    compliance['requirements'].append("Flight permission for Yellow/Red zones")
                elif cat_key == 'medium':
                    compliance['requirements'].append("Type Certificate")
                    compliance['requirements'].append("NPNT compliant")
                    compliance['requirements'].append("Import clearance")
                break
                
        if not category_matched or auw_g > 150000:
            category_name = "Large"
            compliance['category'] = category_name
            compliance['compliant'] = False
            compliance['issues'].append("Weight exceeds 150kg limit")
        else:
            compliance['category'] = category_name
        
        # Altitude check
        max_alt = mission_req.get('max_altitude_m', 120)
        if max_alt > 120:
            compliance['issues'].append("Maximum altitude exceeds 120m AGL limit")
            compliance['requirements'].append("Special altitude permission required")
        
        # BVLOS check
        if mission_req.get('beyond_vlos', False):
            compliance['requirements'].append("BVLOS exemption required")
            compliance['notes'].append("BVLOS operations require special approval")
        
        # Remote ID
        if auw_g > 250:
            compliance['requirements'].append("Remote ID module required")
        
        return compliance
    
    def _check_usa_faa(self, state: Dict[str, Any]) -> Dict:
        """Check FAA (USA) compliance (BUG-067)"""
        cog = state.get('cog_analysis', {})
        auw_kg = cog.get('all_up_weight_kg', 0)
        mission_req = state.get('mission_requirements', {})
        
        if hasattr(mission_req, '__dict__'):
            mission_req = asdict(mission_req)
        
        auw_lb = auw_kg * 2.205
        
        compliance = {
            'jurisdiction': 'USA FAA',
            'compliant': True,
            'issues': [],
            'requirements': [],
            'notes': []
        }
        
        # Load from regulations YAML
        regs = self.regulations.get('USA FAA', {})
        weight_cats = regs.get('weight_categories', {})
        
        category_name = "Over 55 lb"
        category_matched = False
        
        for cat_key, cat_data in weight_cats.items():
            min_w = cat_data.get('min_weight_kg', 0)
            max_w = cat_data.get('max_weight_kg', float('inf'))
            if min_w <= auw_kg <= max_w:
                category_name = cat_data.get('name', cat_key.capitalize())
                category_matched = True
                if cat_key == 'recreational_nano':
                    compliance['notes'].append("No registration required")
                elif cat_key == 'part_107':
                    compliance['requirements'].append("FAA Registration ($5)")
                    compliance['requirements'].append("Part 107 Remote Pilot Certificate")
                    compliance['requirements'].append("Remote ID compliance")
                break
                
        if not category_matched or auw_lb > 55:
            category_name = "Over 55 lb"
            compliance['category'] = category_name
            compliance['requirements'].append("Part 107 waiver required")
            compliance['requirements'].append("Special airworthiness certificate may be required")
        else:
            compliance['category'] = category_name
        
        # Altitude
        max_alt_ft = mission_req.get('max_altitude_m', 120) * 3.281
        if max_alt_ft > 400:
            compliance['issues'].append("Maximum altitude exceeds 400 ft AGL")
            compliance['requirements'].append("Controlled airspace authorization (LAANC)")
        
        # BVLOS
        if mission_req.get('beyond_vlos', False):
            compliance['requirements'].append("Part 107 BVLOS waiver required")
        
        # Night operations
        compliance['notes'].append("Night operations allowed with anti-collision lighting")
        compliance['requirements'].append("Anti-collision strobe visible for 3 statute miles")
        
        return compliance
    
    def _check_eu_easa(self, state: Dict[str, Any]) -> Dict:
        """Check EASA (EU) compliance (BUG-067)"""
        cog = state.get('cog_analysis', {})
        auw_kg = cog.get('all_up_weight_kg', 0)
        mission_req = state.get('mission_requirements', {})
        
        if hasattr(mission_req, '__dict__'):
            mission_req = asdict(mission_req)
        
        compliance = {
            'jurisdiction': 'EU EASA',
            'compliant': True,
            'issues': [],
            'requirements': [],
            'notes': []
        }
        
        # Load EASA categories from regulations YAML
        regs = self.regulations.get('EU EASA', {})
        weight_cats = regs.get('weight_categories', {})
        
        category_name = "Specific/Certified"
        category_matched = False
        
        for cat_key, cat_data in weight_cats.items():
            min_w = cat_data.get('min_weight_kg', 0)
            max_w = cat_data.get('max_weight_kg', float('inf'))
            if min_w <= auw_kg <= max_w:
                category_name = cat_data.get('name', cat_key.capitalize())
                category_matched = True
                
                if cat_key == 'c0':
                    compliance['requirements'].append("Class C0 marking recommended")
                    compliance['notes'].append("Can fly over uninvolved people")
                elif cat_key == 'c1':
                    compliance['requirements'].append("Class C1 marking")
                    compliance['requirements'].append("A1/A3 online training and exam")
                elif cat_key == 'c2':
                    compliance['requirements'].append("Class C2 marking")
                    compliance['requirements'].append("A2 certificate (practical self-training)")
                    compliance['requirements'].append("50m distance from uninvolved people")
                elif cat_key == 'c3_c4':
                    compliance['requirements'].append("Class C3/C4 marking")
                    compliance['requirements'].append("150m from residential areas")
                break
                
        if not category_matched or auw_kg >= 25.0:
            category_name = "Specific/Certified"
            compliance['category'] = category_name
            compliance['requirements'].append("Specific category authorization")
            compliance['requirements'].append("Risk assessment (SORA)")
        else:
            compliance['category'] = category_name
        
        # Registration
        if auw_kg >= 0.25 or mission_req.get('has_camera', True):
            compliance['requirements'].append("Operator registration")
            compliance['requirements'].append("e-ID compliance")
        
        # Altitude
        max_alt = mission_req.get('max_altitude_m', 120)
        if max_alt > 120:
            compliance['issues'].append("Maximum altitude exceeds 120m limit")
            compliance['requirements'].append("U-space authorization required")
        
        return compliance
    
    def _check_required_equipment(self, state: Dict[str, Any], 
                                  compliance_results: List[Dict]) -> List[Dict]:
        """Determine required equipment based on all compliance checks"""
        required_equipment = []
        
        electronics = state.get('electronics_design', {})
        
        # Remote ID
        needs_rid = any('Remote ID' in str(c.get('requirements', [])) 
                       for c in compliance_results)
        if needs_rid:
            required_equipment.append({
                'item': 'Remote ID Module',
                'purpose': 'Regulatory compliance',
                'jurisdictions': ['USA FAA', 'India DGCA'],
                'status': 'required'
            })
        
        # Anti-collision strobe
        needs_strobe = any('strobe' in str(c.get('requirements', [])).lower() 
                          or 'anti-collision' in str(c.get('requirements', [])).lower()
                          for c in compliance_results)
        if needs_strobe:
            led_system = electronics.get('led_system', {})
            has_strobe = led_system.get('strobe', {}).get('type') is not None
            
            required_equipment.append({
                'item': 'Anti-collision strobe',
                'purpose': 'Night flight visibility',
                'jurisdictions': ['USA FAA', 'EU EASA'],
                'status': 'present' if has_strobe else 'required'
            })
        
        # NPNT module for India
        needs_npnt = any('NPNT' in str(c.get('requirements', [])) 
                        for c in compliance_results)
        if needs_npnt:
            required_equipment.append({
                'item': 'NPNT Module',
                'purpose': 'India Digital Sky compliance',
                'jurisdictions': ['India DGCA'],
                'status': 'required'
            })
        
        return required_equipment
    
    def check_compliance(self, requirements: Any, total_weight_kg: float, autonomy: Any, electronics: Any) -> Any:
        """
        Check regulatory compliance.
        
        Args:
            requirements: Mission requirements
            total_weight_kg: Total drone weight in kg
            autonomy: Autonomy design
            electronics: Electronics design
            
        Returns:
            RegulatoryCompliance dataclass
        """
        logger.info("Starting regulatory compliance check")
        
        # Convert dataclasses to dicts
        if hasattr(requirements, '__dict__') and not isinstance(requirements, dict):
            mission_req = asdict(requirements)
        else:
            mission_req = requirements if isinstance(requirements, dict) else {}
            
        if hasattr(autonomy, '__dict__') and not isinstance(autonomy, dict):
            autonomy_dict = asdict(autonomy)
        else:
            autonomy_dict = autonomy if isinstance(autonomy, dict) else {}
            
        if hasattr(electronics, '__dict__') and not isinstance(electronics, dict):
            electronics_dict = asdict(electronics)
        else:
            electronics_dict = electronics if isinstance(electronics, dict) else {}
        
        # Build state for helper methods
        state = {
            'mission_requirements': mission_req,
            'cog_analysis': {'all_up_weight_kg': total_weight_kg},
            'autonomy_design': autonomy_dict,
            'electronics_design': electronics_dict
        }
        
        jurisdictions = mission_req.get('jurisdictions', ['india_dgca'])
        
        # Normalize jurisdiction names
        jurisdiction_map = {
            'india_dgca': 'India DGCA',
            'india': 'India DGCA',
            'usa_faa': 'USA FAA',
            'usa': 'USA FAA',
            'faa': 'USA FAA',
            'eu_easa': 'EU EASA',
            'eu': 'EU EASA',
            'easa': 'EU EASA'
        }
        
        compliance_results = []
        compliance_status = {}
        
        for jurisdiction in jurisdictions:
            j_normalized = jurisdiction_map.get(jurisdiction.lower(), jurisdiction)
            
            if 'india' in j_normalized.lower() or 'dgca' in j_normalized.lower():
                result = self._check_india_dgca(state)
            elif 'usa' in j_normalized.lower() or 'faa' in j_normalized.lower():
                result = self._check_usa_faa(state)
            elif 'eu' in j_normalized.lower() or 'easa' in j_normalized.lower():
                result = self._check_eu_easa(state)
            else:
                result = {
                    'jurisdiction': jurisdiction,
                    'compliant': True,
                    'issues': [],
                    'requirements': ['Manual verification required'],
                    'notes': [f'No automated check available for {jurisdiction}']
                }
            
            compliance_results.append(result)
            compliance_status[result['jurisdiction']] = result
        
        # Check required equipment
        required_equipment = self._check_required_equipment(state, compliance_results)
        
        # Determine overall compliance
        fully_compliant = all(r.get('compliant', False) for r in compliance_results)
        all_issues = []
        all_requirements = []
        
        for result in compliance_results:
            all_issues.extend(result.get('issues', []))
            all_requirements.extend(result.get('requirements', []))
        
        # Deduplicate requirements
        all_requirements = list(set(all_requirements))
        
        # Build regulatory compliance result
        from ..core.state import RegulatoryCompliance
        
        result = RegulatoryCompliance(
            jurisdictions_checked=[r['jurisdiction'] for r in compliance_results],
            compliance_status=compliance_status,
            registrations_required=[
                {'jurisdiction': r['jurisdiction'], 'requirements': r.get('requirements', [])}
                for r in compliance_results
            ],
            equipment_required=required_equipment,
            restrictions=[],
            fully_compliant=fully_compliant,
            compliance_notes=[
                f"Checked {len(compliance_results)} jurisdictions",
                f"Found {len(all_issues)} compliance issues" if all_issues else "No compliance issues found",
                f"Total requirements: {len(all_requirements)}"
            ]
        )
        
        logger.info("Regulatory compliance check completed")
        return result
        
        logger.info("Regulatory compliance check completed")
        return state
