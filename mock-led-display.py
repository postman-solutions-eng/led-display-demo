#!/usr/bin/env python3
"""
LED Name Badge Mock GUI Display
"""

import tkinter as tk
import queue
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


# Simple holder for display state used by the GUI
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
                
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(50, self._process_commands)
    
    def stop(self):
        """Stop the animation loop"""
        self.animation_running = False


# ============================================
# Main Application
# ============================================

def run_gui(display_state=None, command_queue=None):
    """Run the Tkinter GUI. If `display_state` or `command_queue` are not
    provided, new ones will be created. This function blocks (runs the
    Tk mainloop) and is intended to be called as the primary process when a
    GUI is desired."""
    if display_state is None:
        display_state = DisplayState()
    if command_queue is None:
        command_queue = queue.Queue()

    root = tk.Tk()
    gui = LEDDisplayGUI(root, display_state, command_queue)

    # Set initial demo text (API only updates `text`)
    command_queue.put({'type': 'update', 'data': {'text': 'LED Badge API Ready!'}})

    def on_closing():
        gui.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    print('LED Name Badge GUI running')
    root.mainloop()
