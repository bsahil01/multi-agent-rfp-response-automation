"""
AI-Based Multi-Agent RFP Response Automation System
WITH LLM INTEGRATION (Groq API & Ollama Support)

Enhanced with:
- ChatOllama from LangChain for local LLM
- Groq API for fast cloud inference
- Intelligent intent parsing
- Smart product matching
- Natural language generation
"""

import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, TypedDict

# LangChain imports
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

# ============================================================
# LLM CONFIGURATION
# ============================================================

class LLMConfig:
    """LLM Configuration Manager"""

    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'ollama')  # 'groq' or 'ollama'
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')
        self.groq_model = os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768')
        self.ollama_model = os.getenv('OLLAMA_MODEL', 'llama2')
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.3'))

    def get_llm(self):
        """Get configured LLM instance"""
        if self.provider == 'groq':
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY not set. Please set it in .env file")
            return ChatGroq(
                groq_api_key=self.groq_api_key,
                model_name=self.groq_model,
                temperature=self.temperature
            )
        else:  # ollama
            return ChatOllama(
                model=self.ollama_model,
                base_url=self.ollama_base_url,
                temperature=self.temperature
            )


# ============================================================
# STATE MANAGEMENT
# ============================================================

class WorkflowState(TypedDict):
    """Shared state across all agents"""
    conversation_history: List[Dict[str, str]]
    current_step: str
    rfps_identified: List[Dict]
    selected_rfp: Optional[Dict]
    technical_analysis: Optional[Dict]
    pricing_analysis: Optional[Dict]
    final_response: Optional[Dict]
    user_inputs: Dict[str, Any]
    agent_logs: List[str]


# ============================================================
# ENHANCED SALES AGENT WITH LLM
# ============================================================

class SalesAgent:
    """
    Sales Agent with LLM-powered intelligence for:
    - Smart RFP qualification
    - Intelligent prioritization
    - Natural language summarization
    """

    def __init__(self, llm_config: LLMConfig = None):
        self.name = "Sales Agent"
        self.base_url = "https://www.tendersontime.com"
        self.llm = llm_config.get_llm() if llm_config else None

    def scan_tenders_online(self, keywords: List[str], days_ahead: int = 90) -> List[Dict]:
        """Scan tendersontime.com for RFPs matching keywords"""
        self.log(f"🔍 Scanning {self.base_url} for RFPs with keywords: {keywords}")

        # Mock RFPs (in production, use web scraping)
        mock_rfps = [
            {
                "rfp_id": "TOT-2026-001",
                "title": "Supply of 11 kV XLPE Cables for Metro Project",
                "organization": "Delhi Metro Rail Corporation (DMRC)",
                "category": "Electrical - Cables",
                "tender_value": "15,00,000 INR",
                "due_date": (datetime.now() + timedelta(days=35)).strftime("%Y-%m-%d"),
                "published_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
                "url": f"{self.base_url}/tender/dmrc-cables-2026",
                "location": "Delhi",
                "description": "Supply and installation of 11kV XLPE armoured cables for metro rail project",
                "eligibility": "IS certified manufacturers with 5+ years experience",
                "products_required": [
                    {
                        "item": "11 kV XLPE Armoured Cable",
                        "quantity": "50 km",
                        "specs": {
                            "voltage_rating": "11 kV",
                            "conductor": "Aluminum",
                            "size": "300 sq.mm",
                            "insulation": "XLPE",
                            "armour": "GI Wire"
                        }
                    }
                ],
                "tests_required": ["High Voltage Test", "Partial Discharge Test"]
            },
            {
                "rfp_id": "TOT-2026-002",
                "title": "Wires and Cables for Smart City Infrastructure",
                "organization": "Pune Smart City Development Corporation",
                "category": "Electrical - Infrastructure",
                "tender_value": "85,00,000 INR",
                "due_date": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
                "published_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                "url": f"{self.base_url}/tender/pune-smart-city-cables",
                "location": "Pune, Maharashtra",
                "description": "Supply of various cables for smart city project including street lighting and power distribution",
                "eligibility": "OEM manufacturers only",
                "products_required": [
                    {
                        "item": "6.6 kV XLPE Cable",
                        "quantity": "40 km",
                        "specs": {
                            "voltage_rating": "6.6 kV",
                            "conductor": "Aluminum",
                            "size": "240 sq.mm",
                            "insulation": "XLPE"
                        }
                    }
                ],
                "tests_required": ["High Voltage Test", "Water Penetration Test"]
            }
        ]

        # Filter by keywords
        filtered_rfps = [
            rfp for rfp in mock_rfps
            if any(kw.lower() in rfp['title'].lower() or 
                   kw.lower() in rfp['description'].lower() 
                   for kw in keywords)
        ]

        self.log(f"✅ Found {len(filtered_rfps)} matching RFPs")
        return filtered_rfps

    def qualify_rfp_with_llm(self, rfp: Dict, criteria: Dict) -> Dict:
        """Use LLM for intelligent RFP qualification"""
        if self.llm:
            prompt = f"""
            Analyze this RFP and provide qualification assessment:

            RFP Details:
            - Title: {rfp['title']}
            - Organization: {rfp['organization']}
            - Value: {rfp['tender_value']}
            - Due Date: {rfp['due_date']}
            - Location: {rfp['location']}

            Criteria:
            - Minimum Value: {criteria.get('min_tender_value', 1000000)}
            - Preferred Locations: {criteria.get('preferred_locations', [])}

            Provide a qualification score (0-100) and key reasons.
            Format: SCORE: X | REASONS: reason1, reason2, reason3
            """

            try:
                messages = [
                    SystemMessage(content="You are an expert RFP analyst."),
                    HumanMessage(content=prompt)
                ]
                response = self.llm.invoke(messages)

                # Parse LLM response
                content = response.content
                if "SCORE:" in content:
                    score_part = content.split("SCORE:")[1].split("|")[0].strip()
                    score = int(re.findall(r'\d+', score_part)[0])
                    reasons_part = content.split("REASONS:")[1].strip() if "REASONS:" in content else ""
                    reasons = [r.strip() for r in reasons_part.split(',')]

                    return {
                        "rfp_id": rfp['rfp_id'],
                        "qualified": score >= 60,
                        "score": score,
                        "reasons": reasons
                    }
            except Exception as e:
                self.log(f"LLM qualification failed, using fallback: {e}")

        # Fallback to rule-based qualification
        return self.qualify_rfp(rfp, criteria)

    def qualify_rfp(self, rfp: Dict, criteria: Dict) -> Dict:
        """Rule-based RFP qualification (fallback)"""
        qualification = {
            "rfp_id": rfp['rfp_id'],
            "qualified": True,
            "score": 0,
            "reasons": []
        }

        due_date = datetime.strptime(rfp['due_date'], "%Y-%m-%d")
        days_remaining = (due_date - datetime.now()).days

        if days_remaining < 7:
            qualification['qualified'] = False
            qualification['reasons'].append("❌ Insufficient time (< 7 days)")
        else:
            qualification['score'] += 30
            qualification['reasons'].append("✅ Adequate time available")

        tender_value = int(rfp['tender_value'].replace(',', '').replace(' INR', ''))
        if tender_value >= criteria.get('min_tender_value', 1000000):
            qualification['score'] += 40
            qualification['reasons'].append(f"✅ Tender value meets minimum")

        preferred_locations = criteria.get('preferred_locations', [])
        if not preferred_locations or any(loc in rfp['location'] for loc in preferred_locations):
            qualification['score'] += 30
            qualification['reasons'].append("✅ Location acceptable")

        qualification['qualified'] = qualification['score'] >= 60
        return qualification

    def prioritize_rfps(self, rfps: List[Dict], qualifications: List[Dict]) -> List[Dict]:
        """Prioritize qualified RFPs"""
        prioritized = []
        for rfp, qual in zip(rfps, qualifications):
            if qual['qualified']:
                due_date = datetime.strptime(rfp['due_date'], "%Y-%m-%d")
                days_remaining = (due_date - datetime.now()).days
                priority_score = qual['score'] + (100 - days_remaining)

                prioritized.append({
                    **rfp,
                    "qualification_score": qual['score'],
                    "priority_score": priority_score,
                    "days_remaining": days_remaining,
                    "qualification_reasons": qual['reasons']
                })

        prioritized.sort(key=lambda x: x['priority_score'], reverse=True)
        return prioritized

    def prepare_technical_brief(self, rfp: Dict) -> Dict:
        """Prepare brief for Technical Agent"""
        return {
            "rfp_id": rfp['rfp_id'],
            "rfp_title": rfp['title'],
            "products_scope": rfp['products_required']
        }

    def prepare_pricing_brief(self, rfp: Dict) -> Dict:
        """Prepare brief for Pricing Agent"""
        return {
            "rfp_id": rfp['rfp_id'],
            "tests_required": rfp['tests_required'],
            "tender_value": rfp['tender_value']
        }

    def log(self, message: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.name}: {message}")


# ============================================================
# ENHANCED TECHNICAL AGENT WITH LLM
# ============================================================

class TechnicalAgent:
    """
    Technical Agent with LLM-powered:
    - Intelligent specification matching
    - Semantic similarity scoring
    - Natural language explanations
    """

    def __init__(self, catalog_path: str = None, llm_config: LLMConfig = None):
        self.name = "Technical Agent"
        self.product_catalog = []
        self.llm = llm_config.get_llm() if llm_config else None
        if catalog_path:
            self.load_catalog(catalog_path)

    def load_catalog(self, catalog_path: str):
        """Load OEM product catalog"""
        with open(catalog_path, 'r') as f:
            self.product_catalog = json.load(f)
        self.log(f"📚 Loaded {len(self.product_catalog)} products")

    def calculate_match_score_with_llm(self, rfp_specs: Dict, product_specs: Dict) -> float:
        """Use LLM for intelligent spec matching"""
        if self.llm:
            prompt = f"""
            Compare these specifications and provide a match score (0-100):

            RFP Requirements:
            {json.dumps(rfp_specs, indent=2)}

            Product Specifications:
            {json.dumps(product_specs, indent=2)}

            Consider:
            - Exact matches = 100%
            - Numerical tolerance (±10%) = 90%
            - Compatible alternatives = 70%
            - Missing specs = penalty

            Respond with only a number between 0-100.
            """

            try:
                messages = [
                    SystemMessage(content="You are a technical specification analyst."),
                    HumanMessage(content=prompt)
                ]
                response = self.llm.invoke(messages)
                score = float(re.findall(r'\d+', response.content)[0])
                return min(max(score, 0), 100)
            except Exception as e:
                self.log(f"LLM matching failed, using fallback: {e}")

        # Fallback to rule-based matching
        return self.calculate_match_score(rfp_specs, product_specs)

    def calculate_match_score(self, rfp_specs: Dict, product_specs: Dict) -> float:
        """Rule-based specification matching (fallback)"""
        if not rfp_specs or not product_specs:
            return 0.0

        total_specs = 0
        matched_points = 0.0

        for key, rfp_value in rfp_specs.items():
            if key in product_specs:
                total_specs += 1
                product_value = product_specs[key]

                if str(rfp_value).lower() == str(product_value).lower():
                    matched_points += 1.0
                elif key in ['size', 'conductor_size']:
                    try:
                        rfp_num = float(re.findall(r'\d+', str(rfp_value))[0])
                        prod_num = float(re.findall(r'\d+', str(product_value))[0])
                        diff_percent = abs(rfp_num - prod_num) / rfp_num
                        if diff_percent <= 0.1:
                            matched_points += 0.9
                        elif diff_percent <= 0.2:
                            matched_points += 0.7
                    except:
                        pass

        return (matched_points / total_specs * 100) if total_specs > 0 else 0.0

    def find_matching_products(self, rfp_item: Dict, top_n: int = 3) -> List[Dict]:
        """Find top N matching products"""
        matches = []

        for product in self.product_catalog:
            match_score = self.calculate_match_score_with_llm(
                rfp_item['specs'],
                product['specifications']
            ) if self.llm else self.calculate_match_score(
                rfp_item['specs'],
                product['specifications']
            )

            if match_score > 0:
                matches.append({
                    "sku": product['sku'],
                    "product_name": product['product_name'],
                    "match_score": round(match_score, 2),
                    "specifications": product['specifications'],
                    "price_per_unit": product.get('price_per_km', 0)
                })

        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches[:top_n]

    def analyze_rfp(self, technical_brief: Dict) -> Dict:
        """Complete technical analysis"""
        self.log(f"🔧 Analyzing RFP: {technical_brief['rfp_id']}")

        analysis = {
            "rfp_id": technical_brief['rfp_id'],
            "items_analyzed": [],
            "overall_feasibility": "HIGH"
        }

        for item in technical_brief['products_scope']:
            self.log(f"  Matching: {item['item']}")
            top_matches = self.find_matching_products(item, top_n=3)

            analysis['items_analyzed'].append({
                "item_description": item['item'],
                "quantity": item['quantity'],
                "rfp_specifications": item['specs'],
                "top_3_recommendations": top_matches,
                "selected_product": top_matches[0] if top_matches else None
            })

        # Determine feasibility
        if analysis['items_analyzed']:
            avg_match = sum(
                item['selected_product']['match_score'] 
                for item in analysis['items_analyzed'] 
                if item['selected_product']
            ) / len(analysis['items_analyzed'])

            if avg_match >= 90:
                analysis['overall_feasibility'] = "HIGH"
            elif avg_match >= 70:
                analysis['overall_feasibility'] = "MEDIUM"
            else:
                analysis['overall_feasibility'] = "LOW"

        self.log(f"✅ Analysis complete. Feasibility: {analysis['overall_feasibility']}")
        return analysis

    def log(self, message: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.name}: {message}")


# Continue in next part...

# ============================================================
# PRICING AGENT (Standard - No LLM needed)
# ============================================================

class PricingAgent:
    """Pricing Agent for cost calculation"""

    def __init__(self, test_pricing_path: str = None):
        self.name = "Pricing Agent"
        self.test_pricing = {}
        if test_pricing_path:
            self.load_test_pricing(test_pricing_path)

    def load_test_pricing(self, pricing_path: str):
        """Load test pricing"""
        with open(pricing_path, 'r') as f:
            self.test_pricing = json.load(f)
        self.log(f"💰 Loaded pricing for {len(self.test_pricing)} tests")

    def calculate_pricing(self, pricing_brief: Dict, technical_analysis: Dict) -> Dict:
        """Calculate complete pricing"""
        self.log(f"💵 Calculating pricing for {pricing_brief['rfp_id']}")

        pricing = {
            "rfp_id": pricing_brief['rfp_id'],
            "material_breakdown": [],
            "test_breakdown": [],
            "total_material_cost": 0,
            "total_test_cost": 0,
            "grand_total": 0
        }

        for item in technical_analysis['items_analyzed']:
            if item['selected_product']:
                quantity = float(re.findall(r'\d+', item['quantity'])[0])
                unit_price = item['selected_product']['price_per_unit']
                total_price = quantity * unit_price

                pricing['material_breakdown'].append({
                    "item": item['item_description'],
                    "sku": item['selected_product']['sku'],
                    "quantity": item['quantity'],
                    "unit_price": unit_price,
                    "total_cost": total_price
                })

                pricing['total_material_cost'] += total_price

        for test_name in pricing_brief['tests_required']:
            if test_name in self.test_pricing:
                cost = self.test_pricing[test_name]
                pricing['test_breakdown'].append({
                    "test_name": test_name,
                    "cost": cost
                })
                pricing['total_test_cost'] += cost

        pricing['grand_total'] = pricing['total_material_cost'] + pricing['total_test_cost']

        self.log(f"✅ Total: ₹{pricing['grand_total']:,.2f}")
        return pricing

    def log(self, message: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.name}: {message}")


# ============================================================
# ENHANCED CHAT ORCHESTRATOR WITH LLM
# ============================================================

class ChatOrchestrator:
    """
    Main orchestrator with LLM-powered:
    - Natural language understanding
    - Intent classification
    - Response generation
    """

    def __init__(self, sales_agent: SalesAgent, technical_agent: TechnicalAgent, 
                 pricing_agent: PricingAgent, llm_config: LLMConfig = None):
        self.name = "RFP Assistant"
        self.sales_agent = sales_agent
        self.technical_agent = technical_agent
        self.pricing_agent = pricing_agent
        self.llm = llm_config.get_llm() if llm_config else None

        self.state: WorkflowState = {
            "conversation_history": [],
            "current_step": "IDLE",
            "rfps_identified": [],
            "selected_rfp": None,
            "technical_analysis": None,
            "pricing_analysis": None,
            "final_response": None,
            "user_inputs": {},
            "agent_logs": []
        }

    def chat(self, user_message: str) -> str:
        """Main chat interface with LLM-powered understanding"""
        self.log_conversation("user", user_message)

        # Parse intent with LLM
        intent = self.parse_intent_with_llm(user_message) if self.llm else self.parse_intent(user_message)

        # Route to handler
        if intent == "scan_rfps":
            response = self.handle_scan_rfps(user_message)
        elif intent == "select_rfp":
            response = self.handle_select_rfp(user_message)
        elif intent == "analyze_rfp":
            response = self.handle_analyze_rfp(user_message)
        elif intent == "show_results":
            response = self.handle_show_results(user_message)
        elif intent == "full_workflow":
            response = self.handle_full_workflow(user_message)
        elif intent == "status":
            response = self.handle_status()
        else:
            response = self.handle_general_query(user_message)

        # Enhance response with LLM if available
        if self.llm and len(response) < 500:
            response = self.enhance_response_with_llm(response)

        self.log_conversation("assistant", response)
        return response

    def parse_intent_with_llm(self, message: str) -> str:
        """Use LLM for intelligent intent parsing"""
        prompt = f"""
        Classify this user message into one of these intents:
        - scan_rfps: User wants to find/scan RFPs
        - select_rfp: User wants to select a specific RFP
        - analyze_rfp: User wants to analyze an RFP
        - show_results: User wants to see results/details
        - full_workflow: User wants complete automation
        - status: User wants to check status
        - general: General query or greeting

        User message: "{message}"

        Respond with only the intent name (e.g., "scan_rfps")
        """

        try:
            messages = [
                SystemMessage(content="You are an intent classifier."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            intent = response.content.strip().lower().replace('"', '')

            valid_intents = ['scan_rfps', 'select_rfp', 'analyze_rfp', 'show_results', 
                           'full_workflow', 'status', 'general']
            if intent in valid_intents:
                return intent
        except Exception as e:
            print(f"LLM intent parsing failed: {e}")

        # Fallback to rule-based
        return self.parse_intent(message)

    def parse_intent(self, message: str) -> str:
        """Rule-based intent parsing (fallback)"""
        message_lower = message.lower()

        if any(word in message_lower for word in ['scan', 'find', 'search', 'look for']):
            return "scan_rfps"
        elif any(word in message_lower for word in ['select', 'choose', 'pick']):
            return "select_rfp"
        elif any(word in message_lower for word in ['analyze', 'process', 'evaluate']):
            return "analyze_rfp"
        elif any(word in message_lower for word in ['show', 'display', 'results', 'summary']):
            return "show_results"
        elif any(word in message_lower for word in ['complete', 'full', 'entire', 'automate']):
            return "full_workflow"
        elif any(word in message_lower for word in ['status', 'progress', 'where']):
            return "status"
        else:
            return "general"

    def enhance_response_with_llm(self, response: str) -> str:
        """Enhance response with LLM for better readability"""
        prompt = f"""
        Improve this response to be more professional and user-friendly:

        {response}

        Keep it concise and maintain all information. Use emojis sparingly.
        """

        try:
            messages = [
                SystemMessage(content="You are a professional business communication assistant."),
                HumanMessage(content=prompt)
            ]
            enhanced = self.llm.invoke(messages)
            return enhanced.content
        except:
            return response

    def handle_scan_rfps(self, message: str) -> str:
        """Handle RFP scanning"""
        self.state['current_step'] = "SCANNING"

        keywords = self.extract_keywords(message)
        if not keywords:
            keywords = ['cable', 'wire', 'electrical']

        rfps = self.sales_agent.scan_tenders_online(keywords, days_ahead=90)

        criteria = {
            'min_tender_value': 1000000,
            'preferred_locations': ['Delhi', 'Mumbai', 'Pune', 'Ahmedabad']
        }

        qualifications = [
            self.sales_agent.qualify_rfp_with_llm(rfp, criteria) if self.llm 
            else self.sales_agent.qualify_rfp(rfp, criteria)
            for rfp in rfps
        ]

        prioritized_rfps = self.sales_agent.prioritize_rfps(rfps, qualifications)
        self.state['rfps_identified'] = prioritized_rfps
        self.state['current_step'] = "RFPS_IDENTIFIED"

        response = f"🎯 **RFP Scan Complete**\n\n"
        response += f"Found **{len(prioritized_rfps)} qualified RFPs**:\n\n"

        for i, rfp in enumerate(prioritized_rfps[:5], 1):
            response += f"**{i}. {rfp['title']}**\n"
            response += f"   • Organization: {rfp['organization']}\n"
            response += f"   • Value: ₹{rfp['tender_value']}\n"
            response += f"   • Due: {rfp['due_date']} ({rfp['days_remaining']} days)\n"
            response += f"   • Priority: {rfp['priority_score']}\n\n"

        response += "\n💡 Next: Type 'analyze RFP 1' or 'complete workflow'"
        return response

    def handle_select_rfp(self, message: str) -> str:
        """Handle RFP selection"""
        if not self.state['rfps_identified']:
            return "⚠️ No RFPs available. Please scan for RFPs first."

        numbers = re.findall(r'\d+', message)
        if not numbers:
            return "⚠️ Please specify RFP number (e.g., 'select RFP 1')"

        rfp_index = int(numbers[0]) - 1
        if rfp_index < 0 or rfp_index >= len(self.state['rfps_identified']):
            return f"⚠️ Invalid RFP number. Choose 1-{len(self.state['rfps_identified'])}"

        selected_rfp = self.state['rfps_identified'][rfp_index]
        self.state['selected_rfp'] = selected_rfp
        self.state['current_step'] = "RFP_SELECTED"

        response = f"✅ **RFP Selected**\n\n**{selected_rfp['title']}**\n\n"
        response += f"📋 Details:\n"
        response += f"• RFP ID: {selected_rfp['rfp_id']}\n"
        response += f"• Organization: {selected_rfp['organization']}\n"
        response += f"• Due: {selected_rfp['due_date']} ({selected_rfp['days_remaining']} days)\n"
        response += f"\n💡 Type 'analyze this RFP' to begin analysis"

        return response

    def handle_analyze_rfp(self, message: str) -> str:
        """Handle RFP analysis"""
        if not self.state['selected_rfp']:
            if self.state['rfps_identified']:
                self.state['selected_rfp'] = self.state['rfps_identified'][0]
            else:
                return "⚠️ No RFP selected. Please scan and select an RFP first."

        self.state['current_step'] = "ANALYZING"
        rfp = self.state['selected_rfp']

        response = f"🔄 **Analyzing {rfp['rfp_id']}**\n\n"

        # Technical analysis
        response += "⚙️ **Technical Analysis**\n"
        tech_brief = self.sales_agent.prepare_technical_brief(rfp)
        tech_analysis = self.technical_agent.analyze_rfp(tech_brief)
        self.state['technical_analysis'] = tech_analysis

        response += f"✅ Matched {len(tech_analysis['items_analyzed'])} items\n"
        response += f"✅ Feasibility: {tech_analysis['overall_feasibility']}\n\n"

        for item in tech_analysis['items_analyzed']:
            if item['selected_product']:
                response += f"**{item['item_description']}**\n"
                response += f"   Selected: {item['selected_product']['sku']}\n"
                response += f"   Match: {item['selected_product']['match_score']}%\n\n"

        # Pricing
        response += "💰 **Pricing Analysis**\n"
        price_brief = self.sales_agent.prepare_pricing_brief(rfp)
        pricing = self.pricing_agent.calculate_pricing(price_brief, tech_analysis)
        self.state['pricing_analysis'] = pricing

        response += f"✅ Material: ₹{pricing['total_material_cost']:,.2f}\n"
        response += f"✅ Testing: ₹{pricing['total_test_cost']:,.2f}\n"
        response += f"✅ **TOTAL: ₹{pricing['grand_total']:,.2f}**\n"

        self.state['current_step'] = "ANALYSIS_COMPLETE"
        return response

    def handle_full_workflow(self, message: str) -> str:
        """Execute complete workflow"""
        self.state['current_step'] = "FULL_WORKFLOW"

        keywords = self.extract_keywords(message) or ['cable', 'wire']
        scan_response = self.handle_scan_rfps(f"scan for {' '.join(keywords)}")

        if self.state['rfps_identified']:
            self.state['selected_rfp'] = self.state['rfps_identified'][0]
            analyze_response = self.handle_analyze_rfp("analyze")
            return f"{scan_response}\n\n---\n\n{analyze_response}"

        return "⚠️ No RFPs found matching criteria."

    def handle_status(self) -> str:
        """Show workflow status"""
        status = f"📊 **Status: {self.state['current_step']}**\n\n"

        if self.state['rfps_identified']:
            status += f"✅ RFPs: {len(self.state['rfps_identified'])}\n"
        if self.state['selected_rfp']:
            status += f"✅ Selected: {self.state['selected_rfp']['rfp_id']}\n"
        if self.state['technical_analysis']:
            status += f"✅ Technical: Complete\n"
        if self.state['pricing_analysis']:
            status += f"✅ Pricing: Complete\n"

        return status

    def handle_show_results(self, message: str) -> str:
        """Show detailed results"""
        if not self.state['technical_analysis'] or not self.state['pricing_analysis']:
            return "⚠️ No results available. Run analysis first."

        tech = self.state['technical_analysis']
        pricing = self.state['pricing_analysis']

        response = f"📊 **Complete RFP Response**\n\n"
        response += f"**RFP:** {self.state['selected_rfp']['rfp_id']}\n\n"
        response += "**Technical:**\n"

        for item in tech['items_analyzed']:
            response += f"• {item['item_description']}\n"
            response += f"  Top 3: "
            response += ", ".join([
                f"{p['sku']} ({p['match_score']}%)" 
                for p in item['top_3_recommendations'][:3]
            ])
            response += "\n"

        response += f"\n**Pricing:**\n"
        response += f"Material: ₹{pricing['total_material_cost']:,.2f}\n"
        response += f"Testing: ₹{pricing['total_test_cost']:,.2f}\n"
        response += f"**TOTAL: ₹{pricing['grand_total']:,.2f}**\n"

        return response

    def handle_general_query(self, message: str) -> str:
        """Handle general queries"""
        return (
            "👋 Hi! I'm your RFP Assistant with AI-powered intelligence.\n\n"
            "🔍 **Scan for RFPs** from tendersontime.com\n"
            "🤖 **Smart Analysis** with LLM-powered matching\n"
            "💰 **Instant Pricing** with detailed breakdowns\n\n"
            "Try:\n"
            "• 'Scan for cable RFPs'\n"
            "• 'Complete workflow'\n"
            "• 'Show status'\n"
        )

    def extract_keywords(self, message: str) -> List[str]:
        """Extract keywords"""
        keywords = ['cable', 'wire', 'electrical', 'power', 'xlpe', 'pvc']
        return [kw for kw in keywords if kw in message.lower()] or None

    def log_conversation(self, role: str, message: str):
        """Log conversation"""
        self.state['conversation_history'].append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def get_state(self) -> WorkflowState:
        """Get current state"""
        return self.state


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    # Initialize LLM configuration
    llm_config = LLMConfig()

    # Initialize agents with LLM
    sales_agent = SalesAgent(llm_config=llm_config)
    technical_agent = TechnicalAgent(llm_config=llm_config)
    pricing_agent = PricingAgent()

    # Create orchestrator
    orchestrator = ChatOrchestrator(
        sales_agent, 
        technical_agent, 
        pricing_agent,
        llm_config=llm_config
    )

    # Example conversation
    print("="*70)
    print("AI-POWERED RFP AUTOMATION SYSTEM")
    print(f"LLM Provider: {llm_config.provider}")
    print(f"Model: {llm_config.groq_model if llm_config.provider == 'groq' else llm_config.ollama_model}")
    print("="*70)
    print()

    print(orchestrator.chat("Hello!"))
    print()
    print(orchestrator.chat("Scan for cable RFPs"))
    print()
    print(orchestrator.chat("Analyze the first RFP"))
