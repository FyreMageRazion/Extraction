# HR/IT Support Desk Voice Agent

A voice-powered support desk assistant built with Azure VoiceLive SDK that helps employees check ticket status and create new support tickets via natural voice conversation.

## Features

- **Voice-based ticket status checking**: Ask about any ticket by ID
- **Voice-based ticket creation**: Report HR or IT issues and create tickets
- **Real-time voice conversation**: Natural, multi-turn conversations
- **SQLite database**: Lightweight, file-based ticket storage
- **Feedback prevention**: Built-in cooldown and echo cancellation to prevent feedback loops

## Architecture

The system follows a clean, modular architecture:

- **Database Layer**: SQLite for ticket storage
- **Service Layer**: Business logic for ticket operations
- **Audio Layer**: PyAudio for microphone input and speaker output
- **VoiceLive Layer**: Azure VoiceLive SDK integration
- **Function Tools**: VoiceLive function calling for ticket operations

## Setup

### Prerequisites

- Python 3.8+
- Azure VoiceLive API key and endpoint
- Microphone and speakers/headphones

### Installation

1. Clone the repository:
```bash
cd VoiceAI
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.template .env
# Edit .env with your Azure VoiceLive credentials
```

### Required Environment Variables

- `AZURE_VOICELIVE_API_KEY`: Your Azure VoiceLive API key (required)
- `AZURE_VOICELIVE_ENDPOINT`: Your Azure VoiceLive endpoint URL (required)
- `VOICELIVE_MODEL`: Model deployment name (default: `gpt-4o-realtime-preview`)
- `VOICELIVE_VOICE`: Azure voice name (default: `en-US-JennyNeural`)
- `DATABASE_PATH`: SQLite database path (default: `data/tickets.db`)

## Usage

Run the assistant:

```bash
python -m src.main
```

Or:

```bash
python src/main.py
```

The assistant will:
1. List available microphones
2. Connect to Azure VoiceLive
3. Start listening for your voice input

### Example Interactions

**Check ticket status:**
- "What's the status of ticket TKT-IT-00001?"
- "Check ticket TKT-HR-00005"

**Create a ticket:**
- "I have an IT problem - my computer won't start"
- "I need to create an HR ticket for a leave request"
- "My email is not working, this is urgent"

## Project Structure

```
VoiceAI/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── audio/
│   │   └── processor.py    # Audio capture/playback
│   ├── voicelive/
│   │   ├── connection.py   # VoiceLive connection wrapper
│   │   └── assistant.py    # Main assistant class
│   ├── database/
│   │   ├── models.py       # SQLite models
│   │   └── db.py           # Database operations
│   ├── services/
│   │   └── ticket_service.py  # Ticket business logic
│   └── tools/
│       └── function_tools.py   # VoiceLive function tools
├── data/
│   └── tickets.db          # SQLite database (created automatically)
├── legacy/                 # Previous implementation (for reference)
├── requirements.txt
├── .env.template
└── README.md
```

## Function Tools

The assistant uses two function tools:

1. **get_ticket_status(ticket_id)**: Checks the status and details of a ticket
2. **create_support_ticket(ticket_type, description, priority)**: Creates a new HR or IT ticket

## Database Schema

Tickets are stored in SQLite with the following schema:

- `id`: Primary key (auto-increment)
- `ticket_id`: Unique ticket identifier (e.g., TKT-IT-00001)
- `type`: Ticket type ("HR" or "IT")
- `description`: Issue description
- `priority`: Priority level ("low", "medium", "high", "urgent")
- `status`: Ticket status ("open", "in_progress", "resolved", "closed")
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Troubleshooting

### No microphone found
- Ensure your microphone is connected and enabled
- Check Windows sound settings
- Try specifying a device index in the code

### Audio feedback/echo
- Use headphones instead of speakers
- The system includes echo cancellation, but headphones are recommended
- There's a 3-second cooldown after responses to prevent false triggers

### Connection errors
- Verify your Azure VoiceLive API key and endpoint
- Check your internet connection
- Ensure the endpoint URL is correct (should be HTTPS, not WSS for the endpoint)

## License

MIT
