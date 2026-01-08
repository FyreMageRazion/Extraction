"""
Support Assistant - Main voice assistant class for HR/IT support desk.
Inspired by Azure samples orchestrator pattern.
"""

import asyncio
import base64
import json
import logging
import os
import queue
import threading
import time
import wave
from datetime import datetime
from typing import Optional

from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioNoiseReduction,
    AzureSemanticVad,
    AzureStandardVoice,
    FunctionCallOutputItem,
    InputAudioFormat,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
)

from ..audio.processor import AudioProcessor
from ..services.ticket_service import TicketService
from ..tools.function_tools import get_all_tools
from .connection import VoiceLiveConnectionWrapper

logger = logging.getLogger(__name__)


class SupportAssistant:
    """
    Main voice assistant for HR/IT support desk.
    
    Features:
    - Event-driven architecture
    - Function calling integration
    - Audio processing coordination
    - Response state management
    - Feedback loop prevention (cooldown, pause flags)
    """
    
    def __init__(
        self,
        connection_wrapper: VoiceLiveConnectionWrapper,
        ticket_service: TicketService,
        voice: str = "en-US-JennyNeural",
        instructions: Optional[str] = None,
        input_device_index: Optional[int] = None,
    ):
        """
        Initialize the support assistant.
        
        Args:
            connection_wrapper: VoiceLiveConnectionWrapper instance
            ticket_service: TicketService instance
            voice: Azure voice name
            instructions: Optional custom system instructions
            input_device_index: Optional microphone device index
        """
        self.connection_wrapper = connection_wrapper
        self.ticket_service = ticket_service
        self.voice = voice
        self.instructions = instructions or self._default_instructions()
        self.input_device_index = input_device_index
        
        self.connection = None
        self.audio_processor: Optional[AudioProcessor] = None
        self.session_ready = False
        
        # Response state tracking
        self._active_response = False
        self._response_api_done = False
        self._response_in_progress = False
        self._audio_received = False
        
        # Recording functionality
        self.recording_enabled = True
        self.recording_dir = "recordings"
        self.recording_file = None
        self.recording_wav = None
        self.user_audio_queue: queue.Queue[bytes] = queue.Queue()
        self.ai_audio_queue: queue.Queue[bytes] = queue.Queue()
        self.recording_thread: Optional[threading.Thread] = None
        self.session_id = None
        
        # Ensure recording directory exists
        os.makedirs(self.recording_dir, exist_ok=True)
    
    def _default_instructions(self) -> str:
        """Get default system instructions."""
        return """You are a helpful HR/IT support desk assistant. Your role is to help employees with their support tickets.

Key responsibilities:
- Help users check the status of their existing tickets by ticket ID
- Create new support tickets when users report problems or request help
- Be friendly, professional, and empathetic
- Ask clarifying questions if needed to understand the issue
- Always speak the complete ticket information when creating or checking tickets
- Keep responses concise and conversational (as if speaking on the phone)

When a user asks about a ticket:
- Use the get_ticket_status function with the ticket ID they provide
- Read back the complete ticket details including status, type, description, priority, and creation date

When a user reports a problem:
- Determine if it's an HR or IT issue
- Ask about priority if not specified (default to medium)
- Use the create_support_ticket function
- Confirm the ticket creation and provide the ticket ID

Be natural and conversational. Don't be overly formal."""
    
    async def start(self):
        """Start the assistant."""
        try:
            # Connect to VoiceLive using context manager
            async with self.connection_wrapper as wrapper:
                self.connection = wrapper.connection
                
                # Initialize audio processor with user audio queue for recording
                self.audio_processor = AudioProcessor(self.connection, self.input_device_index)
                self.audio_processor.user_audio_queue = self.user_audio_queue
                
                # Setup session
                await self._setup_session()
                
                # Start audio capture
                await self.audio_processor.start_capture()
                
                # Process events
                await self._process_events()
        
        except KeyboardInterrupt:
            logger.info("Assistant stopped by user")
        except Exception as e:
            logger.error(f"Error in assistant: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def _setup_session(self):
        """Configure the VoiceLive session with function calling support."""
        logger.info("Setting up support desk session...")
        
        # Create voice configuration
        voice_config = AzureStandardVoice(name=self.voice, type="azure-standard")
        
        # Create turn detection configuration using Azure Semantic VAD
        # Optimal production-ready configuration per Azure AI Foundry best practices:
        # - Semantic VAD provides ~20% relative improvement in accuracy
        # - 200-300ms prefix padding prevents clipping start of speech
        # - 400-600ms silence duration balances natural pauses with responsiveness
        # - 500ms is optimal for most conversational scenarios
        turn_detection_config = AzureSemanticVad(
            threshold=0.3,
            prefix_padding_ms=200,  # 200-300ms range (optimal: 200ms)
            silence_duration_ms=500  # 400-600ms range (optimal: 400-500ms)
        )
        logger.info(f"VAD configured: type=AzureSemanticVad (production-optimized), threshold=0.3, prefix_padding=200ms, silence_duration=500ms")
        
        # Get function tools
        tools = get_all_tools()
        
        # Create session configuration with production-optimized settings
        # Per Azure AI Foundry best practices:
        # - 24kHz PCM16 for high-quality audio (default and recommended)
        # - Azure Deep Noise Suppression for noisy environments
        # - Server echo cancellation to prevent feedback loops
        session_config = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=self.instructions,
            voice=voice_config,
            input_audio_format=InputAudioFormat.PCM16,  # 16-bit linear PCM (standard)
            output_audio_format=OutputAudioFormat.PCM16,  # 16-bit linear PCM (standard)
            turn_detection=turn_detection_config,  # Azure Semantic VAD (optimal for production)
            tools=tools,
            input_audio_echo_cancellation=AudioEchoCancellation(type="server_echo_cancellation"),  # Prevents AI hearing its own voice
            input_audio_noise_reduction=AudioNoiseReduction(type="azure_deep_noise_suppression"),  # Significantly improves accuracy in noisy environments
        )
        
        await self.connection.session.update(session=session_config)
        logger.info("Support desk session configured with ticket functions")
    
    async def _process_events(self):
        """Process events from the VoiceLive connection."""
        try:
            async for event in self.connection:
                await self._handle_event(event)
        except KeyboardInterrupt:
            logger.info("Event processing interrupted")
        except Exception as e:
            logger.error(f"Error processing events: {e}")
            raise
    
    async def _handle_event(self, event):
        """Handle different types of events from VoiceLive."""
        logger.debug(f"📥 Event received: {event.type}")
        
        ap = self.audio_processor
        conn = self.connection
        
        if event.type == ServerEventType.SESSION_UPDATED:
            logger.info(f"Session ready: {event.session.id}")
            self.session_ready = True
            self.session_id = event.session.id
            await ap.start_capture()
            # Start recording when session is ready
            self._start_recording()
        
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            # Check cooldown period
            if ap._response_cooldown_until and time.time() < ap._response_cooldown_until:
                remaining = ap._response_cooldown_until - time.time()
                logger.warning(f"Speech detected during cooldown period (IGNORING) - {remaining:.2f}s remaining")
                try:
                    await conn.response.cancel()
                except Exception:
                    pass
                return
            
            logger.info("User started speaking - skipping pending audio")
            print("Listening...")
            ap.skip_pending_audio()
            
            # Only cancel if response is active and not already done
            if self._active_response and not self._response_api_done:
                try:
                    await conn.response.cancel()
                    logger.debug("Cancelled in-progress response due to barge-in")
                except Exception as e:
                    if "no active response" in str(e).lower():
                        logger.debug("Cancel ignored - response already completed")
                    else:
                        logger.warning(f"Cancel failed: {e}")
        
        elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            logger.info("User stopped speaking")
            print("Processing...")
            await ap.start_playback()
        
        elif event.type == ServerEventType.RESPONSE_CREATED:
            logger.info("Assistant response created")
            self._active_response = True
            self._response_api_done = False
            ap._pause_capture_during_response = True
            self._audio_received = False
            
            # Clear input audio buffer to prevent feedback
            try:
                await conn.input_audio_buffer.clear()
                logger.info("Input audio buffer cleared to prevent feedback")
            except Exception as e:
                logger.debug(f"Could not clear input buffer: {e}")
        
        elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
            # event.delta from VoiceLive is base64-encoded string
            delta_type = type(event.delta).__name__
            delta_length = len(event.delta) if event.delta else 0
            logger.info(f"Received audio delta (type: {delta_type}, length: {delta_length})")
            
            if not ap.is_playing:
                logger.info("Starting audio playback...")
                await ap.start_playback()
            
            if event.delta:
                await ap.queue_audio(event.delta)
                logger.debug(f"Queued audio chunk for playback")
            else:
                logger.warning("RESPONSE_AUDIO_DELTA event has no delta data!")
            
            self._audio_received = True
            if not self._response_in_progress:
                self._response_in_progress = True
            
            # Queue AI audio for recording
            # event.delta is already bytes from VoiceLive, not base64
            if self.recording_enabled and event.delta:
                try:
                    if isinstance(event.delta, bytes):
                        # Already bytes - use directly
                        ai_audio = event.delta
                    elif isinstance(event.delta, str):
                        # String - decode as base64
                        audio_str = event.delta.strip()
                        missing_padding = len(audio_str) % 4
                        if missing_padding:
                            audio_str += '=' * (4 - missing_padding)
                        ai_audio = base64.b64decode(audio_str, validate=False)
                    else:
                        logger.warning(f"Unexpected delta type for recording: {type(event.delta)}")
                        return
                    
                    self.ai_audio_queue.put(ai_audio)
                except Exception as e:
                    logger.debug(f"Error queuing AI audio for recording: {e}")
        
        elif event.type == ServerEventType.RESPONSE_AUDIO_DONE:
            logger.info("Assistant finished speaking")
            print("Ready for next input...")
            ap._response_audio_done_time = time.time()
        
        elif event.type == ServerEventType.RESPONSE_DONE:
            logger.info("Response complete")
            self._active_response = False
            self._response_api_done = True
            
            # Add delay and clear audio queue
            if ap._response_audio_done_time:
                elapsed = time.time() - ap._response_audio_done_time
                if elapsed < 0.5:
                    await asyncio.sleep(0.5 - elapsed)
            
            # Clear any audio queued during response
            try:
                while not ap.audio_send_queue.empty():
                    try:
                        ap.audio_send_queue.get_nowait()
                    except queue.Empty:
                        break
                logger.info("Cleared audio queue before resuming capture")
            except Exception as e:
                logger.debug(f"Could not clear audio queue: {e}")
            
            ap._pause_capture_during_response = False
            ap._response_audio_done_time = None
            
            # Set cooldown period - don't accept speech for 3 seconds after response
            ap._response_cooldown_until = time.time() + 3.0
            logger.info("Response complete - 3s cooldown started")
            
            # Clear response state
            if self._audio_received:
                self._response_in_progress = False
                self._audio_received = False
        
        elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
            await self._execute_function_call(event)
        
        elif event.type == ServerEventType.ERROR:
            logger.error(f"VoiceLive error: {event.error.message}")
            print(f"Error: {event.error.message}")
        
        else:
            logger.debug(f"Unhandled event type: {event.type}")
    
    async def _execute_function_call(self, event):
        """Execute function call and return result to VoiceLive."""
        try:
            function_name = getattr(event, 'name', None)
            function_arguments = getattr(event, 'arguments', '{}')
            call_id = getattr(event, 'call_id', None)
            
            logger.info(f"Function call: {function_name} with args: {function_arguments}")
            print(f"Executing: {function_name}")
            
            # Parse arguments
            if isinstance(function_arguments, str):
                args = json.loads(function_arguments)
            else:
                args = function_arguments
            
            # Execute function
            if function_name == "get_ticket_status":
                ticket_id = args.get("ticket_id", "")
                result = self.ticket_service.check_ticket_status(ticket_id)
                function_output = result.get("message", "Ticket not found")
            
            elif function_name == "create_support_ticket":
                ticket_type = args.get("ticket_type", "")
                description = args.get("description", "")
                priority = args.get("priority", "medium")
                result = self.ticket_service.create_ticket(ticket_type, description, priority)
                function_output = result.get("message", "Failed to create ticket")
            
            else:
                function_output = f"Unknown function: {function_name}"
                logger.warning(f"Unknown function called: {function_name}")
            
            logger.info(f"Function result: {function_output}")
            
            # Send function output back to VoiceLive
            if call_id:
                try:
                    output_item = FunctionCallOutputItem(
                        call_id=call_id,
                        output=function_output
                    )
                    
                    await self.connection.conversation.item.create(item=output_item)
                    logger.info(f"Function output sent (call_id: {call_id})")
                    
                    # Trigger response creation
                    if not self._response_in_progress:
                        await self.connection.response.create()
                        self._response_in_progress = True
                        logger.info("Response triggered - VoiceLive will now speak the result")
                    else:
                        logger.warning("Skipping response.create() - response already in progress")
                
                except Exception as e:
                    logger.error(f"Error sending function output: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.warning("No call_id found - function output may not be sent correctly")
        
        except Exception as e:
            logger.error(f"Error executing function: {e}")
            import traceback
            traceback.print_exc()
    
    def _start_recording(self):
        """Start recording conversation to WAV file."""
        if not self.recording_enabled or self.recording_wav:
            return
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = (self.session_id or "session")[:8]
            filename = f"conversation_{timestamp}_{session_id}.wav"
            self.recording_file = os.path.join(self.recording_dir, filename)
            
            # Open WAV file for writing (24kHz, mono, 16-bit PCM)
            self.recording_wav = wave.open(self.recording_file, "wb")
            self.recording_wav.setnchannels(1)  # Mono
            self.recording_wav.setsampwidth(2)  # 16-bit
            self.recording_wav.setframerate(24000)  # 24kHz
            
            logger.info(f"Started recording: {self.recording_file}")
            
            # Start recording thread to mix audio streams
            self.recording_thread = threading.Thread(target=self._recording_thread, daemon=True)
            self.recording_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording_enabled = False
    
    def _recording_thread(self):
        """Thread that mixes and writes user and AI audio to WAV file."""
        import struct
        
        while self.recording_wav and self.recording_enabled:
            try:
                # Try to get audio from both queues (with timeout)
                user_audio = None
                ai_audio = None
                
                # Get user audio
                try:
                    user_audio = self.user_audio_queue.get(timeout=0.05)
                except queue.Empty:
                    pass
                
                # Get AI audio
                try:
                    ai_audio = self.ai_audio_queue.get(timeout=0.05)
                except queue.Empty:
                    pass
                
                # Mix audio if we have both, otherwise write whichever we have
                if user_audio and ai_audio:
                    # Ensure both audio chunks are valid and have even length (16-bit samples)
                    user_len = len(user_audio)
                    ai_len = len(ai_audio)
                    
                    # Skip if either chunk is invalid or odd length
                    if user_len < 2 or ai_len < 2 or user_len % 2 != 0 or ai_len % 2 != 0:
                        # Write whichever is valid
                        if user_len >= 2 and user_len % 2 == 0:
                            if self.recording_wav:
                                self.recording_wav.writeframes(user_audio)
                        if ai_len >= 2 and ai_len % 2 == 0:
                            if self.recording_wav:
                                self.recording_wav.writeframes(ai_audio)
                    else:
                        # Mix user and AI audio (simple addition with normalization)
                        # Convert bytes to samples
                        user_samples = struct.unpack(f'<{user_len//2}h', user_audio)
                        ai_samples = struct.unpack(f'<{ai_len//2}h', ai_audio)
                        
                        # Mix samples (take the shorter length to avoid index errors)
                        min_len = min(len(user_samples), len(ai_samples))
                        mixed_samples = []
                        for i in range(min_len):
                            # Mix with slight attenuation to prevent clipping
                            mixed = int((user_samples[i] + ai_samples[i]) * 0.5)
                            # Clamp to 16-bit range
                            mixed = max(-32768, min(32767, mixed))
                            mixed_samples.append(mixed)
                        
                        # Convert back to bytes
                        mixed_audio = struct.pack(f'<{len(mixed_samples)}h', *mixed_samples)
                        if self.recording_wav:
                            self.recording_wav.writeframes(mixed_audio)
                        
                        # Write any remaining samples from the longer chunk
                        if len(user_samples) > min_len:
                            remaining = struct.pack(f'<{len(user_samples) - min_len}h', *user_samples[min_len:])
                            if self.recording_wav:
                                self.recording_wav.writeframes(remaining)
                        elif len(ai_samples) > min_len:
                            remaining = struct.pack(f'<{len(ai_samples) - min_len}h', *ai_samples[min_len:])
                            if self.recording_wav:
                                self.recording_wav.writeframes(remaining)
                
                elif user_audio:
                    # Only user audio - validate length
                    if len(user_audio) >= 2 and len(user_audio) % 2 == 0:
                        if self.recording_wav:
                            self.recording_wav.writeframes(user_audio)
                
                elif ai_audio:
                    # Only AI audio - validate length
                    if len(ai_audio) >= 2 and len(ai_audio) % 2 == 0:
                        if self.recording_wav:
                            self.recording_wav.writeframes(ai_audio)
                
                # Check if we should continue
                if not self.recording_enabled:
                    break
                    
            except Exception as e:
                if self.recording_wav:
                    logger.error(f"Error in recording thread: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                break
    
    def _stop_recording(self):
        """Stop recording and close WAV file."""
        if not self.recording_wav:
            return
        
        try:
            # Signal recording thread to stop
            self.recording_enabled = False
            
            # Wait for recording thread
            if self.recording_thread:
                self.recording_thread.join(timeout=2.0)
            
            # Close WAV file
            self.recording_wav.close()
            self.recording_wav = None
            
            logger.info(f"Recording saved to: {self.recording_file}")
            print(f"Conversation recorded: {self.recording_file}")
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        # Stop recording
        self._stop_recording()
        
        if self.audio_processor:
            await self.audio_processor.cleanup()
        # Connection is closed automatically by context manager
        logger.info("Support assistant cleaned up")
