import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Container
from protocols.tcp.tcp_server_controller import TcpServerController



MODPATH_ART = """
  __  __           _ ____       _   _     
 |  \/  |         | |  _ \     | | | |    
 | \  / | ___   __| | |_) |__ _| |_| |__  
 | |\/| |/ _ \ / _` |  __/ _` | __| '_ \  
 | |  | | (_) | (_| | | | (_| | |_| | | | 
 |_|  |_|\___/ \__,_|_|  \__,_|\__|_| |_| 
"""
SUBTITLE = "made by 0xfam936"

# ==========================================
# 1. The Textual UI Class (The View)
# ==========================================
class ProtocolSelectorApp(App):
    """The TUI App responsible ONLY for selecting a protocol."""

    CSS = """
    Screen { align: center middle; background: black; }
    #main-container {
        width: 90; height: auto;
        border: heavy magenta; background: #0d0d0d;
        padding: 1 2;
    }
    .ascii-art {
        text-align: center; color: blue; text-style: bold;
    }
    .subtitle {
        text-align: center; color: red; text-style: bold italic;
        margin-bottom: 2; border-bottom: solid cyan;
    }
    DataTable {
        height: 10; border: heavy green; margin-top: 1;
    }
    DataTable > .datatable--header {
        text-style: bold; color: cyan; background: black;
    }
    DataTable > .datatable--cursor {
        background: green; color: black; text-style: bold;
    }
    """

    BINDINGS = [("escape", "quit", "Exit"), ("enter", "select_cursor", "Select")]

    def __init__(self, protocols_list):
        super().__init__()
        self.protocols_list = protocols_list

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield Static(MODPATH_ART, classes="ascii-art")
            yield Static(SUBTITLE, classes="subtitle")
            yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("PROTOCOL", "FILEPATH")
        
        # Add rows. IMPORTANT: We store the INDEX as the key 
        # so we can retrieve the full object later.
        for index, item in enumerate(self.protocols_list):
            table.add_row(
                item["protocol"], 
                item["filepath"], 
                key=str(index) # Key must be string
            )
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # Get the index (key) of the selected row
        row_key = event.row_key.value
        index = int(row_key)
        
        # Return the FULL object (including the 'module' class)
        selected_item = self.protocols_list[index]
        self.exit(selected_item)


# ==========================================
# 2. The Logic Class (The Controller)
# ==========================================
class MainMenu:
    def __init__(self) -> None:
        # Define your available modules here
        self.modules = [
            {
                "protocol": "TCP", 
                "filepath": "protocols/tcp/tcp_server_controller", 
                "module": TcpServerController
            }
            
        ]

    def start(self):
        """Launches the UI, waits for selection, then runs the module."""
        
        # 1. Instantiate the Textual App
        app = ProtocolSelectorApp(self.modules)
        
        # 2. Run it (This blocks until user selects or quits)
        # Note: We do NOT use curses.wrapper here!
        selected_module_data = app.run()

        # 3. Process the result
        if selected_module_data:
            # User selected something
            print(f"\n[+] Loading {selected_module_data['protocol']}...")
            
            # Instantiate the class and run its start method
            # This assumes TcpServerController has a .start() method
            controller_class = selected_module_data["module"]
            controller_instance = controller_class()
            controller_instance.start()
        else:
            # User pressed ESC
            print("[-] Exiting.")
            sys.exit(0)

# ==========================================
# 3. Execution
# ==========================================
if __name__ == "__main__":
    MainMenu().start()
