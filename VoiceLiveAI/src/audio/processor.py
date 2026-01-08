"""
Audio processor for microphone input and speaker output using PyAudio.
Based on Azure samples pattern but simplified.
"""

import asyncio
import base64
import logging
import queue
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

try:
    import pyaudio
except ImportError:
    raise ImportError("pyaudio is required. Install with: pip install pyaudio")

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Handles real-time audio capture and playback for the voice assistant.
    
    Threading Architecture:
    - Main thread: Event loop and UI
    - Capture thread: PyAudio input stream reading
    - Send thread: Async audio data transmission to VoiceLive
    - Playback thread: PyAudio output stream writing
    """
    
    def __init__(self, connection, input_device_index: Optional[int] = None):
        """
        Initialize the audio processor.
        
        Args:
            connection: VoiceLive connection object
            input_device_index: Optional microphone device index
        """
        self.connection = connection
        self.audio = pyaudio.PyAudio()
        
        # Audio configuration - PCM16, 24kHz, mono as specified
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 24000
        self.chunk_size = 1024
        
        # Noise gate settings - filter out quiet audio to reduce false positives
        # Typical speech RMS: 1000-5000, background noise: 50-300
        self.noise_gate_threshold = 200  # Filter background noise while preserving clear speech
        
        # Capture and playback state
        self.is_capturing = False
        self.is_playing = False
        self.input_stream = None
        self.output_stream = None
        self.input_device_index = input_device_index
        
        # Flag to pause audio capture during response playback (prevents feedback loop)
        self._pause_capture_during_response = False
        # Track when response audio finished (for delayed resume)
        self._response_audio_done_time = None
        # Cooldown period after response - don't accept speech for N seconds to prevent feedback
        self._response_cooldown_until = None  # Timestamp when cooldown expires
        
        # Audio queues and threading
        self.audio_queue: queue.Queue[bytes] = queue.Queue()
        self.audio_send_queue: queue.Queue[str] = queue.Queue()  # base64 audio to send
        self.user_audio_queue: Optional[queue.Queue[bytes]] = None  # Optional queue for recording user audio
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.capture_thread: Optional[threading.Thread] = None
        self.playback_thread: Optional[threading.Thread] = None
        self.send_thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None  # Store the event loop
        
        # Detect and log input device
        self._detect_input_device()
        
        logger.info("AudioProcessor initialized with 24kHz PCM16 mono audio")
    
    @staticmethod
    def list_input_devices():
        """List all available input devices (microphones)."""
        audio = pyaudio.PyAudio()
        devices = []
        try:
            for i in range(audio.get_device_count()):
                try:
                    device_info = audio.get_device_info_by_index(i)
                    if device_info.get('maxInputChannels', 0) > 0:
                        devices.append({
                            'index': i,
                            'name': device_info.get('name', 'Unknown'),
                            'channels': device_info.get('maxInputChannels', 0),
                            'default': device_info.get('index') == audio.get_default_input_device_info()['index']
                        })
                except Exception:
                    continue
        finally:
            audio.terminate()
        return devices
    
    def _detect_input_device(self):
        """Detect and verify the input device (microphone) to use."""
        try:
            # Get default input device if not specified
            if self.input_device_index is None:
                try:
                    default_input = self.audio.get_default_input_device_info()
                    self.input_device_index = default_input['index']
                    logger.info(f"Using default input device: {default_input['name']} (index {self.input_device_index})")
                except Exception as e:
                    logger.warning(f"Could not get default input device: {e}")
                    # Fallback: find first available input device
                    for i in range(self.audio.get_device_count()):
                        try:
                            device_info = self.audio.get_device_info_by_index(i)
                            if device_info.get('maxInputChannels', 0) > 0:
                                self.input_device_index = i
                                logger.info(f"Using input device: {device_info['name']} (index {self.input_device_index})")
                                break
                        except Exception:
                            continue
            
            # Verify the selected device has input channels
            if self.input_device_index is not None:
                try:
                    device_info = self.audio.get_device_info_by_index(self.input_device_index)
                    max_input_channels = device_info.get('maxInputChannels', 0)
                    if max_input_channels == 0:
                        logger.error(f"Selected device '{device_info['name']}' has no input channels!")
                        raise ValueError(f"Device {self.input_device_index} is not an input device")
                    logger.info(f"Verified microphone input: {device_info['name']} (index {self.input_device_index}, {max_input_channels} channels)")
                    print(f"Using microphone: {device_info['name']}")
                except Exception as e:
                    logger.warning(f"Could not verify device channels: {e}")
            else:
                raise ValueError("No input device found")
        except Exception as e:
            logger.error(f"Error detecting input device: {e}")
            raise
    
    async def start_capture(self):
        """Start audio capture from microphone."""
        if self.is_capturing:
            return
        
        try:
            self.loop = asyncio.get_event_loop()
            self.is_capturing = True
            
            # Open input stream
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk_size,
            )
            
            self.input_stream.start_stream()
            
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._capture_audio_thread)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            # Start audio send thread
            self.send_thread = threading.Thread(target=self._send_audio_thread)
            self.send_thread.daemon = True
            self.send_thread.start()
            
            logger.info("Started audio capture")
        
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self.is_capturing = False
            raise
    
    def _capture_audio_thread(self):
        """Audio capture thread - runs in background."""
        while self.is_capturing and self.input_stream:
            try:
                # Read audio data
                audio_data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                if audio_data and self.is_capturing:
                    # CRITICAL: Skip audio capture during response playback to prevent feedback loop
                    if self._pause_capture_during_response:
                        continue  # Don't send audio while assistant is speaking
                    
                    # CRITICAL: Check cooldown period after response completes
                    if self._response_cooldown_until and time.time() < self._response_cooldown_until:
                        # Still in cooldown - don't send audio
                        continue
                    
                    # Apply noise gate if enabled (threshold > 0)
                    if self.noise_gate_threshold > 0:
                        # Calculate RMS (Root Mean Square) level of audio chunk
                        try:
                            # Convert bytes to 16-bit signed integers
                            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
                            # Calculate RMS
                            rms = int((sum(s*s for s in samples) / len(samples)) ** 0.5)
                            
                            # Only send audio if it's above noise gate threshold
                            if rms >= self.noise_gate_threshold:
                                # Convert to base64 and queue for sending
                                audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                                self.audio_send_queue.put(audio_base64)
                            # else: audio is too quiet, filter it out (noise gate)
                        except Exception as gate_error:
                            # If noise gate fails, send audio anyway (fail-safe)
                            logger.debug(f"Noise gate error: {gate_error}, sending audio anyway")
                            audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                            self.audio_send_queue.put(audio_base64)
                    else:
                        # Noise gate disabled - send all audio
                        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                        self.audio_send_queue.put(audio_base64)
                    
                    # Queue user audio for recording if recording is enabled
                    if self.user_audio_queue is not None:
                        try:
                            self.user_audio_queue.put(audio_data)
                        except Exception:
                            pass  # Fail silently if recording queue is full
            
            except Exception as e:
                if self.is_capturing:
                    logger.error(f"Error in audio capture: {e}")
                break
    
    def _send_audio_thread(self):
        """Audio send thread - handles async operations from sync thread."""
        while self.is_capturing:
            try:
                # Get audio data from queue (blocking with timeout)
                audio_base64 = self.audio_send_queue.get(timeout=0.1)
                
                if audio_base64 and self.is_capturing and self.loop:
                    # CRITICAL: Double-check pause flag before sending (safety measure)
                    if self._pause_capture_during_response:
                        continue  # Don't send audio while assistant is speaking
                    
                    # Schedule the async send operation in the main event loop
                    future = asyncio.run_coroutine_threadsafe(
                        self.connection.input_audio_buffer.append(audio=audio_base64), self.loop
                    )
                    # Don't wait for completion to avoid blocking
            
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_capturing:
                    logger.error(f"Error sending audio: {e}")
                break
    
    async def start_playback(self):
        """Start audio playback to speakers."""
        if self.is_playing:
            return
        
        try:
            self.is_playing = True
            
            # Open output stream
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk_size,
            )
            
            self.output_stream.start_stream()
            
            # Start playback thread
            self.playback_thread = threading.Thread(target=self._playback_audio_thread)
            self.playback_thread.daemon = True
            self.playback_thread.start()
            
            # Get default output device info for logging
            try:
                default_output = self.audio.get_default_output_device_info()
                logger.info(f"Started audio playback on device: {default_output['name']} (rate={self.rate}Hz, channels={self.channels})")
            except Exception:
                logger.info(f"Started audio playback (rate={self.rate}Hz, channels={self.channels})")
        
        except Exception as e:
            logger.error(f"Failed to start audio playback: {e}")
            self.is_playing = False
            raise
    
    def _playback_audio_thread(self):
        """Audio playback thread - runs in background."""
        chunks_played = 0
        empty_count = 0
        while self.is_playing and self.output_stream:
            try:
                # Get audio data from queue (blocking with timeout)
                audio_data = self.audio_queue.get(timeout=0.1)
                empty_count = 0  # Reset empty count when we get data
                
                if audio_data and self.is_playing and self.output_stream:
                    try:
                        self.output_stream.write(audio_data)
                        chunks_played += 1
                        if chunks_played == 1:
                            logger.info(f"First audio chunk played successfully ({len(audio_data)} bytes)")
                        elif chunks_played % 50 == 0:  # Log every 50 chunks to avoid spam
                            logger.debug(f"Played {chunks_played} audio chunks")
                    except Exception as write_error:
                        logger.error(f"Error writing to output stream: {write_error}")
                        import traceback
                        logger.debug(traceback.format_exc())
                        break
            
            except queue.Empty:
                empty_count += 1
                if empty_count == 100:  # Log if queue is empty for 10 seconds
                    logger.warning(f"Audio queue empty for {empty_count * 0.1:.1f} seconds - no audio data received")
                    empty_count = 0  # Reset to avoid spam
                continue
            except Exception as e:
                if self.is_playing:
                    logger.error(f"Error in audio playback: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                break
        
        logger.info(f"Playback thread ended. Total chunks played: {chunks_played}")
    
    async def queue_audio(self, audio_data):
        """
        Queue audio data for playback.
        
        Args:
            audio_data: PCM16 audio data (bytes or base64 string)
        """
        try:
            if not audio_data:
                logger.warning("Attempted to queue empty audio data")
                return
            
            # event.delta from VoiceLive is already bytes, not base64!
            # Check if it's bytes or string
            if isinstance(audio_data, bytes):
                # Already bytes - use directly (this is what VoiceLive provides)
                decoded_audio = audio_data
            elif isinstance(audio_data, str):
                # It's a string - try to decode as base64
                try:
                    # Strip all whitespace (including newlines, tabs, etc.)
                    audio_str = ''.join(audio_data.split())
                    
                    # Remove any non-base64 characters (just in case)
                    import re
                    audio_str = re.sub(r'[^A-Za-z0-9+/=]', '', audio_str)
                    
                    # Add padding if needed (base64 strings must be multiple of 4)
                    missing_padding = len(audio_str) % 4
                    if missing_padding:
                        audio_str += '=' * (4 - missing_padding)
                    
                    # Try lenient decode first (no validation)
                    decoded_audio = base64.b64decode(audio_str, validate=False)
                    
                    if len(decoded_audio) == 0:
                        logger.warning("Base64 decode resulted in empty data")
                        return
                        
                except Exception as decode_error:
                    logger.error(f"Failed to decode base64 audio: {decode_error}")
                    logger.debug(f"Audio string sample (first 100 chars): {audio_data[:100] if len(audio_data) > 100 else audio_data}")
                    return
            else:
                logger.error(f"Unexpected audio data type: {type(audio_data)}")
                return
            
            if not decoded_audio:
                logger.warning("Decoded audio data is empty")
                return
            
            self.audio_queue.put(decoded_audio)
            logger.debug(f"Queued {len(decoded_audio)} bytes for playback (queue size: {self.audio_queue.qsize()})")
        except Exception as e:
            logger.error(f"Error queuing audio: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def skip_pending_audio(self):
        """Clear pending audio in queue without stopping playback system."""
        try:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
        except Exception:
            pass
    
    async def stop_playback(self):
        """Stop audio playback."""
        if not self.is_playing:
            return
        
        self.is_playing = False
        
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception:
                pass
            self.output_stream = None
        
        logger.info("Stopped audio playback")
    
    async def cleanup(self):
        """Clean up audio resources."""
        self.is_capturing = False
        self.is_playing = False
        
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception:
                pass
        
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception:
                pass
        
        self.audio.terminate()
        logger.info("Audio processor cleaned up")
