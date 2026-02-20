"""
Agent Roles for AI Trading System
Defines the different agent types and their responsibilities
"""

from enum import Enum


class AgentRole(Enum):
    """
    Available agent roles in the trading system
    
    Each role has specific responsibilities:
    - MAYOR: Main coordinator, strategic decisions
    - RESEARCHER: Market analysis and research
    - TRADER: Trade execution specialist
    - RISK_MANAGER: Risk assessment and capital protection
    - REPORTER: Performance tracking and reporting
    """
    MAYOR = "mayor"
    RESEARCHER = "researcher"
    TRADER = "trader"
    RISK_MANAGER = "risk_manager"
    REPORTER = "reporter"


# Role display names and descriptions
ROLE_INFO = {
    AgentRole.MAYOR: {
        "name": "Mayor",
        "description": "Main coordinator of the AI trading system",
        "emoji": "🏛️"
    },
    AgentRole.RESEARCHER: {
        "name": "Researcher", 
        "description": "Market analyst and opportunity finder",
        "emoji": "🔬"
    },
    AgentRole.TRADER: {
        "name": "Trader",
        "description": "Trade execution specialist",
        "emoji": "📈"
    },
    AgentRole.RISK_MANAGER: {
        "name": "Risk Manager",
        "description": "Guardian of capital and risk assessor",
        "emoji": "🛡️"
    },
    AgentRole.REPORTER: {
        "name": "Reporter",
        "description": "Performance analyst and communicator",
        "emoji": "📊"
    }
}


def get_role_info(role: AgentRole) -> dict:
    """Get information about a specific role"""
    return ROLE_INFO.get(role, {
        "name": role.value,
        "description": "AI Assistant",
        "emoji": "🤖"
    })
