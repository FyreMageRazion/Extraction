"""
Main entry point for HR/IT Support Desk Voice Agent.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from azure.core.credentials import AzureKeyCredential

from .audio.processor import AudioProcessor
from .config import config
from .database.db import init_db
from .services.ticket_service import TicketService
from .voicelive.assistant import SupportAssistant
from .voicelive.connection import VoiceLiveConnectionWrapper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the Support Desk Assistant."""
    # Check required configuration
    api_key = config["azure_voicelive_api_key"]
    if not api_key:
        logger.error("AZURE_VOICELIVE_API_KEY environment variable not set.")
        sys.exit(1)
    
    endpoint = config["azure_voicelive_endpoint"]
    model = config["voicelive_model"]
    voice = config["voicelive_voice"]
    database_path = config["database_path"]
    instructions = config.get("instructions")
    recording_dir = config.get("recording_dir", "recordings")
    
    # Initialize database
    logger.info(f"Initializing database at {database_path}")
    db = init_db(database_path)
    
    # Initialize ticket service
    ticket_service = TicketService(db)
    
    # List available microphones
    print("\n" + "=" * 70)
    print("Available Microphones:")
    input_devices = AudioProcessor.list_input_devices()
    if not input_devices:
        logger.error("No audio input devices found. Please check your microphone.")
        sys.exit(1)
    
    for device in input_devices[:5]:
        default_marker = " (DEFAULT)" if device['default'] else ""
        print(f"  [{device['index']}] {device['name']}{default_marker}")
    if len(input_devices) > 5:
        print(f"  ... and {len(input_devices) - 5} more")
    
    # Use the first available input device as default
    default_input_device_index = input_devices[0]['index']
    print(f"\nUsing microphone: {input_devices[0]['name']}")
    print("=" * 70 + "\n")
    
    # Create credential
    credential = AzureKeyCredential(api_key)
    
    # Create connection wrapper
    connection_wrapper = VoiceLiveConnectionWrapper(
        endpoint=endpoint,
        credential=credential,
        model=model
    )
    
    try:
        # Create and start assistant
        assistant = SupportAssistant(
            connection_wrapper=connection_wrapper,
            ticket_service=ticket_service,
            voice=voice,
            instructions=instructions,
            input_device_index=default_input_device_index
        )
        # Set recording directory
        assistant.recording_dir = recording_dir
        
        print("\n" + "=" * 70)
        print("HR/IT Support Desk Voice Agent")
        print("=" * 70)
        print("\nThe assistant can help you with:")
        print("  • Check ticket status by ticket ID")
        print("  • Create new HR or IT support tickets")
        print("\nThis is a MULTI-TURN conversation - you can speak multiple times!")
        print("   The conversation continues until you press Ctrl+C.")
        print("\nTry saying:")
        print("  'I need to check the status of ticket TKT-IT-00001'")
        print("  'I have an IT problem - my computer won't start'")
        print("  'I need to create an HR ticket for a leave request'")
        print("\nPress Ctrl+C to exit")
        print("=" * 70 + "\n")
        
        await assistant.start()
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    logger.info("Interrupt received, shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main function
    asyncio.run(main())
