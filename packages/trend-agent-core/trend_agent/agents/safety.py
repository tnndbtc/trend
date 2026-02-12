"""
Safety and Stability Mechanisms for Agent Control Plane.

Provides risk scoring, confidence assessment, and trust management.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

from trend_agent.agents.interface import AgentTask

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classifications."""

    MINIMAL = "minimal"  # < 20
    LOW = "low"  # 20-40
    MEDIUM = "medium"  # 40-60
    HIGH = "high"  # 60-80
    CRITICAL = "critical"  # > 80


class TrustLevel(Enum):
    """Agent trust levels."""

    UNTRUSTED = 0  # New agent, no history
    BASIC = 1  # Limited successful operations
    STANDARD = 2  # Proven track record
    ELEVATED = 3  # Extensive successful operations
    FULLY_TRUSTED = 4  # Maximum autonomy


@dataclass
class RiskAssessment:
    """Risk assessment result."""

    risk_score: float  # 0-100
    risk_level: RiskLevel
    factors: Dict[str, float]  # Individual risk factors
    requires_approval: bool
    approval_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfidenceScore:
    """Confidence score for agent output."""

    confidence: float  # 0-1
    source_quality: float  # 0-1
    consistency: float  # 0-1
    uncertainty: float  # 0-1
    factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPerformanceRecord:
    """Agent performance tracking."""

    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_duration: float = 0.0
    total_cost: float = 0.0
    policy_violations: int = 0
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.failed_tasks / self.total_tasks


class RiskScorer:
    """
    Multi-dimensional risk assessment for agent operations.

    Factors:
    - Cost (budget impact)
    - Scope (number of resources affected)
    - Impact (severity of changes)
    - Novelty (new vs proven patterns)
    - Chain depth (causality chain length)
    """

    # Risk weights
    WEIGHTS = {
        "cost": 0.25,
        "scope": 0.20,
        "impact": 0.25,
        "novelty": 0.15,
        "chain_depth": 0.15,
    }

    def __init__(
        self,
        cost_threshold_high: float = 10.0,
        scope_threshold_high: int = 100,
        chain_depth_threshold: int = 10,
    ):
        """
        Initialize risk scorer.

        Args:
            cost_threshold_high: Cost above which is high risk
            scope_threshold_high: Scope above which is high risk
            chain_depth_threshold: Chain depth above which is high risk
        """
        self._cost_threshold_high = cost_threshold_high
        self._scope_threshold_high = scope_threshold_high
        self._chain_depth_threshold = chain_depth_threshold

        logger.info("Risk Scorer initialized")

    async def assess_risk(
        self,
        task: AgentTask,
        agent_id: str,
        estimated_cost: float = 0.0,
        scope_size: int = 1,
        impact_level: str = "low",
        is_novel: bool = False,
        chain_depth: int = 0,
    ) -> RiskAssessment:
        """
        Assess risk for agent task.

        Args:
            task: Task to assess
            agent_id: Agent ID
            estimated_cost: Estimated cost in USD
            scope_size: Number of resources affected
            impact_level: Impact level (low, medium, high)
            is_novel: Whether task uses novel patterns
            chain_depth: Depth in causality chain

        Returns:
            Risk assessment
        """
        factors = {}

        # 1. Cost risk (0-100)
        cost_risk = min(100, (estimated_cost / self._cost_threshold_high) * 100)
        factors["cost"] = cost_risk

        # 2. Scope risk (0-100)
        scope_risk = min(100, (scope_size / self._scope_threshold_high) * 100)
        factors["scope"] = scope_risk

        # 3. Impact risk (0-100)
        impact_map = {"low": 20, "medium": 50, "high": 80, "critical": 100}
        impact_risk = impact_map.get(impact_level.lower(), 50)
        factors["impact"] = impact_risk

        # 4. Novelty risk (0-100)
        novelty_risk = 80 if is_novel else 20
        factors["novelty"] = novelty_risk

        # 5. Chain depth risk (0-100)
        chain_risk = min(100, (chain_depth / self._chain_depth_threshold) * 100)
        factors["chain_depth"] = chain_risk

        # Calculate weighted risk score
        risk_score = sum(
            factors[factor] * self.WEIGHTS[factor]
            for factor in self.WEIGHTS.keys()
        )

        # Determine risk level
        risk_level = self._classify_risk(risk_score)

        # Determine if approval required
        requires_approval = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        approval_reason = None

        if requires_approval:
            high_factors = [
                f"{factor}={value:.1f}"
                for factor, value in factors.items()
                if value >= 60
            ]
            approval_reason = f"High risk factors: {', '.join(high_factors)}"

        assessment = RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            factors=factors,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
        )

        logger.info(
            f"Risk assessed: {agent_id} - {task.id} "
            f"(score={risk_score:.1f}, level={risk_level.value})"
        )

        return assessment

    def _classify_risk(self, score: float) -> RiskLevel:
        """
        Classify risk score into level.

        Args:
            score: Risk score (0-100)

        Returns:
            Risk level
        """
        if score < 20:
            return RiskLevel.MINIMAL
        elif score < 40:
            return RiskLevel.LOW
        elif score < 60:
            return RiskLevel.MEDIUM
        elif score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


class ConfidenceScorer:
    """
    Confidence scoring for agent outputs.

    Factors:
    - Source quality (reliability of data sources)
    - Consistency (agreement between multiple sources)
    - Uncertainty (model's own uncertainty)
    - Historical accuracy (agent's track record)
    """

    def __init__(self):
        """Initialize confidence scorer."""
        logger.info("Confidence Scorer initialized")

    async def score_output(
        self,
        agent_id: str,
        output: Any,
        sources: Optional[List[Dict[str, Any]]] = None,
        model_uncertainty: Optional[float] = None,
        performance_record: Optional[AgentPerformanceRecord] = None,
    ) -> ConfidenceScore:
        """
        Score confidence in agent output.

        Args:
            agent_id: Agent ID
            output: Agent output
            sources: Data sources used
            model_uncertainty: Model's reported uncertainty
            performance_record: Agent's performance history

        Returns:
            Confidence score
        """
        factors = {}

        # 1. Source quality (0-1)
        source_quality = self._assess_source_quality(sources or [])
        factors["source_quality"] = source_quality

        # 2. Consistency (0-1)
        consistency = self._assess_consistency(sources or [])
        factors["consistency"] = consistency

        # 3. Model uncertainty (0-1, inverted)
        if model_uncertainty is not None:
            uncertainty = 1.0 - model_uncertainty
        else:
            uncertainty = 0.5  # Neutral if unknown
        factors["uncertainty"] = uncertainty

        # 4. Historical accuracy (0-1)
        if performance_record:
            historical = performance_record.success_rate()
        else:
            historical = 0.5  # Neutral for new agents
        factors["historical_accuracy"] = historical

        # Calculate overall confidence (weighted average)
        weights = {
            "source_quality": 0.3,
            "consistency": 0.25,
            "uncertainty": 0.25,
            "historical_accuracy": 0.2,
        }

        confidence = sum(
            factors.get(factor, 0.5) * weight
            for factor, weight in weights.items()
        )

        score = ConfidenceScore(
            confidence=confidence,
            source_quality=source_quality,
            consistency=consistency,
            uncertainty=uncertainty,
            factors=factors,
        )

        logger.debug(
            f"Confidence scored: {agent_id} (confidence={confidence:.2f})"
        )

        return score

    def _assess_source_quality(self, sources: List[Dict[str, Any]]) -> float:
        """
        Assess quality of data sources.

        Args:
            sources: List of sources

        Returns:
            Quality score (0-1)
        """
        if not sources:
            return 0.5  # Neutral if no sources

        # Simple heuristic: average source reliability
        # In production, use source reputation system
        total_quality = 0.0

        for source in sources:
            # Check source type
            source_type = source.get("type", "unknown")
            quality_map = {
                "database": 0.9,
                "api_response": 0.8,
                "verified_web": 0.7,
                "web_scrape": 0.5,
                "user_input": 0.6,
                "unknown": 0.3,
            }
            total_quality += quality_map.get(source_type, 0.5)

        return total_quality / len(sources)

    def _assess_consistency(self, sources: List[Dict[str, Any]]) -> float:
        """
        Assess consistency between sources.

        Args:
            sources: List of sources

        Returns:
            Consistency score (0-1)
        """
        if len(sources) < 2:
            return 1.0  # Single source is consistent with itself

        # In production, compare source content/values
        # For now, return neutral score
        return 0.75


class TrustManager:
    """
    Manages agent trust levels based on performance.

    Trust calculation factors:
    - Success rate
    - Time in production
    - Total operations completed
    - Policy violations
    - Cost efficiency
    """

    # Trust level thresholds
    TRUST_THRESHOLDS = {
        TrustLevel.UNTRUSTED: {"min_tasks": 0, "min_success_rate": 0.0},
        TrustLevel.BASIC: {"min_tasks": 10, "min_success_rate": 0.7},
        TrustLevel.STANDARD: {"min_tasks": 100, "min_success_rate": 0.85},
        TrustLevel.ELEVATED: {"min_tasks": 500, "min_success_rate": 0.92},
        TrustLevel.FULLY_TRUSTED: {"min_tasks": 1000, "min_success_rate": 0.95},
    }

    def __init__(self):
        """Initialize trust manager."""
        self._performance_records: Dict[str, AgentPerformanceRecord] = {}

        logger.info("Trust Manager initialized")

    def get_or_create_record(self, agent_id: str) -> AgentPerformanceRecord:
        """
        Get or create performance record.

        Args:
            agent_id: Agent ID

        Returns:
            Performance record
        """
        if agent_id not in self._performance_records:
            self._performance_records[agent_id] = AgentPerformanceRecord(
                agent_id=agent_id
            )

        return self._performance_records[agent_id]

    def record_task_completion(
        self,
        agent_id: str,
        success: bool,
        duration: float,
        cost: float,
    ) -> None:
        """
        Record task completion.

        Args:
            agent_id: Agent ID
            success: Whether task succeeded
            duration: Task duration in seconds
            cost: Task cost in USD
        """
        record = self.get_or_create_record(agent_id)

        record.total_tasks += 1
        if success:
            record.successful_tasks += 1
        else:
            record.failed_tasks += 1

        # Update average duration (running average)
        record.average_duration = (
            (record.average_duration * (record.total_tasks - 1) + duration)
            / record.total_tasks
        )

        record.total_cost += cost
        record.last_active = datetime.utcnow()

        logger.debug(
            f"Task recorded: {agent_id} "
            f"(success={success}, total={record.total_tasks})"
        )

    def record_policy_violation(self, agent_id: str) -> None:
        """
        Record policy violation.

        Args:
            agent_id: Agent ID
        """
        record = self.get_or_create_record(agent_id)
        record.policy_violations += 1

        logger.warning(
            f"Policy violation recorded: {agent_id} "
            f"(total={record.policy_violations})"
        )

    def calculate_trust_level(self, agent_id: str) -> TrustLevel:
        """
        Calculate trust level for agent.

        Args:
            agent_id: Agent ID

        Returns:
            Trust level
        """
        record = self.get_or_create_record(agent_id)

        # Start from highest level and work down
        for level in reversed(list(TrustLevel)):
            threshold = self.TRUST_THRESHOLDS[level]

            if (
                record.total_tasks >= threshold["min_tasks"]
                and record.success_rate() >= threshold["min_success_rate"]
                and record.policy_violations == 0  # No violations for elevated trust
            ):
                return level

        return TrustLevel.UNTRUSTED

    def get_performance_summary(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Get performance summary.

        Args:
            agent_id: Agent ID

        Returns:
            Performance summary
        """
        record = self.get_or_create_record(agent_id)
        trust_level = self.calculate_trust_level(agent_id)

        return {
            "agent_id": agent_id,
            "trust_level": trust_level.name,
            "total_tasks": record.total_tasks,
            "success_rate": record.success_rate(),
            "failure_rate": record.failure_rate(),
            "average_duration": record.average_duration,
            "total_cost": record.total_cost,
            "policy_violations": record.policy_violations,
            "age_days": (datetime.utcnow() - record.first_seen).days,
            "last_active": record.last_active.isoformat(),
        }
