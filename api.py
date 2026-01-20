from flask import Flask, request
from lednamebadge import SimpleTextAndIcons, LedNameBadge
from array import array

import argparse
import threading
import queue
import importlib.util
import os

app = Flask(__name__)


def _process_and_write(text, command_queue=None, write_hardware=True):
    """Create the scene buffer for `text` and either write to hardware,
    post to the mock GUI via `command_queue`, or both depending on flags.
    """
    creator = SimpleTextAndIcons()
    scene_bitmap = creator.bitmap(text)

    buf = array('B')
    buf.extend(LedNameBadge.header([scene_bitmap[1]], [4], [0], [0], [0], 100))
    buf.extend(scene_bitmap[0])

    # Debug: report what we're about to do
    print(f"_process_and_write: write_hardware={write_hardware}, command_queue_set={command_queue is not None}, text='{text[:50]}'")

    if write_hardware:
        try:
            LedNameBadge.write(buf)
            print("_process_and_write: wrote to hardware")
        except Exception as e:
            print(f"_process_and_write: hardware write failed: {e}")

    if command_queue is not None:
        # API mock expects only `text` updates
        try:
            command_queue.put({'type': 'update', 'data': {'text': text}})
            print("_process_and_write: enqueued update to mock GUI")
        except Exception as e:
            print(f"_process_and_write: enqueue failed: {e}")


@app.route('/display-text', methods=['POST'])
def display_text():
    data = request.get_json()
    text = data.get('text', '')

    try:
        # Validate and prepare scene; actual write/mocking handled in main
        creator = SimpleTextAndIcons()
        creator.bitmap(text)
    except (KeyError, ValueError, FileNotFoundError, OSError) as e:
        return {'error': 'Invalid display string format', 'details': str(e)}, 400
    except Exception as e:
        return {'error': 'Invalid display string format', 'details': str(e)}, 400

    # On actual run, the main program will decide whether to write to
    # hardware and/or the mock GUI by providing globals.
    global _API_COMMAND_QUEUE, _API_WRITE_HARDWARE
    _process_and_write(text, command_queue=globals().get('_API_COMMAND_QUEUE'), write_hardware=globals().get('_API_WRITE_HARDWARE', True))

    return {'status': 'Text displayed on LED', 'text': text}, 200


@app.route('/predefined-icons', methods=['GET'])
def get_predefined_icons():
    creator = SimpleTextAndIcons()
    icons = [f':{name}:' for name in creator.bitmap_named.keys()]
    return {'icons': icons}, 200


@app.route('/display-summary', methods=['POST'])
def display_summary():
    summary = "Open LED Badge - Free, hackable, and fun! :star: :heart:"

    try:
        creator = SimpleTextAndIcons()
        creator.bitmap(summary)
    except (KeyError, ValueError, FileNotFoundError, OSError) as e:
        return {'error': 'Invalid display string format', 'details': str(e)}, 400

    global _API_COMMAND_QUEUE, _API_WRITE_HARDWARE
    _process_and_write(summary, command_queue=globals().get('_API_COMMAND_QUEUE'), write_hardware=globals().get('_API_WRITE_HARDWARE', True))

    return {'status': 'Summary displayed on LED'}, 200


def _load_mock_gui_module():
    """Dynamically load `mock-led-display.py` as module `mock_gui`.
    This avoids Python import issues with hyphens in the filename.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, 'mock-led-display.py')
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location('mock_gui', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description='LED Name Badge API server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5001)
    parser.add_argument('--mock', action='store_true', help='Run with mock GUI instead of writing to hardware')
    parser.add_argument('--both', action='store_true', help='Write to hardware and also show mock GUI')
    args = parser.parse_args()

    # Decide behavior
    use_mock = args.mock or args.both
    write_hardware = not args.mock

    if use_mock:
        # Prepare shared state and command queue for the GUI
        cmd_q = queue.Queue()
        globals()['_API_COMMAND_QUEUE'] = cmd_q
        globals()['_API_WRITE_HARDWARE'] = args.both

        # Start Flask server in background thread, then run GUI in foreground
        server_thread = threading.Thread(
            target=app.run,
            kwargs={'host': args.host, 'port': args.port, 'threaded': True, 'use_reloader': False},
            daemon=True,
        )
        server_thread.start()

        # Load and run GUI (this will block in the main thread)
        mock_gui = _load_mock_gui_module()
        # mock_gui.run_gui accepts display_state and command_queue optionally; pass the queue
        mock_gui.run_gui(display_state=None, command_queue=cmd_q)
    else:
        # Default: run API server and write to hardware as before
        globals()['_API_WRITE_HARDWARE'] = True
        app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
