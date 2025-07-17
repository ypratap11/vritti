# src/agents/ask_vritti.py
"""
Ask Vritti - Intelligent Multi-LLM Conversational AI Engine
The most cost-optimized, intelligent AI agent for invoice processing

Features:
- Multi-LLM routing (Gemini, GPT-4o Mini, Claude, GPT-4)
- Intelligent cost optimization
- Smart escalation chains
- Real-time cost tracking
- GCP integration
"""

import json
import re
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Multi-LLM imports
import google.generativeai as genai
import openai
import anthropic
from google.cloud import aiplatform
from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from src.models.tenant import Tenant, Invoice, Document, TenantUser
from src.database.connection import get_db_session
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Available LLM providers"""
    GEMINI_FLASH = "gemini_flash"
    GPT4O_MINI = "gpt4o_mini"
    CLAUDE_HAIKU = "claude_haiku"
    CLAUDE_SONNET = "claude_sonnet"
    GPT4_TURBO = "gpt4_turbo"


class QueryComplexity(Enum):
    """Query complexity levels for intelligent routing"""
    SIMPLE = 1  # Basic search, retrieval
    MODERATE = 2  # Simple logic, comparisons
    COMPLEX = 3  # Analysis, reasoning
    CRITICAL = 4  # Fraud detection, strategic insights


class ConversationIntent(Enum):
    """Possible user intents for invoice processing"""
    PROCESS_INVOICE = "process_invoice"
    APPROVE_INVOICE = "approve_invoice"
    REJECT_INVOICE = "reject_invoice"
    SEARCH_INVOICES = "search_invoices"
    GET_INVOICE_STATUS = "get_invoice_status"
    GET_ANALYTICS = "get_analytics"
    VENDOR_INQUIRY = "vendor_inquiry"
    PAYMENT_STATUS = "payment_status"
    FRAUD_DETECTION = "fraud_detection"
    HELP = "help"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class LLMConfig:
    """Configuration for each LLM provider"""
    provider: LLMProvider
    model_name: str
    cost_per_1m_tokens: float
    max_tokens: int
    temperature: float
    timeout_seconds: int
    strengths: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)


@dataclass
class QueryAnalysis:
    """Analysis of user query for intelligent routing"""
    complexity: QueryComplexity
    confidence: float
    estimated_tokens: int
    requires_reasoning: bool
    is_time_sensitive: bool
    business_impact: str  # "low", "medium", "high", "critical"
    recommended_llm: LLMProvider
    fallback_llms: List[LLMProvider]


@dataclass
class LLMResponse:
    """Response from an LLM with metadata"""
    text: str
    provider: LLMProvider
    tokens_used: int
    cost: float
    confidence_score: float
    processing_time_ms: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class ExtractedEntity:
    """Entities extracted from user messages"""
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    invoice_number: Optional[str] = None
    date_range: Optional[Tuple[datetime, datetime]] = None
    approval_status: Optional[str] = None
    approval_status: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[str] = None


@dataclass
class ConversationContext:
    """Context for ongoing conversation"""
    tenant_id: str
    user_id: str
    session_id: str
    conversation_history: List[Dict[str, Any]]
    current_intent: Optional[ConversationIntent] = None
    pending_action: Optional[Dict[str, Any]] = None
    entities: Optional[ExtractedEntity] = None
    total_cost: float = 0.0
    llm_usage_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """Response from Ask Vritti with full metadata"""
    text: str
    intent: ConversationIntent
    action_required: bool = False
    action_type: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    suggested_responses: Optional[List[str]] = None
    llm_used: Optional[LLMProvider] = None
    cost: float = 0.0
    confidence: float = 0.0


class IntelligentLLMRouter:
    """The brain that decides which LLM to use for maximum ROI"""

    def __init__(self):
        # LLM Configurations with real-world pricing
        self.llm_configs = {
            LLMProvider.GEMINI_FLASH: LLMConfig(
                provider=LLMProvider.GEMINI_FLASH,
                model_name="gemini-1.5-flash",
                cost_per_1m_tokens=0.075,
                max_tokens=8192,
                temperature=0.3,
                timeout_seconds=5,
                strengths=["speed", "cost", "search", "simple_queries"],
                use_cases=["search", "retrieval", "basic_questions"]
            ),
            LLMProvider.GPT4O_MINI: LLMConfig(
                provider=LLMProvider.GPT4O_MINI,
                model_name="gpt-4o-mini",
                cost_per_1m_tokens=0.15,
                max_tokens=16384,
                temperature=0.3,
                timeout_seconds=10,
                strengths=["reasoning", "balance", "reliability"],
                use_cases=["analysis", "comparisons", "logic"]
            ),
            LLMProvider.CLAUDE_HAIKU: LLMConfig(
                provider=LLMProvider.CLAUDE_HAIKU,
                model_name="claude-3-haiku-20240307",
                cost_per_1m_tokens=0.25,
                max_tokens=4096,
                temperature=0.3,
                timeout_seconds=10,
                strengths=["conversation", "natural_language", "helpful"],
                use_cases=["chat", "explanations", "user_interaction"]
            ),
            LLMProvider.CLAUDE_SONNET: LLMConfig(
                provider=LLMProvider.CLAUDE_SONNET,
                model_name="claude-3-5-sonnet-20241022",
                cost_per_1m_tokens=3.0,
                max_tokens=8192,
                temperature=0.3,
                timeout_seconds=15,
                strengths=["reasoning", "analysis", "complex_logic"],
                use_cases=["complex_analysis", "business_logic", "decision_support"]
            ),
            LLMProvider.GPT4_TURBO: LLMConfig(
                provider=LLMProvider.GPT4_TURBO,
                model_name="gpt-4-turbo",
                cost_per_1m_tokens=10.0,
                max_tokens=4096,
                temperature=0.2,
                timeout_seconds=20,
                strengths=["maximum_capability", "critical_analysis", "accuracy"],
                use_cases=["fraud_detection", "critical_decisions", "complex_reasoning"]
            )
        }

        # Intent to complexity mapping
        self.intent_complexity = {
            ConversationIntent.GREETING: QueryComplexity.SIMPLE,
            ConversationIntent.SEARCH_INVOICES: QueryComplexity.SIMPLE,
            ConversationIntent.GET_INVOICE_STATUS: QueryComplexity.SIMPLE,
            ConversationIntent.APPROVE_INVOICE: QueryComplexity.MODERATE,
            ConversationIntent.VENDOR_INQUIRY: QueryComplexity.MODERATE,
            ConversationIntent.GET_ANALYTICS: QueryComplexity.COMPLEX,
            ConversationIntent.FRAUD_DETECTION: QueryComplexity.CRITICAL,
            ConversationIntent.UNKNOWN: QueryComplexity.MODERATE
        }

        # Smart routing rules
        self.routing_matrix = {
            QueryComplexity.SIMPLE: {
                "primary": LLMProvider.GEMINI_FLASH,
                "fallback": [LLMProvider.GPT4O_MINI, LLMProvider.CLAUDE_HAIKU]
            },
            QueryComplexity.MODERATE: {
                "primary": LLMProvider.GPT4O_MINI,
                "fallback": [LLMProvider.CLAUDE_HAIKU, LLMProvider.CLAUDE_SONNET]
            },
            QueryComplexity.COMPLEX: {
                "primary": LLMProvider.CLAUDE_SONNET,
                "fallback": [LLMProvider.GPT4_TURBO, LLMProvider.GPT4O_MINI]
            },
            QueryComplexity.CRITICAL: {
                "primary": LLMProvider.GPT4_TURBO,
                "fallback": [LLMProvider.CLAUDE_SONNET]
            }
        }

    def analyze_query(self, message: str, intent: ConversationIntent, context: ConversationContext) -> QueryAnalysis:
        """Analyze query to determine optimal LLM routing"""

        # Base complexity from intent
        base_complexity = self.intent_complexity.get(intent, QueryComplexity.MODERATE)

        # Analyze message content for complexity indicators
        complexity_indicators = {
            "simple": ["show", "list", "find", "search", "what", "who", "when"],
            "moderate": ["approve", "compare", "analyze", "calculate", "total"],
            "complex": ["why", "how", "explain", "pattern", "trend", "insight", "recommend"],
            "critical": ["fraud", "suspicious", "unusual", "risk", "security", "audit"]
        }

        message_lower = message.lower()
        detected_complexity = QueryComplexity.SIMPLE

        for level, keywords in complexity_indicators.items():
            if any(keyword in message_lower for keyword in keywords):
                if level == "moderate":
                    detected_complexity = QueryComplexity.MODERATE
                elif level == "complex":
                    detected_complexity = QueryComplexity.COMPLEX
                elif level == "critical":
                    detected_complexity = QueryComplexity.CRITICAL

        # Use higher of base or detected complexity
        final_complexity = max(base_complexity, detected_complexity, key=lambda x: x.value)

        # Estimate tokens (rough approximation)
        estimated_tokens = max(100, len(message.split()) * 15)

        # Determine business impact
        business_impact = "low"
        if "approve" in message_lower or "payment" in message_lower:
            business_impact = "medium"
        if "fraud" in message_lower or "risk" in message_lower:
            business_impact = "critical"
        elif final_complexity == QueryComplexity.COMPLEX:
            business_impact = "high"

        # Time sensitivity
        is_time_sensitive = any(word in message_lower for word in ["urgent", "asap", "immediately", "now"])

        # Get routing recommendation
        routing = self.routing_matrix[final_complexity]
        recommended_llm = routing["primary"]

        # Override for time-sensitive queries (prefer speed)
        if is_time_sensitive and final_complexity <= QueryComplexity.MODERATE:
            recommended_llm = LLMProvider.GEMINI_FLASH

        return QueryAnalysis(
            complexity=final_complexity,
            confidence=0.8,  # Base confidence
            estimated_tokens=estimated_tokens,
            requires_reasoning=final_complexity.value >= 3,
            is_time_sensitive=is_time_sensitive,
            business_impact=business_impact,
            recommended_llm=recommended_llm,
            fallback_llms=routing["fallback"]
        )

    def should_escalate(self, response: LLMResponse, analysis: QueryAnalysis) -> bool:
        """Determine if we should escalate to a more powerful LLM"""

        # Escalate if confidence is too low
        if response.confidence_score < 0.7:
            return True

        # Escalate if response seems incomplete
        if len(response.text.strip()) < 20:
            return True

        # Escalate if error occurred
        if not response.success:
            return True

        # Escalate for critical business impact
        if analysis.business_impact == "critical" and response.provider != LLMProvider.GPT4_TURBO:
            return True

        return False

    def get_escalation_llm(self, current_llm: LLMProvider, analysis: QueryAnalysis) -> Optional[LLMProvider]:
        """Get next LLM in escalation chain"""

        routing = self.routing_matrix[analysis.complexity]
        fallbacks = routing["fallback"]

        # Find current position and return next
        try:
            current_index = [current_llm] + fallbacks
            for i, llm in enumerate(current_index):
                if llm == current_llm and i + 1 < len(current_index):
                    return current_index[i + 1]
        except:
            pass

        return None


class AskVrittiAI:
    """Ask Vritti - The most intelligent, cost-optimized conversational AI for invoices"""

    def __init__(
            self,
            gemini_api_key: Optional[str] = None,
            openai_api_key: Optional[str] = None,
            anthropic_api_key: Optional[str] = None,
            gcp_project_id: Optional[str] = None
    ):
        # Initialize LLM clients
        self.gemini_client = None
        self.openai_client = None
        self.anthropic_client = None

        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')

        if openai_api_key:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

        if anthropic_api_key:
            self.anthropic_client = anthropic.Client(api_key=anthropic_api_key)

        if gcp_project_id:
            aiplatform.init(project=gcp_project_id)

        # Initialize intelligent router
        self.router = IntelligentLLMRouter()
        self.conversation_contexts: Dict[str, ConversationContext] = {}

        # 🔧 NEW: Override routing for forced configurations
        self._override_routing_for_available_providers(
            gemini_api_key, openai_api_key, anthropic_api_key
        )

        # Cost tracking and limits
        self.daily_cost_limit = 50.0  # $50 per day
        self.monthly_cost_limit = 1000.0  # $1000 per month
        self.cost_tracking = {
            "daily": {"date": datetime.now().date(), "cost": 0.0},
            "monthly": {"month": datetime.now().month, "cost": 0.0}
        }

        # Intent classification patterns
        self.intent_patterns = {
            ConversationIntent.PROCESS_INVOICE: [
                r'process.*invoice', r'upload.*invoice', r'new.*invoice',
                r'extract.*data', r'scan.*document', r'analyze.*pdf'
            ],
            ConversationIntent.APPROVE_INVOICE: [
                r'approve.*invoice', r'accept.*invoice', r'sign.*off',
                r'authorize.*payment', r'approve.*payment', r'looks.*good'
            ],
            ConversationIntent.REJECT_INVOICE: [
                r'reject.*invoice', r'deny.*invoice', r'decline.*invoice',
                r'not.*approved', r'hold.*invoice', r'needs.*review'
            ],
            ConversationIntent.SEARCH_INVOICES: [
                r'find.*invoice', r'search.*invoice', r'show.*invoice',
                r'list.*invoice', r'invoices.*from', r'invoices.*over'
            ],
            ConversationIntent.GET_INVOICE_STATUS: [
                r'status.*invoice', r'where.*invoice', r'invoice.*status',
                r'what.*happened', r'progress.*invoice'
            ],
            ConversationIntent.VENDOR_INQUIRY: [
                r'vendor.*', r'supplier.*', r'how.*much.*paid',
                r'spending.*with', r'invoices.*from'
            ],
            ConversationIntent.PAYMENT_STATUS: [
                r'payment.*status', r'paid.*invoice', r'when.*paid',
                r'payment.*sent', r'check.*sent'
            ],
            ConversationIntent.GET_ANALYTICS: [
                r'analytics', r'dashboard', r'report', r'summary',
                r'total.*spent', r'breakdown', r'overview'
            ],
            ConversationIntent.FRAUD_DETECTION: [
                r'fraud', r'suspicious', r'unusual', r'risk', r'security'
            ],
            ConversationIntent.HELP: [
                r'help', r'what.*can.*you', r'how.*do', r'commands'
            ],
            ConversationIntent.GREETING: [
                r'hello', r'hi', r'hey', r'good.*morning', r'good.*afternoon'
            ]
        }

    def _override_routing_for_available_providers(
            self,
            gemini_api_key: Optional[str],
            openai_api_key: Optional[str],
            anthropic_api_key: Optional[str]
    ):
        """Override routing matrix when providers are explicitly disabled"""

        available_providers = []

        if gemini_api_key:
            available_providers.append(LLMProvider.GEMINI_FLASH)

        if openai_api_key:
            available_providers.extend([LLMProvider.GPT4O_MINI, LLMProvider.GPT4_TURBO])

        if anthropic_api_key:
            available_providers.extend([LLMProvider.CLAUDE_HAIKU, LLMProvider.CLAUDE_SONNET])

        # If only Gemini is available, force all routing to Gemini
        if available_providers == [LLMProvider.GEMINI_FLASH]:
            print("🔧 FORCING GEMINI-ONLY MODE - All queries will use Gemini Flash")

            # Override all routing to use only Gemini
            for complexity in QueryComplexity:
                self.router.routing_matrix[complexity] = {
                    "primary": LLMProvider.GEMINI_FLASH,
                    "fallback": [LLMProvider.GEMINI_FLASH]  # Even fallback is Gemini
                }

        # If only specific providers are disabled, remove them from routing
        else:
            for complexity in QueryComplexity:
                route = self.router.routing_matrix[complexity]

                # Ensure primary is available
                if route["primary"] not in available_providers:
                    route["primary"] = available_providers[0]

                # Filter fallbacks to only available providers
                route["fallback"] = [
                    provider for provider in route["fallback"]
                    if provider in available_providers
                ]

    async def call_llm(self, prompt: str, provider: LLMProvider, context: ConversationContext) -> LLMResponse:
        """Call specific LLM provider with better error handling for disabled providers"""

        start_time = datetime.now()
        config = self.router.llm_configs[provider]

        try:
            if provider == LLMProvider.GEMINI_FLASH:
                if not self.gemini_client:
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="Gemini client not initialized"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_gemini(prompt)),
                    timeout=config.timeout_seconds
                )

            elif provider == LLMProvider.GPT4O_MINI:
                if not self.openai_client:
                    # 🔧 NEW: Better error message when OpenAI is explicitly disabled
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="OpenAI client explicitly disabled - using Gemini instead"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_openai(prompt, config.model_name)),
                    timeout=config.timeout_seconds
                )

            elif provider in [LLMProvider.CLAUDE_HAIKU, LLMProvider.CLAUDE_SONNET]:
                if not self.anthropic_client:
                    # 🔧 NEW: Better error message when Anthropic is explicitly disabled
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="Anthropic client explicitly disabled - using Gemini instead"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_anthropic(prompt, config.model_name)),
                    timeout=config.timeout_seconds
                )

            elif provider == LLMProvider.GPT4_TURBO:
                if not self.openai_client:
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="GPT-4 client explicitly disabled - using Gemini instead"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_openai(prompt, config.model_name)),
                    timeout=config.timeout_seconds
                )

            else:
                return LLMResponse(
                    text="", provider=provider, tokens_used=0, cost=0.0,
                    confidence_score=0.0, processing_time_ms=0, success=False,
                    error_message="Unsupported provider"
                )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Calculate cost
            cost = (response.tokens_used / 1_000_000) * config.cost_per_1m_tokens

            return LLMResponse(
                text=response.text,
                provider=provider,
                tokens_used=response.tokens_used,
                cost=cost,
                confidence_score=response.confidence_score,
                processing_time_ms=int(processing_time),
                success=True
            )

        except asyncio.TimeoutError:
            return LLMResponse(
                text="", provider=provider, tokens_used=0, cost=0.0,
                confidence_score=0.0, processing_time_ms=config.timeout_seconds * 1000,
                success=False, error_message="Timeout"
            )
        except Exception as e:
            return LLMResponse(
                text="", provider=provider, tokens_used=0, cost=0.0,
                confidence_score=0.0, processing_time_ms=0, success=False,
                error_message=str(e)
            )

    def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get existing conversation context"""
        return self.conversation_contexts.get(session_id)

    def create_conversation_context(
            self,
            session_id: str,
            tenant_id: str,
            user_id: str
    ) -> ConversationContext:
        """Create new conversation context"""
        context = ConversationContext(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            conversation_history=[]
        )
        self.conversation_contexts[session_id] = context
        return context

    def classify_intent(self, message: str) -> ConversationIntent:
        """Classify user intent from message - ENHANCED VERSION"""
        message_lower = message.lower()

        # Enhanced patterns with better status detection
        enhanced_patterns = {
            ConversationIntent.SEARCH_INVOICES: [
                r'find.*invoice', r'search.*invoice', r'show.*invoice',
                r'list.*invoice', r'invoices.*from', r'invoices.*over',
                r'pending.*invoice', r'approved.*invoice', r'rejected.*invoice',  # NEW!
                r'show.*pending', r'list.*pending', r'find.*pending',  # NEW!
                r'show.*approved', r'list.*approved', r'find.*approved',  # NEW!
                r'invoices.*status', r'status.*pending', r'what.*pending'  # NEW!
            ],
            # ... rest of your existing patterns
        }

        # Check enhanced patterns first
        for intent, patterns in enhanced_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent

        # Fallback to original patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent

        return ConversationIntent.UNKNOWN

    def extract_entities(self, message: str) -> ExtractedEntity:
        """Extract relevant entities from user message - FIXED VERSION"""
        entities = ExtractedEntity()
        message_lower = message.lower()

        # Status keywords mapping (NEW!)
        status_keywords = {
            'pending': ['pending', 'awaiting', 'waiting', 'unprocessed', 'review'],
            'approved': ['approved', 'accepted', 'authorized', 'signed off'],
            'rejected': ['rejected', 'denied', 'declined', 'refused'],
            'paid': ['paid', 'payment sent', 'settled', 'completed'],
            'overdue': ['overdue', 'late', 'past due', 'expired']
        }

        # Extract status FIRST (most important for your use case)
        for status, keywords in status_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                entities.approval_status = status
                break

        # Extract amounts (money patterns) - IMPROVED
        amount_patterns = [
            r'\$([0-9,]+\.?[0-9]*)',
            r'([0-9,]+\.?[0-9]*)\s*dollars?',
            r'([0-9,]+\.?[0-9]*)\s*USD',
            r'amount\s+of\s+\$?([0-9,]+\.?[0-9]*)',
            r'total\s+\$?([0-9,]+\.?[0-9]*)'
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    entities.amount = float(amount_str)
                    break
                except ValueError:
                    continue

        # Extract invoice numbers - IMPROVED with better validation
        invoice_patterns = [
            r'invoice\s*#?\s*([A-Z0-9\-]{3,20})',  # Min 3 chars, max 20
            r'inv[\s\-#]*([A-Z0-9\-]{3,20})',
            r'#([A-Z0-9\-]{3,20})',
            r'number\s+([A-Z0-9\-]{3,20})'
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                # Validate: not just single characters or common words
                if len(candidate) >= 3 and candidate.lower() not in ['show', 'pending', 'the', 'and']:
                    entities.invoice_number = candidate
                    break

        # Extract vendor names - COMPLETELY REWRITTEN to avoid false matches
        # Only extract if specific vendor indicators are present
        vendor_patterns = [
            r'(?:from|vendor|supplier|company)\s+([A-Z][a-zA-Z\s&.,\-]{2,40})(?:\s+(?:invoice|for|bill)|\s*$)',
            r'invoices?\s+from\s+([A-Z][a-zA-Z\s&.,\-]{2,40})(?:\s|$)',
            r'([A-Z][a-zA-Z\s&.,\-]{2,40})\s+(?:invoice|bill|statement)',
            r'paid\s+to\s+([A-Z][a-zA-Z\s&.,\-]{2,40})(?:\s|$)'
        ]

        for pattern in vendor_patterns:
            match = re.search(pattern, message)
            if match:
                vendor_candidate = match.group(1).strip()

                # Additional validation: exclude common false matches
                exclude_words = [
                    'show me', 'pending', 'approved', 'rejected', 'total', 'amount',
                    'invoices', 'invoice', 'bills', 'payments', 'dollars', 'usd',
                    'the', 'and', 'or', 'but', 'with', 'from', 'for'
                ]

                vendor_lower = vendor_candidate.lower()

                # Only accept if:
                # 1. Not in exclude words
                # 2. Has reasonable length (3-40 chars)
                # 3. Contains at least one letter
                # 4. Not a query word
                if (vendor_lower not in exclude_words and
                        3 <= len(vendor_candidate) <= 40 and
                        any(c.isalpha() for c in vendor_candidate) and
                        not any(word in vendor_lower for word in ['show', 'pending', 'search', 'find', 'list'])):
                    entities.vendor_name = vendor_candidate
                    break

        return entities

    def check_cost_limits(self, estimated_cost: float) -> bool:
        """Check if we're within cost limits"""

        # Update tracking
        today = datetime.now().date()
        current_month = datetime.now().month

        if self.cost_tracking["daily"]["date"] != today:
            self.cost_tracking["daily"] = {"date": today, "cost": 0.0}

        if self.cost_tracking["monthly"]["month"] != current_month:
            self.cost_tracking["monthly"] = {"month": current_month, "cost": 0.0}

        # Check limits
        daily_total = self.cost_tracking["daily"]["cost"] + estimated_cost
        monthly_total = self.cost_tracking["monthly"]["cost"] + estimated_cost

        if daily_total > self.daily_cost_limit:
            return False

        if monthly_total > self.monthly_cost_limit:
            return False

        return True

    def update_cost_tracking(self, cost: float):
        """Update cost tracking"""
        self.cost_tracking["daily"]["cost"] += cost
        self.cost_tracking["monthly"]["cost"] += cost

    async def call_llm(self, prompt: str, provider: LLMProvider, context: ConversationContext) -> LLMResponse:
        """Call specific LLM provider"""

        start_time = datetime.now()
        config = self.router.llm_configs[provider]

        try:
            if provider == LLMProvider.GEMINI_FLASH:
                if not self.gemini_client:
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="Gemini client not initialized"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_gemini(prompt)),
                    timeout=config.timeout_seconds
                )

            elif provider == LLMProvider.GPT4O_MINI:
                if not self.openai_client:
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="OpenAI client not initialized"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_openai(prompt, config.model_name)),
                    timeout=config.timeout_seconds
                )

            elif provider in [LLMProvider.CLAUDE_HAIKU, LLMProvider.CLAUDE_SONNET]:
                if not self.anthropic_client:
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="Anthropic client not initialized"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_anthropic(prompt, config.model_name)),
                    timeout=config.timeout_seconds
                )

            elif provider == LLMProvider.GPT4_TURBO:
                if not self.openai_client:
                    return LLMResponse(
                        text="", provider=provider, tokens_used=0, cost=0.0,
                        confidence_score=0.0, processing_time_ms=0, success=False,
                        error_message="GPT-4 client not initialized"
                    )

                response = await asyncio.wait_for(
                    asyncio.create_task(self._call_openai(prompt, config.model_name)),
                    timeout=config.timeout_seconds
                )

            else:
                return LLMResponse(
                    text="", provider=provider, tokens_used=0, cost=0.0,
                    confidence_score=0.0, processing_time_ms=0, success=False,
                    error_message="Unsupported provider"
                )

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Calculate cost
            cost = (response.tokens_used / 1_000_000) * config.cost_per_1m_tokens

            return LLMResponse(
                text=response.text,
                provider=provider,
                tokens_used=response.tokens_used,
                cost=cost,
                confidence_score=response.confidence_score,
                processing_time_ms=int(processing_time),
                success=True
            )

        except asyncio.TimeoutError:
            return LLMResponse(
                text="", provider=provider, tokens_used=0, cost=0.0,
                confidence_score=0.0, processing_time_ms=config.timeout_seconds * 1000,
                success=False, error_message="Timeout"
            )
        except Exception as e:
            return LLMResponse(
                text="", provider=provider, tokens_used=0, cost=0.0,
                confidence_score=0.0, processing_time_ms=0, success=False,
                error_message=str(e)
            )

    async def _call_gemini(self, prompt: str) -> LLMResponse:
        """Call Gemini Flash"""
        response = self.gemini_client.generate_content(prompt)
        return LLMResponse(
            text=response.text,
            provider=LLMProvider.GEMINI_FLASH,
            tokens_used=len(prompt.split()) * 1.3,  # Rough estimate
            cost=0.0,  # Will be calculated by caller
            confidence_score=0.85,  # Default confidence
            processing_time_ms=0,
            success=True
        )

    async def _call_openai(self, prompt: str, model: str) -> LLMResponse:
        """Call OpenAI models"""
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )

        return LLMResponse(
            text=response.choices[0].message.content,
            provider=LLMProvider.GPT4O_MINI if "mini" in model else LLMProvider.GPT4_TURBO,
            tokens_used=response.usage.total_tokens,
            cost=0.0,  # Will be calculated by caller
            confidence_score=0.9,
            processing_time_ms=0,
            success=True
        )

    async def _call_anthropic(self, prompt: str, model: str) -> LLMResponse:
        """Call Claude models"""
        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        provider = LLMProvider.CLAUDE_HAIKU if "haiku" in model else LLMProvider.CLAUDE_SONNET

        return LLMResponse(
            text=response.content[0].text,
            provider=provider,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            cost=0.0,  # Will be calculated by caller
            confidence_score=0.92,
            processing_time_ms=0,
            success=True
        )

    async def process_message(
            self,
            message: str,
            context: ConversationContext
    ) -> AIResponse:
        """Process user message with intelligent LLM routing"""

        # Add message to history
        context.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'user',
            'message': message
        })

        # Classify intent and extract entities
        intent = self.classify_intent(message)
        entities = self.extract_entities(message)

        # Analyze query for intelligent routing
        analysis = self.router.analyze_query(message, intent, context)

        # Check cost limits
        config = self.router.llm_configs[analysis.recommended_llm]
        estimated_cost = (analysis.estimated_tokens / 1_000_000) * config.cost_per_1m_tokens

        if not self.check_cost_limits(estimated_cost):
            # Fall back to cheapest option
            analysis.recommended_llm = LLMProvider.GEMINI_FLASH

        # Build enhanced prompt
        prompt = self._build_enhanced_prompt(message, intent, context, analysis)

        # Try primary LLM
        llm_response = await self.call_llm(prompt, analysis.recommended_llm, context)

        # Smart escalation if needed
        max_retries = 2
        retry_count = 0

        while (self.router.should_escalate(llm_response, analysis) and
               retry_count < max_retries):

            next_llm = self.router.get_escalation_llm(llm_response.provider, analysis)
            if not next_llm:
                break

            print(f"🔄 Escalating from {llm_response.provider.value} to {next_llm.value}")
            llm_response = await self.call_llm(prompt, next_llm, context)
            retry_count += 1

        # Update cost tracking
        if llm_response.success:
            self.update_cost_tracking(llm_response.cost)

            # Update context stats
            if llm_response.provider.value not in context.llm_usage_stats:
                context.llm_usage_stats[llm_response.provider.value] = {"calls": 0, "cost": 0.0}

            context.llm_usage_stats[llm_response.provider.value]["calls"] += 1
            context.llm_usage_stats[llm_response.provider.value]["cost"] += llm_response.cost
            context.total_cost += llm_response.cost

        # Process business logic based on intent
        if intent == ConversationIntent.GREETING:
            business_response = await self._handle_greeting(context)
        elif intent == ConversationIntent.SEARCH_INVOICES:
            business_response = await self._handle_search_invoices(context, entities)
        elif intent == ConversationIntent.APPROVE_INVOICE:
            business_response = await self._handle_approve_invoice(context, entities)
        else:
            # Use LLM response as fallback
            business_response = AIResponse(
                text=llm_response.text if llm_response.success else "I'm having trouble processing that request. Please try again.",
                intent=intent,
                llm_used=llm_response.provider,
                cost=llm_response.cost,
                confidence=llm_response.confidence_score
            )

        # Add response to history
        context.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'assistant',
            'message': business_response.text,
            'intent': intent.value,
            'llm_used': llm_response.provider.value if llm_response.success else None,
            'cost': llm_response.cost,
            'processing_time_ms': llm_response.processing_time_ms
        })

        return business_response

    def _build_enhanced_prompt(
            self,
            message: str,
            intent: ConversationIntent,
            context: ConversationContext,
            analysis: QueryAnalysis
    ) -> str:
        """Build enhanced prompt with context and intelligence"""

        base_prompt = f"""You are Ask Vritti, an intelligent AI assistant specializing in invoice processing and business finance.

User Message: "{message}"
Intent: {intent.value}
Complexity: {analysis.complexity.value}
Business Impact: {analysis.business_impact}

Context:
- Tenant: {context.tenant_id}
- Session: {context.session_id}
- Total conversation cost so far: ${context.total_cost:.4f}

You should respond naturally and helpfully. Keep responses concise but informative.
Focus on invoice processing, vendor management, approvals, and financial analytics.

Respond as Ask Vritti in a professional yet friendly tone."""

        return base_prompt

    async def _handle_greeting(self, context: ConversationContext) -> AIResponse:
        """Handle greeting messages with enhanced data"""
        db = get_db_session()
        try:
            tenant = db.query(Tenant).filter(Tenant.id == context.tenant_id).first()
            tenant_name = tenant.name if tenant else "there"

            pending_count = db.query(Invoice).filter(
                Invoice.tenant_id == context.tenant_id,
                Invoice.approval_status == 'pending',
                Invoice.deleted_at.is_(None)
            ).count()

            greeting_text = f"Hello! I'm Ask Vritti, your intelligent AI assistant for {tenant_name}. "

            if pending_count > 0:
                greeting_text += f"You have {pending_count} invoices waiting for approval. "
                greeting_text += "I can help you review them, search invoices, check vendor spending, or answer any questions about your invoice processing."
            else:
                greeting_text += "All your invoices are up to date! I can help you search invoices, analyze spending, or process new documents."

            # Add cost optimization note
            greeting_text += f"\n\n💰 Session cost so far: ${context.total_cost:.4f}"

            return AIResponse(
                text=greeting_text,
                intent=ConversationIntent.GREETING,
                suggested_responses=[
                    "Show me pending invoices",
                    "How much did we spend this month?",
                    "Search invoices from Amazon"
                ]
            )

        finally:
            db.close()

    async def _handle_search_invoices(
        self,
        context: ConversationContext,
        entities: ExtractedEntity
) -> AIResponse:

        db = get_db_session()
        try:
            query = db.query(Invoice).filter(
                Invoice.tenant_id == context.tenant_id,
                Invoice.deleted_at.is_(None)
            )

            # Apply status filter if extracted (THIS IS THE KEY FIX!)
            if entities.approval_status:
                query = query.filter(Invoice.approval_status == entities.approval_status)
                logger.info(f"🔍 Filtering by status: {entities.approval_status}")

            # Apply vendor filter if extracted
            if entities.vendor_name:
                query = query.filter(Invoice.vendor_name.ilike(f"%{entities.vendor_name}%"))
                logger.info(f"🔍 Filtering by vendor: {entities.vendor_name}")

            # Apply amount filter if extracted
            if entities.amount:
                tolerance = entities.amount * 0.1
                query = query.filter(
                    Invoice.total_amount >= entities.amount - tolerance,
                    Invoice.total_amount <= entities.amount + tolerance
                )
                logger.info(f"🔍 Filtering by amount: ${entities.amount}")

            invoices = query.order_by(Invoice.created_at.desc()).limit(10).all()

            if not invoices:
                # Better error message based on what was searched
                search_criteria = []
                if entities.approval_status:
                    search_criteria.append(f"status '{entities.approval_status}'")
                if entities.vendor_name:
                    search_criteria.append(f"vendor '{entities.vendor_name}'")
                if entities.amount:
                    search_criteria.append(f"amount ${entities.amount}")

                criteria_text = " and ".join(search_criteria) if search_criteria else "your criteria"

                return AIResponse(
                    text=f"I couldn't find any invoices matching {criteria_text}. Try a different search or ask me to show all recent invoices.",
                    intent=ConversationIntent.SEARCH_INVOICES,
                    suggested_responses=[
                        "Show me all recent invoices",
                        "Show me all pending invoices",
                        "Show me approved invoices"
                    ]
                )

            # Build response with clear status indication
            status_text = f" {entities.approval_status}" if entities.approval_status else ""
            result_text = f"I found {len(invoices)}{status_text} invoice(s):\n\n"
            total_amount = 0

            for invoice in invoices:
                status_emoji = {
                    'pending': '⏳', 'approved': '✅',
                    'rejected': '❌', 'on_hold': '⏸️'
                }.get(invoice.approval_status, '❓')

                result_text += f"{status_emoji} **{invoice.vendor_name or 'Unknown'}** - ${invoice.total_amount:.2f}\n"
                result_text += f"   Invoice #{invoice.invoice_number or 'N/A'} • {invoice.approval_status.title()}\n\n"
                total_amount += invoice.total_amount or 0

            result_text += f"**Total: ${total_amount:.2f}**"

            return AIResponse(
                text=result_text,
                intent=ConversationIntent.SEARCH_INVOICES,
                suggested_responses=[
                    "Approve all pending invoices",
                    "Show me more details",
                    "Search for different criteria"
                ]
            )

        finally:
            db.close()

    async def _handle_approve_invoice(
            self,
            context: ConversationContext,
            entities: ExtractedEntity
    ) -> AIResponse:
        """Handle invoice approval with enhanced logic"""
        db = get_db_session()
        try:
            query = db.query(Invoice).filter(
                Invoice.tenant_id == context.tenant_id,
                Invoice.approval_status == 'pending',
                Invoice.deleted_at.is_(None)
            )

            if entities.vendor_name:
                query = query.filter(Invoice.vendor_name.ilike(f"%{entities.vendor_name}%"))

            if entities.amount:
                tolerance = entities.amount * 0.05
                query = query.filter(
                    Invoice.total_amount >= entities.amount - tolerance,
                    Invoice.total_amount <= entities.amount + tolerance
                )

            invoices = query.all()

            if not invoices:
                return AIResponse(
                    text="I couldn't find any pending invoices matching your criteria. Would you like me to show you all pending invoices?",
                    intent=ConversationIntent.APPROVE_INVOICE
                )

            if len(invoices) == 1:
                invoice = invoices[0]
                invoice.approval_status = 'approved'
                invoice.approved_by = context.user_id
                invoice.approved_at = datetime.utcnow()
                db.commit()

                return AIResponse(
                    text=f"✅ **Approved!** Invoice from {invoice.vendor_name} for ${invoice.total_amount:.2f} has been approved and sent to accounting.",
                    intent=ConversationIntent.APPROVE_INVOICE,
                    action_required=True,
                    action_type="invoice_approved",
                    action_data={"invoice_id": invoice.id}
                )
            else:
                invoice_list = "\n".join([
                    f"• {inv.vendor_name} - ${inv.total_amount:.2f}"
                    for inv in invoices[:5]
                ])

                return AIResponse(
                    text=f"I found {len(invoices)} pending invoices:\n\n{invoice_list}\n\nWhich one would you like to approve?",
                    intent=ConversationIntent.APPROVE_INVOICE,
                    suggested_responses=["Approve all of them", "Just the first one"]
                )

        finally:
            db.close()

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary"""
        return {
            "daily_cost": self.cost_tracking["daily"]["cost"],
            "daily_limit": self.daily_cost_limit,
            "monthly_cost": self.cost_tracking["monthly"]["cost"],
            "monthly_limit": self.monthly_cost_limit,
            "daily_remaining": self.daily_cost_limit - self.cost_tracking["daily"]["cost"],
            "monthly_remaining": self.monthly_cost_limit - self.cost_tracking["monthly"]["cost"]
        }


# Test function
async def test_ask_vritti():
    """Test Ask Vritti with multiple LLMs"""

    # You'll need to set your API keys
    ask_vritti = AskVrittiAI(
        gemini_api_key="your-gemini-key",
        openai_api_key="your-openai-key",
        anthropic_api_key="your-anthropic-key"
    )

    context = ask_vritti.create_conversation_context(
        session_id="test-session",
        tenant_id="demo-tenant-id",
        user_id="demo-user-id"
    )

    test_messages = [
        "Hello",  # Should use Gemini Flash
        "Show me invoices from Amazon",  # Should use Gemini Flash
        "Analyze my spending patterns this quarter",  # Should use Claude Sonnet
        "Is there any suspicious activity in recent invoices?"  # Should use GPT-4 Turbo
    ]

    for message in test_messages:
        print(f"\n👤 User: {message}")
        response = await ask_vritti.process_message(message, context)
        print(f"🤖 Ask Vritti ({response.llm_used.value if response.llm_used else 'unknown'}): {response.text}")
        print(f"💰 Cost: ${response.cost:.6f}")

    print("\n📊 Final Cost Summary:")
    print(ask_vritti.get_cost_summary())
    print(f"\n🎯 Session Total: ${context.total_cost:.6f}")


if __name__ == "__main__":
    asyncio.run(test_ask_vritti())