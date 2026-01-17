"""
Function tools for VoiceLive - ticket status checking and creation.
"""

from azure.ai.voicelive.models import FunctionTool, ToolType


def get_ticket_status_tool() -> FunctionTool:
    """
    Get the function tool definition for checking ticket status.
    
    Returns:
        FunctionTool instance
    """
    return FunctionTool(
        type=ToolType.FUNCTION,
        name="get_ticket_status",
        description=(
            "Check the status and details of a support ticket by ticket ID. "
            "Use when user asks about ticket status, ticket details, or wants to know about a specific ticket."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "The ticket ID provided by the user (e.g., TKT-HR-00001, TKT-IT-00042)"
                }
            },
            "required": ["ticket_id"]
        }
    )


def create_support_ticket_tool() -> FunctionTool:
    """
    Get the function tool definition for creating support tickets.
    
    Returns:
        FunctionTool instance
    """
    return FunctionTool(
        type=ToolType.FUNCTION,
        name="create_support_ticket",
        description=(
            "Create a new support ticket for HR or IT issues. "
            "Use when user reports a problem, requests help, or wants to create a ticket. "
            "ALWAYS speak the complete ticket information returned by this function to the user."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ticket_type": {
                    "type": "string",
                    "enum": ["HR", "IT"],
                    "description": "Type of ticket - HR for human resources issues, IT for technical/IT issues"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the issue or problem reported by the user"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Priority level - low for minor issues, medium for normal issues, high for important issues, urgent for critical issues"
                }
            },
            "required": ["ticket_type", "description", "priority"]
        }
    )


def get_all_tools() -> list[FunctionTool]:
    """
    Get all function tools.
    
    Returns:
        List of FunctionTool instances
    """
    return [
        get_ticket_status_tool(),
        create_support_ticket_tool(),
    ]
