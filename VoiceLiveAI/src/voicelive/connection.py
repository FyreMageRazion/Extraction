"""
VoiceLive connection wrapper for Azure VoiceLive SDK.
"""

import logging
from typing import Optional, AsyncContextManager

from azure.core.credentials import AzureKeyCredential
from azure.ai.voicelive.aio import connect, VoiceLiveConnection

logger = logging.getLogger(__name__)


class VoiceLiveConnectionWrapper:
    """Wrapper around Azure VoiceLive SDK connection."""
    
    def __init__(
        self,
        endpoint: str,
        credential: AzureKeyCredential,
        model: str = "gpt-4o-realtime-preview"
    ):
        """
        Initialize the VoiceLive connection wrapper.
        
        Args:
            endpoint: Azure VoiceLive endpoint URL
            credential: Azure credential
            model: Model deployment name
        """
        self.endpoint = endpoint
        self.credential = credential
        self.model = model
        self._connection_manager: Optional[AsyncContextManager] = None
        self.connection: Optional[VoiceLiveConnection] = None
    
    def get_connection_manager(self) -> AsyncContextManager:
        """
        Get the connection context manager.
        
        Returns:
            AsyncContextManager for VoiceLive connection
        """
        if self._connection_manager is None:
            self._connection_manager = connect(
                endpoint=self.endpoint,
                credential=self.credential,
                model=self.model,
            )
        return self._connection_manager
    
    async def __aenter__(self):
        """Enter the context manager."""
        manager = self.get_connection_manager()
        self.connection = await manager.__aenter__()
        logger.info("Connected to VoiceLive")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if self._connection_manager:
            await self._connection_manager.__aexit__(exc_type, exc_val, exc_tb)
            self.connection = None
            self._connection_manager = None
            logger.info("Disconnected from VoiceLive")
