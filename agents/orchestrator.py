"""
AI Agent Orchestrator
Manages multiple AI agents with different roles for the trading system
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import anthropic
from loguru import logger

from agents.roles import AgentRole, get_role_info
from agents.prompts import get_system_prompt


@dataclass
class Agent:
    """Individual AI Agent configuration"""
    name: str
    role: AgentRole
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4096
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Message:
    """A message in the conversation history"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class AgentOrchestrator:
    """
    Manages the AI agent team for trading decisions
    
    Features:
    - Multiple specialized agents with different roles
    - Conversation history management
    - Rate limiting for API calls
    - Structured JSON responses
    """

    def __init__(
        self,
        api_key: str,
        max_history_length: int = 10,
        rate_limit_calls: int = 10,
        rate_limit_period: int = 60
    ):
        """
        Initialize the orchestrator
        
        Args:
            api_key: Anthropic API key
            max_history_length: Maximum conversation history to keep per agent
            rate_limit_calls: Max API calls per period
            rate_limit_period: Rate limit period in seconds
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.agents: Dict[str, Agent] = {}
        self.conversation_history: Dict[str, List[Message]] = {}
        self.max_history_length = max_history_length
        
        # Rate limiting
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period
        self._api_call_times: List[float] = []
        
        logger.info("Agent Orchestrator initialized")

    def create_agent(self, name: str, role: AgentRole, 
                     model: Optional[str] = None,
                     temperature: Optional[float] = None) -> Agent:
        """
        Create a new agent
        
        Args:
            name: Unique name for the agent
            role: Agent's role (MAYOR, RESEARCHER, etc.)
            model: Optional custom model override
            temperature: Optional custom temperature override
            
        Returns:
            Created Agent instance
        """
        agent = Agent(
            name=name,
            role=role,
            model=model or agent.model,
            temperature=temperature or agent.temperature
        )
        self.agents[name] = agent
        self.conversation_history[name] = []
        
        role_info = get_role_info(role)
        logger.info(f"Created agent: {name} ({role_info['emoji']} {role_info['name']})")
        
        return agent

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name"""
        return self.agents.get(name)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return [
            {
                "name": agent.name,
                "role": agent.role.value,
                "model": agent.model,
                "created_at": agent.created_at.isoformat()
            }
            for agent in self.agents.values()
        ]

    async def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits"""
        import time
        
        now = time.time()
        
        # Remove calls outside the current period
        self._api_call_times = [
            t for t in self._api_call_times 
            if now - t < self.rate_limit_period
        ]
        
        # If at limit, wait
        if len(self._api_call_times) >= self.rate_limit_calls:
            oldest_call = min(self._api_call_times)
            sleep_time = self.rate_limit_period - (now - oldest_call)
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, waiting {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
                return await self._wait_for_rate_limit()  # Retry after waiting
        
        # Record this call
        self._api_call_times.append(now)

    async def send_message(
        self,
        agent_name: str,
        message: str,
        system_prompt: Optional[str] = None,
        require_json: bool = False
    ) -> str:
        """
        Send a message to an agent and get response
        
        Args:
            agent_name: Name of the agent to message
            message: User message
            system_prompt: Optional custom system prompt override
            require_json: If True, try to extract JSON from response
            
        Returns:
            Agent's response
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not found")

        agent = self.agents[agent_name]

        # Get system prompt
        if system_prompt is None:
            system_prompt = get_system_prompt(agent.role)

        # Build messages for API
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history[agent_name]
        ]
        messages.append({"role": "user", "content": message})

        # Wait for rate limit
        await self._wait_for_rate_limit()

        try:
            # Make API call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model=agent.model,
                    max_tokens=agent.max_tokens,
                    temperature=agent.temperature,
                    system=system_prompt,
                    messages=messages
                )
            )

            assistant_message = response.content[0].text

            # Update conversation history
            self.conversation_history[agent_name].append(
                Message(role="user", content=message)
            )
            self.conversation_history[agent_name].append(
                Message(role="assistant", content=assistant_message)
            )

            # Trim history if too long
            while len(self.conversation_history[agent_name]) > self.max_history_length:
                self.conversation_history[agent_name].pop(0)

            # Extract JSON if requested
            if require_json:
                extracted = self._extract_json(assistant_message)
                if extracted:
                    return extracted
                logger.warning(f"Failed to extract JSON from {agent_name}'s response")

            return assistant_message

        except Exception as e:
            logger.error(f"Error communicating with agent {agent_name}: {e}")
            raise

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text response"""
        try:
            # Try to find JSON object in response
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = text[start:end]
                # Validate JSON
                json.loads(json_str)
                return json_str
        except (json.JSONDecodeError, ValueError):
            pass
        
        return None

    def clear_history(self, agent_name: Optional[str] = None) -> None:
        """
        Clear conversation history
        
        Args:
            agent_name: Specific agent to clear, or None for all
        """
        if agent_name:
            if agent_name in self.conversation_history:
                self.conversation_history[agent_name] = []
                logger.debug(f"Cleared history for agent: {agent_name}")
        else:
            self.conversation_history = {name: [] for name in self.conversation_history}
            logger.debug("Cleared all conversation history")

    async def town_meeting(
        self,
        topic: str,
        participating_agents: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Have multiple agents discuss a topic
        
        Args:
            topic: Discussion topic
            participating_agents: List of agent names to include (default: all)
            
        Returns:
            Dictionary of agent responses
        """
        if participating_agents is None:
            participating_agents = list(self.agents.keys())

        responses = {}

        # Mayor introduces the topic
        if "mayor" in self.agents:
            mayor_message = await self.send_message(
                "mayor",
                f"We need to discuss: {topic}. Please provide your perspective and coordinate with other agents."
            )
            responses["mayor"] = mayor_message
        else:
            mayor_message = ""

        # Other agents respond
        for agent_name in participating_agents:
            if agent_name == "mayor" or agent_name not in self.agents:
                continue

            context = f"""The Mayor says: {mayor_message}

Topic: {topic}

Provide your professional opinion from your role's perspective."""

            response = await self.send_message(agent_name, context)
            responses[agent_name] = response

        # Mayor makes final decision
        if "mayor" in self.agents:
            summary = "\n\n".join(
                [f"{name}: {resp}" for name, resp in responses.items()]
            )
            final_decision = await self.send_message(
                "mayor",
                f"Based on all perspectives:\n\n{summary}\n\nWhat is your final decision or recommendation?"
            )
            responses["final_decision"] = final_decision

        return responses

    def get_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about agent usage"""
        stats = {}
        for name, history in self.conversation_history.items():
            stats[name] = {
                "message_count": len(history),
                "user_messages": sum(1 for m in history if m.role == "user"),
                "assistant_messages": sum(1 for m in history if m.role == "assistant"),
            }
        return stats
