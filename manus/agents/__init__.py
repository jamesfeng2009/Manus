"""Agent system for Manus."""

from manus.agents.react import ReActAgent, ReActAgentWithReflection, AgentState
from manus.agents.team import AgentTeam, SimpleAgentTeam, TeamMember, TeamResult, TeamRole
from manus.agents.verifier import VerifierAgent
from manus.agents.state import TaskState, SubTask, SubTaskStatus, Phase
from manus.agents.reflector import Reflector, ReflectionResult, RetryDecision
from manus.agents.enhanced import EnhancedAgent
from manus.agents.executor import ReActExecutor, get_executor, TaskCancelledError, TaskTimeoutError
from manus.agents.reflector_executor import ReflectorRetryExecutor, get_reflector_executor, RetryConfig, RetryRecord
from manus.agents.error_tracker import ErrorTracker, ErrorCategory, ErrorSeverity, ErrorRecord, ErrorPattern, ErrorStats, get_error_tracker
from manus.agents.learning_engine import LearningEngine, TaskComplexity, StrategyType, TaskExample, StrategyPerformance, LearningInsight, ExecutionStrategy, get_learning_engine
from manus.agents.callbacks import (
    ExecutorCallbacks,
    ExecutionState,
    ExecutionResult,
    ExecutionStatus,
    StepRecord,
)
from manus.core.types import TaskPlan

import manus.agents.planner as planner_module
PlannerAgent = getattr(planner_module, 'PlannerAgent', None)

__all__ = [
    "ReActAgent",
    "ReActAgentWithReflection",
    "AgentState",
    "PlannerAgent",
    "TaskPlan",
    "VerifierAgent",
    "AgentTeam",
    "SimpleAgentTeam",
    "TeamMember",
    "TeamResult",
    "TeamRole",
    "TaskState",
    "SubTask",
    "SubTaskStatus",
    "Phase",
    "Reflector",
    "ReflectionResult",
    "RetryDecision",
    "EnhancedAgent",
    "ReActExecutor",
    "get_executor",
    "ReflectorRetryExecutor",
    "get_reflector_executor",
    "RetryConfig",
    "RetryRecord",
    "ErrorTracker",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorRecord",
    "ErrorPattern",
    "ErrorStats",
    "get_error_tracker",
    "LearningEngine",
    "TaskComplexity",
    "StrategyType",
    "TaskExample",
    "StrategyPerformance",
    "LearningInsight",
    "ExecutionStrategy",
    "get_learning_engine",
    "ExecutorCallbacks",
    "ExecutionState",
    "ExecutionResult",
    "ExecutionStatus",
    "StepRecord",
    "TaskCancelledError",
    "TaskTimeoutError",
]
