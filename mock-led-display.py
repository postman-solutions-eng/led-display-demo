#!/usr/bin/env python3
"""
LED Name Badge Mock Server with GUI Display

A Python application that simulates an LED name badge display with a visual GUI
and provides a Flask HTTP server that accepts the same API endpoints as the
LED Name Badge API collection.

API Endpoints:
- POST /display-text - Update badge display text
- GET /predefined-icons - Retrieve available icon library
- POST /display-summary - Display the demo summary text

Author: Generated for LED Name Badge API testing
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import queue
import math
from lednamebadge import SimpleTextAndIcons

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


# Simple holder for display state shared between Flask and GUI
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

    def clear(self):
        self.text = ""
        self.text_bitmap = []
        self.text_width = 0
        self.scroll_position = 0
        self.is_running = False


# ============================================
# LED Display GUI
# ============================================

class LEDDisplayGUI:
    """Tkinter GUI for LED display visualization"""
    
    def __init__(self, root, display_state, command_queue):
        self.root = root
        self.display_state = display_state
        self.command_queue = command_queue
        
        self.root.title("LED Name Badge Simulator")
        self.root.configure(bg='#1a1a1a')
        self.root.resizable(True, True)
        
        # Create main frame
        self.main_frame = tk.Frame(root, bg='#1a1a1a')
        self.main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            self.main_frame, 
            text="LED Name Badge Simulator",
            font=('Helvetica', 16, 'bold'),
            fg='#ffffff',
            bg='#1a1a1a'
        )
        title_label.pack(pady=(0, 10))
        
        # LED Display Frame (badge-like appearance)
        self.display_frame = tk.Frame(
            self.main_frame,
            bg='#0a0a0a',
            relief=tk.RAISED,
            bd=3
        )
        self.display_frame.pack(pady=10)
        
        # Inner bezel
        self.bezel_frame = tk.Frame(
            self.display_frame,
            bg='#333333',
            padx=8,
            pady=8
        )
        self.bezel_frame.pack(padx=4, pady=4)
        
        # Canvas for LED matrix
        canvas_width = LED_COLS * (LED_SIZE + LED_SPACING) + LED_SPACING
        canvas_height = LED_ROWS * (LED_SIZE + LED_SPACING) + LED_SPACING
        
        self.canvas = tk.Canvas(
            self.bezel_frame,
            width=canvas_width,
            height=canvas_height,
            bg='#0a0a0a',
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Create LED pixels
        self.leds = []
        for row in range(LED_ROWS):
            led_row = []
            for col in range(LED_COLS):
                x = LED_SPACING + col * (LED_SIZE + LED_SPACING)
                y = LED_SPACING + row * (LED_SIZE + LED_SPACING)
                led = self.canvas.create_oval(
                    x, y, x + LED_SIZE, y + LED_SIZE,
                    fill=LED_COLORS['red']['off'],
                    outline=''
                )
                led_row.append(led)
            self.leds.append(led_row)
        
        # Status Frame
        self.status_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        self.status_frame.pack(pady=10, fill=tk.X)
        
        # Status label (only show current text; api.py only updates text)
        self.status_text = tk.StringVar(value="Text: (none)")
        status_label = tk.Label(
            self.status_frame,
            textvariable=self.status_text,
            font=('Courier', 10),
            fg='#00ff00',
            bg='#1a1a1a'
        )
        status_label.pack(anchor=tk.W)
        
        # Control Frame
        self.control_frame = tk.Frame(self.main_frame, bg='#1a1a1a')
        self.control_frame.pack(pady=10, fill=tk.X)
        
        # Server status
        self.server_status = tk.StringVar(value="Server: Starting...")
        server_label = tk.Label(
            self.control_frame,
            textvariable=self.server_status,
            font=('Courier', 10),
            fg='#ffaa00',
            bg='#1a1a1a'
        )
        server_label.pack(side=tk.RIGHT, padx=10)

        # No color selector: api.py does not support color changes (fixed red)
        
        # Start animation loop
        self.animation_running = True
        self._animate()
        
        # Process command queue
        self._process_commands()
    
    def _animate(self):
        """Animation loop for scrolling text"""
        if not self.animation_running:
            return
        
        if self.display_state.is_running and self.display_state.text:
            # Simplified: always scroll left (API enforces left mode)
            self.display_state.scroll_position += 1
            if self.display_state.scroll_position > self.display_state.text_width + LED_COLS:
                self.display_state.scroll_position = 0
            self._update_display()
        
        # Schedule next animation frame (fixed delay to match speed 4)
        self.root.after(ANIMATION_DELAY_MS, self._animate)
    
    def _update_display(self):
        """Update the LED display based on current state"""
        color = self.display_state.color
        brightness = self.display_state.brightness / 100.0
        
        # Get color values
        colors = LED_COLORS.get(color, LED_COLORS['red'])
        on_color = colors['on']
        dim_color = colors['dim']
        off_color = colors['off']
        
        # Adjust for brightness
        if brightness < 0.5:
            on_color = dim_color
        
        # Clear or render based on state
        if not self.display_state.text:
            # All LEDs off
            for row in range(LED_ROWS):
                for col in range(LED_COLS):
                    self.canvas.itemconfig(self.leds[row][col], fill=off_color)
        else:
            # Render text bitmap (support only 'static' centered and left-scrolling)
            text_bitmap = self.display_state.text_bitmap
            scroll_pos = self.display_state.scroll_position
            mode = self.display_state.mode

            for row in range(LED_ROWS):
                for col in range(LED_COLS):
                    pixel_on = False

                    if mode == 'static':
                        # Center text
                        text_col = col - (LED_COLS - self.display_state.text_width) // 2
                        if row < len(text_bitmap) and 0 <= text_col < len(text_bitmap[row]):
                            pixel_on = text_bitmap[row][text_col] == 1
                    else:
                        # Default: left scroll
                        text_col = col + scroll_pos - LED_COLS
                        if row < len(text_bitmap) and 0 <= text_col < len(text_bitmap[row]):
                            pixel_on = text_bitmap[row][text_col] == 1

                    fill_color = on_color if pixel_on else off_color
                    self.canvas.itemconfig(self.leds[row][col], fill=fill_color)
        
        # Update status labels
        display_text = self.display_state.text[:30] + "..." if len(self.display_state.text) > 30 else self.display_state.text
        self.status_text.set(f"Text: {display_text or '(none)'}")
        # Only display text in status; other settings are fixed by the API
    
    def _process_commands(self):
        """Process commands from the API server"""
        try:
            while True:
                command = self.command_queue.get_nowait()
                
                if command['type'] == 'update':
                    data = command['data']
                    
                    # Only 'text' is accepted from api.py; enforce defaults for other settings
                    if 'text' in data:
                        self.display_state.text = data['text']
                        self.display_state.text_bitmap = TextRenderer.render_text(data['text'])
                        self.display_state.text_width = len(self.display_state.text_bitmap[0]) if self.display_state.text_bitmap else 0
                        self.display_state.scroll_position = 0
                        self.display_state.is_running = True
                        # enforce api.py fixed settings
                        self.display_state.mode = 'left'
                        self.display_state.speed = 4
                        self.display_state.brightness = 100
                        self.display_state.color = 'red'
                    
                    self._update_display()
                
                elif command['type'] == 'clear':
                    self.display_state.clear()
                    self._update_display()
                
                elif command['type'] == 'server_status':
                    self.server_status.set(command['status'])
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(50, self._process_commands)
    
    def stop(self):
        """Stop the animation loop"""
        self.animation_running = False


# ============================================
# Flask API Server
# ============================================

def create_flask_app(display_state, command_queue):
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    CORS(app)
    # Use the real creator for icon names and supported characters
    creator = SimpleTextAndIcons()
    BUILTIN_ICON_NAMES = set(creator.bitmap_named.keys())
    SUPPORTED_CHARS = set(creator.charmap)
    
    def _validate_display_string(text):
        """Validate a display string similar to SimpleTextAndIcons.bitmap()
        Raises KeyError, ValueError, FileNotFoundError or OSError on invalid input.
        """
        if not isinstance(text, str):
            raise ValueError("Display text must be a string")

        # Allow escape :: -> : so treat empty name specially
        tokens = re.findall(r':([^:]*):', text)
        for name in tokens:
            if name == '':
                continue
            if re.match(r'^[0-9]+$', name):
                continue
            if '.' in name:
                # image path -> must exist
                import os
                if not os.path.exists(name):
                    raise FileNotFoundError(f"Image file not found: {name}")
                continue
            # builtin icons come from SimpleTextAndIcons.bitmap_named
            if name not in BUILTIN_ICON_NAMES:
                raise KeyError(f"Unknown builtin icon: {name}")

        # Validate remaining characters (remove tokens first)
        text_no_tokens = re.sub(r':[^:]*:', '', text)
        for ch in text_no_tokens:
            if ch == '\n' or ch == '\r':
                continue
            if ch not in SUPPORTED_CHARS:
                raise KeyError(f"Unsupported character: {ch}")

    @app.route('/display-text', methods=['POST'])
    def update_display():
        """Mimic `api.py` POST /display-text behavior and responses."""
        try:
            data = request.get_json()
            if not data or 'text' not in data:
                return {'error': "Invalid display string format", 'details': "Missing 'text' field"}, 400

            text = data.get('text', '')

            # Validate using local validator to avoid importing hardware module
            try:
                _validate_display_string(text)
            except (KeyError, ValueError, FileNotFoundError, OSError) as e:
                return {'error': 'Invalid display string format', 'details': str(e)}, 400

            # API parity: `api.py` only accepts `text`. Enforce defaults for other settings.
            update_data = {
                'text': text,
                'mode': 'left',
                'speed': 4,
                'brightness': 100,
                'color': 'red'
            }

            command_queue.put({'type': 'update', 'data': update_data})

            # update internal state with enforced defaults
            display_state.text = text
            display_state.mode = 'left'
            display_state.speed = 4
            display_state.brightness = 100
            display_state.color = 'red'

            return {'status': 'Text displayed on LED', 'text': text}, 200

        except Exception as e:
            return {'error': 'Invalid display string format', 'details': str(e)}, 400
    
    @app.route('/predefined-icons', methods=['GET'])
    def get_icons():
        """Return icon names in the same format as `api.py` (eg. ':heart:')"""
        try:
            icons = []
            for k in creator.bitmap_named.keys():
                icons.append(f':{k}:')
            return {'icons': icons}, 200
        except Exception as e:
            return {'status': 'error', 'message': f'Failed to retrieve icon library: {str(e)}'}, 500

    @app.route('/display-summary', methods=['POST'])
    def display_summary():
        """Mimic `api.py` POST /display-summary endpoint."""
        try:
            summary = "Open LED Badge - Free, hackable, and fun! :star: :heart:"

            try:
                _validate_display_string(summary)
            except (KeyError, ValueError, FileNotFoundError, OSError) as e:
                return {'error': 'Invalid display string format', 'details': str(e)}, 400

            command_queue.put({'type': 'update', 'data': {'text': summary, 'mode': 'left', 'speed': 4}})
            display_state.text = summary
            display_state.mode = 'left'
            display_state.speed = 4
            return {'status': 'Summary displayed on LED'}, 200
        except Exception as e:
            return {'error': 'Invalid display string format', 'details': str(e)}, 400
    
    # Mock exposes only the same endpoints as api.py: /display-text, /predefined-icons, /display-summary
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "status": "error",
            "message": "Endpoint not found"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({
            "status": "error",
            "message": "Method not allowed"
        }), 405
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500
    
    return app


def run_flask_server(app, command_queue, host='0.0.0.0', port=5000):
    """Run Flask server in a separate thread"""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Notify GUI that server is starting
    command_queue.put({
        'type': 'server_status',
        'status': f'Server: Running on http://{host}:{port}'
    })
    
    app.run(host=host, port=port, threaded=True, use_reloader=False)


# ============================================
# Main Application
# ============================================

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LED Name Badge Mock Server with GUI')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Server port (default: 5000)')
    args = parser.parse_args()
    
    # Create shared state and command queue
    display_state = DisplayState()
    command_queue = queue.Queue()
    
    # Create Flask app
    flask_app = create_flask_app(display_state, command_queue)
    
    # Start Flask server in background thread
    server_thread = threading.Thread(
        target=run_flask_server,
        args=(flask_app, command_queue, args.host, args.port),
        daemon=True
    )
    server_thread.start()
    
    # Create and run Tkinter GUI
    root = tk.Tk()
    gui = LEDDisplayGUI(root, display_state, command_queue)
    
    # Set initial demo text (API only updates `text`)
    command_queue.put({
        'type': 'update',
        'data': {
            'text': 'LED Badge API Ready!'
        }
    })
    
    def on_closing():
        gui.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           LED Name Badge Mock Server with GUI                ║
╠══════════════════════════════════════════════════════════════╣
║  Server running at: http://{args.host}:{args.port:<24}║
║                                                              ║
║  API Endpoints:                                              ║
║    POST /display-text     - Update display text              ║
║    GET  /predefined-icons - Get available icons              ║
║    POST /display-summary  - Display demo summary text        ║
║                                                              ║
║  Example:                                                    ║
║    curl -X POST http://localhost:{args.port}/display-text \\    ║
║      -H "Content-Type: application/json" \\                   ║
║      -d '{{"text": "Hello World!"}}'                          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    root.mainloop()


if __name__ == '__main__':
    main()
