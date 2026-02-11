"""
AI Agent Platform - Core Interfaces.

Defines the foundational abstractions for the multi-agent system.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class AgentRole(Enum):
    """Agent role/specialty."""

    RESEARCHER = "researcher"
    ANALYST = "analyst"
    SUMMARIZER = "summarizer"
    CLASSIFIER = "classifier"
    TRANSLATOR = "translator"
    ORCHESTRATOR = "orchestrator"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(Enum):
    """Message role in conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in an agent conversation."""

    role: MessageRole
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Tool:
    """
    A tool that agents can use.

    Tools are functions that agents can call to perform actions
    or retrieve information.
    """

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    function: Callable
    async_function: bool = False


@dataclass
class ToolCall:
    """A request to call a tool."""

    id: str
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Result from a tool execution."""

    tool_call_id: str
    result: Any
    error: Optional[str] = None


@dataclass
class AgentTask:
    """A task assigned to an agent."""

    id: UUID = field(default_factory=uuid4)
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    role: AgentRole
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: List[str] = field(default_factory=list)  # Tool names
    system_prompt: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """
    Abstract base class for AI agents.

    Agents are autonomous entities that can:
    - Process tasks
    - Use tools
    - Make decisions
    - Communicate with other agents
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize agent.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.status = AgentStatus.IDLE
        self._conversation_history: List[Message] = []

    @abstractmethod
    async def process_task(self, task: AgentTask) -> Any:
        """
        Process a task.

        Args:
            task: Task to process

        Returns:
            Task result
        """
        pass

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
    ) -> Union[str, List[ToolCall]]:
        """
        Generate a response to messages.

        Args:
            messages: Conversation messages
            tools: Available tools

        Returns:
            Text response or list of tool calls
        """
        pass

    async def use_tool(
        self,
        tool: Tool,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Use a tool.

        Args:
            tool: Tool to use
            arguments: Tool arguments

        Returns:
            Tool result
        """
        try:
            if tool.async_function:
                return await tool.function(**arguments)
            else:
                return tool.function(**arguments)
        except Exception as e:
            raise RuntimeError(f"Tool {tool.name} failed: {e}")

    def add_message(self, message: Message) -> None:
        """
        Add a message to conversation history.

        Args:
            message: Message to add
        """
        self._conversation_history.append(message)

    def get_conversation_history(self) -> List[Message]:
        """
        Get conversation history.

        Returns:
            List of messages
        """
        return self._conversation_history.copy()

    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history = []


class AgentRegistry(ABC):
    """
    Registry for managing available agents.

    Provides:
    - Agent registration
    - Agent discovery
    - Agent lifecycle management
    """

    @abstractmethod
    async def register(self, agent: Agent) -> None:
        """
        Register an agent.

        Args:
            agent: Agent to register
        """
        pass

    @abstractmethod
    async def unregister(self, agent_name: str) -> None:
        """
        Unregister an agent.

        Args:
            agent_name: Name of agent to unregister
        """
        pass

    @abstractmethod
    async def get(self, agent_name: str) -> Optional[Agent]:
        """
        Get an agent by name.

        Args:
            agent_name: Agent name

        Returns:
            Agent or None if not found
        """
        pass

    @abstractmethod
    async def list_agents(self) -> List[str]:
        """
        List all registered agents.

        Returns:
            List of agent names
        """
        pass


class ToolRegistry(ABC):
    """
    Registry for managing tools that agents can use.

    Provides:
    - Tool registration
    - Tool discovery
    - Tool validation
    """

    @abstractmethod
    async def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool to register
        """
        pass

    @abstractmethod
    async def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of tool to unregister
        """
        pass

    @abstractmethod
    async def get(self, tool_name: str) -> Optional[Tool]:
        """
        Get a tool by name.

        Args:
            tool_name: Tool name

        Returns:
            Tool or None if not found
        """
        pass

    @abstractmethod
    async def list_tools(self) -> List[str]:
        """
        List all registered tools.

        Returns:
            List of tool names
        """
        pass


class AgentOrchestrator(ABC):
    """
    Orchestrates multi-agent collaboration.

    Coordinates:
    - Task distribution
    - Agent communication
    - Workflow execution
    - Result aggregation
    """

    @abstractmethod
    async def execute_task(
        self,
        task: AgentTask,
        agents: Optional[List[str]] = None,
    ) -> Any:
        """
        Execute a task using one or more agents.

        Args:
            task: Task to execute
            agents: Optional list of agent names to use

        Returns:
            Task result
        """
        pass

    @abstractmethod
    async def broadcast_message(
        self,
        message: Message,
        agents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Broadcast a message to agents.

        Args:
            message: Message to broadcast
            agents: Optional list of agent names (all if None)

        Returns:
            Dictionary of agent responses
        """
        pass
