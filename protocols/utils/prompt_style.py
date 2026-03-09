import builtins
import io
import sys
import re
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText, ANSI
from prompt_toolkit import print_formatted_text
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.patch_stdout import patch_stdout

# 1. THE HIJACK
original_print = builtins.print
shared_last_log = "System Ready"

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def custom_print(*args, **kwargs):
    global shared_last_log
    
    # Capture the exact text the user is trying to print
    temp_buffer = io.StringIO()
    original_print(*args, file=temp_buffer, **kwargs)
    printed_text = temp_buffer.getvalue()
    
    if printed_text.strip():
        # Strip colors for the toolbar
        clean_text = ansi_escape.sub('', printed_text.strip()).split('\n')[-1]
        shared_last_log = clean_text[:80] 

    # --- THE MAGIC FIX ---
    # If we are printing to the normal screen...
    if kwargs.get('file') is None or kwargs.get('file') == sys.stdout:
        # Use prompt_toolkit's native color engine to safely draw the ANSI colors!
        print_formatted_text(ANSI(printed_text), end="")
    else:
        # If it's writing to a file or somewhere else, do it normally
        original_print(*args, **kwargs)

# Overwrite Python's global print function
builtins.print = custom_print

# 2. THE PROMPT SETUP
shared_history = InMemoryHistory()

def styled_prompt(username: str, host: str, history_size: int = 1000):
    style = Style.from_dict({
        "": "#ff0066",
        "username": "#884444",
        "at": "#00aa00",
        "colon": "#0000aa",
        "pound": "#00aa00",
        "host": "#00ffff",
        "auto-suggestion": "#555555",
    })

    message = FormattedText([
        ("class:username", username),
        ("class:at", "@"),
        ("class:host", host),
        ("class:colon", ":"),
        ("class:pound", "# "),
    ])

    def get_toolbar():
        # Using the direct styling we set up earlier!
        return FormattedText([
            ("bg:#003388 #ffffff bold noreverse", f" [LOG]: {shared_last_log} ")
        ])

    def read_command() -> str:
        with patch_stdout():
            text = prompt(
                message,
                style=style,
                history=shared_history,
                auto_suggest=AutoSuggestFromHistory(),
                bottom_toolbar=get_toolbar,
            )

        while len(shared_history._loaded_strings) > history_size:
            shared_history._loaded_strings.pop(0)

        return text

    return read_command
