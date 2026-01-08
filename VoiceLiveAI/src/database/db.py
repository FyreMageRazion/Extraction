"""
Database operations for ticket management using SQLite.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .models import Ticket

logger = logging.getLogger(__name__)


class TicketDatabase:
    """SQLite database manager for tickets."""
    
    def __init__(self, db_path: str = "data/tickets.db"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket_id TEXT UNIQUE NOT NULL,
                        type TEXT NOT NULL CHECK(type IN ('HR', 'IT')),
                        description TEXT NOT NULL,
                        priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
                        status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'resolved', 'closed')),
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """
        Retrieve a ticket by ticket_id.
        
        Args:
            ticket_id: The ticket ID to look up
        
        Returns:
            Ticket object if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, ticket_id, type, description, priority, status, created_at, updated_at FROM tickets WHERE ticket_id = ?",
                    (ticket_id,)
                )
                row = cursor.fetchone()
                if row:
                    return Ticket.from_row(row)
                return None
        except Exception as e:
            logger.error(f"Error retrieving ticket {ticket_id}: {e}")
            return None
    
    def create_ticket(
        self,
        ticket_type: str,
        description: str,
        priority: str
    ) -> Optional[Ticket]:
        """
        Create a new ticket.
        
        Args:
            ticket_type: Type of ticket ("HR" or "IT")
            description: Description of the issue
            priority: Priority level ("low", "medium", "high", "urgent")
        
        Returns:
            Created Ticket object, or None if creation failed
        """
        # Generate ticket ID
        ticket_id = self._generate_ticket_id(ticket_type)
        
        now = datetime.now().isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO tickets (ticket_id, type, description, priority, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'open', ?, ?)
                    """,
                    (ticket_id, ticket_type, description, priority, now, now)
                )
                conn.commit()
                
                # Retrieve the created ticket
                return self.get_ticket_by_id(ticket_id)
        except sqlite3.IntegrityError as e:
            logger.error(f"Ticket ID collision for {ticket_id}: {e}")
            # Retry with a new ID
            return self.create_ticket(ticket_type, description, priority)
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            return None
    
    def update_ticket_status(self, ticket_id: str, status: str) -> bool:
        """
        Update the status of a ticket.
        
        Args:
            ticket_id: The ticket ID to update
            status: New status ("open", "in_progress", "resolved", "closed")
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tickets SET status = ?, updated_at = ? WHERE ticket_id = ?",
                    (status, datetime.now().isoformat(), ticket_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            return False
    
    def _generate_ticket_id(self, ticket_type: str) -> str:
        """
        Generate a unique ticket ID.
        
        Args:
            ticket_type: Type of ticket ("HR" or "IT")
        
        Returns:
            Unique ticket ID in format TKT-{TYPE}-{NUMBER}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Get the highest number for this ticket type
                cursor.execute(
                    "SELECT ticket_id FROM tickets WHERE ticket_id LIKE ? ORDER BY ticket_id DESC LIMIT 1",
                    (f"TKT-{ticket_type}-%",)
                )
                row = cursor.fetchone()
                
                if row:
                    # Extract number from existing ticket ID
                    last_id = row[0]
                    try:
                        last_num = int(last_id.split("-")[-1])
                        new_num = last_num + 1
                    except (ValueError, IndexError):
                        new_num = 1
                else:
                    new_num = 1
                
                return f"TKT-{ticket_type}-{new_num:05d}"
        except Exception as e:
            logger.error(f"Error generating ticket ID: {e}")
            # Fallback: use timestamp
            timestamp = int(datetime.now().timestamp())
            return f"TKT-{ticket_type}-{timestamp}"


def init_db(db_path: str = "data/tickets.db") -> TicketDatabase:
    """
    Initialize the database.
    
    Args:
        db_path: Path to the SQLite database file
    
    Returns:
        TicketDatabase instance
    """
    return TicketDatabase(db_path)
