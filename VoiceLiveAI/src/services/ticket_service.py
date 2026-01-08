"""
Ticket service - business logic layer for ticket operations.
"""

import logging
from typing import Dict, Any, Optional

from ..database.db import TicketDatabase
from ..database.models import Ticket

logger = logging.getLogger(__name__)


class TicketService:
    """Service layer for ticket operations."""
    
    def __init__(self, db: TicketDatabase):
        """
        Initialize the ticket service.
        
        Args:
            db: TicketDatabase instance
        """
        self.db = db
    
    def check_ticket_status(self, ticket_id: str) -> Dict[str, Any]:
        """
        Check the status and details of a ticket.
        
        Args:
            ticket_id: The ticket ID to check
        
        Returns:
            Dictionary with ticket information or error message
        """
        ticket = self.db.get_ticket_by_id(ticket_id)
        
        if not ticket:
            return {
                "found": False,
                "message": f"Ticket {ticket_id} not found. Please check your ticket ID and try again."
            }
        
        # Format ticket information for voice response
        status_messages = {
            "open": "is currently open and awaiting assignment",
            "in_progress": "is in progress and being worked on",
            "resolved": "has been resolved",
            "closed": "has been closed"
        }
        
        status_message = status_messages.get(ticket.status, f"has status {ticket.status}")
        
        result = {
            "found": True,
            "ticket_id": ticket.ticket_id,
            "type": ticket.type,
            "status": ticket.status,
            "status_message": status_message,
            "description": ticket.description,
            "priority": ticket.priority,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "message": (
                f"Ticket {ticket.ticket_id} ({ticket.type}) {status_message}. "
                f"Description: {ticket.description}. "
                f"Priority: {ticket.priority}. "
                f"Created on {ticket.created_at.strftime('%B %d, %Y') if ticket.created_at else 'unknown date'}."
            )
        }
        
        return result
    
    def create_ticket(
        self,
        ticket_type: str,
        description: str,
        priority: str
    ) -> Dict[str, Any]:
        """
        Create a new support ticket.
        
        Args:
            ticket_type: Type of ticket ("HR" or "IT")
            description: Description of the issue
            priority: Priority level ("low", "medium", "high", "urgent")
        
        Returns:
            Dictionary with ticket creation result
        """
        # Validate inputs
        if ticket_type.upper() not in ["HR", "IT"]:
            return {
                "success": False,
                "message": f"Invalid ticket type: {ticket_type}. Must be 'HR' or 'IT'."
            }
        
        if priority.lower() not in ["low", "medium", "high", "urgent"]:
            return {
                "success": False,
                "message": f"Invalid priority: {priority}. Must be 'low', 'medium', 'high', or 'urgent'."
            }
        
        # Normalize inputs
        ticket_type = ticket_type.upper()
        priority = priority.lower()
        
        # Create ticket
        ticket = self.db.create_ticket(ticket_type, description, priority)
        
        if not ticket:
            return {
                "success": False,
                "message": "Failed to create ticket. Please try again."
            }
        
        return {
            "success": True,
            "ticket_id": ticket.ticket_id,
            "type": ticket.type,
            "status": ticket.status,
            "priority": ticket.priority,
            "message": (
                f"Ticket {ticket.ticket_id} has been created successfully. "
                f"Type: {ticket.type}, Priority: {ticket.priority}. "
                f"Your ticket is now open and will be assigned to a support agent."
            )
        }
