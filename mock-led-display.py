#!/usr/bin/env python3
"""
LED Name Badge Mock Console Display
"""

import re
import queue
import time
import sys
import threading
from lednamebadge import SimpleTextAndIcons
from openai import OpenAI
import base64

# Global creator to reuse SimpleTextAndIcons for bitmap generation
creator = SimpleTextAndIcons()

# ============================================
# LED Display Configuration
# ============================================

# LED Matrix dimensions (11 rows x 44 columns - typical LED badge size)
LED_ROWS = 11
LED_COLS = 44

# LED pixel size and spacing
LED_SIZE = 8
LED_SPACING = 2

# Colors for different LED states and modes
LED_COLORS = {
    'red': {'on': '#FF0000', 'dim': '#660000', 'off': '#1A0000'},
}

ANIMATION_DELAY_MS = 75

# Helper that converts `creator.bitmap()` output into per-row pixel bitmaps
class TextRenderer:
    @staticmethod
    def render_text(text):
        """Return a list of `LED_ROWS` rows, each a list of pixel bits (0/1)."""
        try:
            buf, cols = creator.bitmap(text)
        except Exception:
            return []

        if cols == 0:
            return [[0] * 0 for _ in range(LED_ROWS)]

        width = cols * 8
        rows = [[0] * width for _ in range(LED_ROWS)]

        # buf is organized as: for each column: 11 bytes (one per row)
        for c in range(cols):
            base = c * LED_ROWS
            for r in range(LED_ROWS):
                byte_val = buf[base + r]
                for bit in range(8):
                    if byte_val & (1 << (7 - bit)):
                        x = c * 8 + bit
                        rows[r][x] = 1

        return rows


# Simple holder for display state used by the console renderer
class DisplayState:
    def __init__(self):
        self.text = ""
        self.text_bitmap = []
        self.text_width = 0
        self.mode = 'left'
        self.speed = 4
        self.brightness = 100
        self.color = 'red'
        self.scroll_position = 0
        self.is_running = False
        self.x_api_key = None
        self.custom_prompt = None

    def clear(self):
        self.text = ""
        self.text_bitmap = []
        self.text_width = 0
        self.scroll_position = 0
        self.is_running = False
        self.x_api_key = None
        self.custom_prompt = None


# ============================================
# LED Display Console Renderer
# ============================================
class ConsoleDisplay:
    """Console-based LED display renderer. Renders the 11x44 matrix to the
    terminal using ANSI colors and simple characters.
    """

    ON_CHAR = '\u25CF'  # ●
    OFF_CHAR = '\u25CB'  # ○

    def __init__(self, display_state, command_queue, refresh_ms=ANIMATION_DELAY_MS):
        self.display_state = display_state
        self.command_queue = command_queue
        self.refresh = refresh_ms / 1000.0
        self._stop = threading.Event()

    def _clear_screen(self):
        # Clear screen and move cursor home.
        sys.stdout.write('\033[2J\033[H')

    def _render(self):
        """Render the current display_state to the terminal."""
        # Header
        self._clear_screen()
        print('LED Name Badge (mock) — console renderer')
        display_text = (self.display_state.text[:60] + '...') if len(self.display_state.text) > 60 else self.display_state.text
        print(f'Text: {display_text or "(none)"}\n')

        # Colors: use a black background only for LED cells and RGB
        # foreground colors for ON (bright red) and OFF (dim red).
        BG_BLACK = '\033[48;2;0;0;0m'
        ON = BG_BLACK + '\033[38;2;255;0;0m'   # red on black
        OFF = BG_BLACK + '\033[38;2;102;0;0m'  # dim red on black
        RESET = '\033[0m'

        text_bitmap = self.display_state.text_bitmap
        scroll_pos = self.display_state.scroll_position
        mode = self.display_state.mode

        for row in range(LED_ROWS):
            line = []
            for col in range(LED_COLS):
                if not text_bitmap:
                    pixel_on = False
                else:
                    if mode == 'static':
                        text_col = col - (LED_COLS - self.display_state.text_width) // 2
                    else:
                        text_col = col + scroll_pos - LED_COLS

                    if 0 <= row < len(text_bitmap) and 0 <= text_col < len(text_bitmap[row]):
                        pixel_on = text_bitmap[row][text_col] == 1
                    else:
                        pixel_on = False

                if pixel_on:
                    line.append(f'{ON}{self.ON_CHAR}')
                else:
                    line.append(f'{OFF}{self.OFF_CHAR}')
            print(''.join(line))
        # Reset colors (restores user's terminal background)
        print(RESET + '\n')

    def _process_commands(self):
        changed = False
        try:
            while True:
                command = self.command_queue.get_nowait()
                if command['type'] == 'update':
                    data = command['data']
                    if 'text' in data:
                        self.display_state.text = data['text']
                        self.display_state.text_bitmap = TextRenderer.render_text(data['text'])
                        self.display_state.text_width = len(self.display_state.text_bitmap[0]) if self.display_state.text_bitmap else 0
                        self.display_state.scroll_position = 0
                        self.display_state.is_running = True
                        self.display_state.mode = 'left'
                        self.display_state.speed = 4
                        self.display_state.brightness = 100
                        self.display_state.color = 'red'
                        changed = True
                    if 'x-api-key' in data:
                        self.display_state.x_api_key = data['x-api-key']
                        print(f"[API Key Received in Mock] {self.display_state.x_api_key.replace(self.display_state.x_api_key[10:-10], '**********')}")
                    if 'x-openai-prompt' in data:
                        self.display_state.custom_prompt = data['x-openai-prompt']
                        print(f"[Custom OpenAI Prompt Set: {self.display_state.custom_prompt[:50]}...]")
                    # If response_queue is provided, generate image in background thread
                    if 'response_queue' in data:
                        response_queue = data['response_queue']
                        # Run image generation in a separate thread so terminal rendering isn't blocked
                        thread = threading.Thread(target=self._generate_and_send_mock_image, args=(response_queue,), daemon=True)
                        thread.start()
                elif command['type'] == 'clear':
                    self.display_state.clear()
                    changed = True
        except queue.Empty:
            pass
        return changed
    
    def _generate_and_send_mock_image(self, response_queue):
        """Generate image in background and send to response queue."""
        mock_image = self._generate_mock_image()
        response_queue.put({'mock_image': mock_image})
    
    def _generate_mock_image(self):
        """Generate an image using OpenAI based on the display text."""
        if not self.display_state.text or not self.display_state.x_api_key:
            return ""
        
        try:
            # Initialize OpenAI client with the provided API key
            client = OpenAI(api_key=self.display_state.x_api_key)
            
            # Use custom prompt if provided, otherwise use default
            if self.display_state.custom_prompt:
                prompt = self.display_state.custom_prompt.replace('{text}', self.display_state.text)
            else:
                # Default prompt
                prompt = f"""
Create an image of the berlin tv tower with an LED display showing the following text:
{self.display_state.text}
"""
            
            # Generate image using OpenAI
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt
            )
            
            # Return base64 encoded image
            image_base64 = result.data[0].b64_json
            return image_base64
            
        except Exception as e:
            print(f"Error generating image with OpenAI: {e}")
            return f"error: {str(e)}"

    def run(self):
        try:
            while not self._stop.is_set():
                # process commands
                changed = self._process_commands()

                # advance scroll if running
                if self.display_state.is_running and self.display_state.text:
                    self.display_state.scroll_position += 1
                    if self.display_state.scroll_position > self.display_state.text_width + LED_COLS:
                        self.display_state.scroll_position = 0
                    changed = True

                if changed:
                    self._render()

                time.sleep(self.refresh)
        except KeyboardInterrupt:
            pass

    def stop(self):
        self._stop.set()


def run_mock(display_state=None, command_queue=None):
    """Run the console-based mock. This blocks until stopped.

    If `display_state` or `command_queue` are omitted, new ones are created.
    """
    if display_state is None:
        display_state = DisplayState()
    if command_queue is None:
        command_queue = queue.Queue()

    console = ConsoleDisplay(display_state, command_queue)
    try:
        console.run()
    except KeyboardInterrupt:
        console.stop()
