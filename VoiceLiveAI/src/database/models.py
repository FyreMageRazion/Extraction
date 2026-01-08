"""
SQLite database models for ticket management.
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any


class Ticket:
    """Ticket model for HR/IT support tickets."""
    
    def __init__(
        self,
        ticket_id: str,
        ticket_type: str,
        description: str,
        priority: str,
        status: str = "open",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        id: Optional[int] = None,
    ):
        self.id = id
        self.ticket_id = ticket_id
        self.type = ticket_type  # "HR" or "IT"
        self.description = description
        self.priority = priority  # "low", "medium", "high", "urgent"
        self.status = status  # "open", "in_progress", "resolved", "closed"
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "type": self.type,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> "Ticket":
        """Create Ticket from database row."""
        return cls(
            id=row[0],
            ticket_id=row[1],
            ticket_type=row[2],
            description=row[3],
            priority=row[4],
            status=row[5],
            created_at=datetime.fromisoformat(row[6]) if row[6] else None,
            updated_at=datetime.fromisoformat(row[7]) if row[7] else None,
        )
