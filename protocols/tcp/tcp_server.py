import ssl
import asyncio
import socket
from typing import List
from colorama import Fore, init
import secrets
import json

init(autoreset=True)


class TCPServer:

    def __init__(self, host: str, port: int, cert: str | None, keyfile: str | None, auth_tokens: List[str] | None):
        self.HOST = host
        self.PORT = port
        self.CERT = cert
        self.KEYFILE = keyfile
        self.agents = []
        self.messages = asyncio.Queue()
        self.agent_count = 0
        self.AUTH_TOKENS = auth_tokens
        self.loop = None

    def ssl_setup(self) -> ssl.SSLContext | None:
        if not (self.CERT and self.KEYFILE):
            return None

        context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=self.CERT, keyfile=self.KEYFILE)
        return context

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        ip, port = writer.get_extra_info("peername")

        # Change 2: The "Null" Check
        # If self.AUTH_TOKENS is None or an empty list [], this block is skipped.
        # This fulfills your "if null nothing happens" requirement.
        if self.AUTH_TOKENS:
            try:
                token_data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
                token = token_data.decode(errors="ignore").strip()

                # Change 3: Check against the LIST securely
                is_valid = False
                for valid_token in self.AUTH_TOKENS:
                    # We still use compare_digest to prevent timing attacks
                    if secrets.compare_digest(token, valid_token):
                        is_valid = True
                        break

                if not is_valid:
                    print(f"{Fore.YELLOW}[!] Unauthorized connection attempt from {ip}:{port} (Invalid Token)")
                    writer.close()
                    await writer.wait_closed()
                    return

            except asyncio.TimeoutError:
                print(f"{Fore.YELLOW}[!] Authentication timeout from {ip}:{port}")
                writer.close()
                await writer.wait_closed()
                return
            except Exception as e:
                print(f"{Fore.RED}[!] Error during handshake with {ip}:{port}: {e}")
                writer.close()
                await writer.wait_closed()
                return

        loop = asyncio.get_running_loop()
        try:
            hostname = await loop.run_in_executor(None, socket.getfqdn, ip)
        except Exception:
            hostname = "unknown"

        client = {
            "id": self.agent_count,
            "ip": ip,
            "port": port,
            "hostname": hostname,
            "writer": writer,
            "tasks": {}
        }

        self.agents.append(client)
        self.agent_count += 1
        print(f"\n{Fore.GREEN}[+] Agent {client['ip']}@{client['hostname']} connected.\n")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode(errors="ignore").strip()
                if not message:
                    continue

                try:
                    parsed_data = json.loads(message)
                    task_id = parsed_data.get("task_id")
                    output = parsed_data.get("output", "")

                    if task_id:
                        if task_id not in client["tasks"]:
                            client["tasks"][task_id] = {"command": "Unknown (Async)", "output": None}
                        client["tasks"][task_id]["output"] = output
                    else:
                        print(f"{Fore.YELLOW}[!] Rogue JSON received from agent {client['id']}: {message}")
                except json.JSONDecodeError:
                    print(f"{Fore.YELLOW}[*] Raw message from agent {client['id']}: {message}")
                

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"{Fore.RED}[!] Error from agent {client['id']}: {e}")
        finally:
            print(f"{Fore.RED}[-] Agent {client['id']} disconnected")
            if client in self.agents:
                self.agents.remove(client)
                self.agent_count -= 1
            writer.close()
            await writer.wait_closed()

    async def register_task(self, agent_id: int, task_id: int, command: str):
        agent =  next ((a for a in self.agents if a["id"] == agent_id), None)
        if agent:
            agent["tasks"][task_id] =  {"command": command, "output": None}
    
    async def get_task_response(self, agent_id: int, task_id: str, timeout: int = 10):
        agent = next((a for a in self.agents if a["id"] == agent_id), None)
        if not agent:
            return "[!] Agent not found."

        end_time = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < end_time:
            # Check if the task exists AND if the output is no longer None
            if task_id in agent["tasks"] and agent["tasks"][task_id]["output"] is not None:
                return agent["tasks"][task_id]["output"]
            await asyncio.sleep(0.1) 
        return "[Agent timeout]"

    async def shut_all_agents(self):
        """Notifies all agents to close and cleans up server resources."""
        # Create a special shutdown task
        shutdown_payload = json.dumps({
            "task_id": "9999", 
            "command": "kill" # Or "exit" depending on your agent logic
        }) + "\n"

        print(f"\n[{Fore.YELLOW}!{Fore.RESET}] Sending shutdown signal to {len(self.agents)} agents...")

        for agent in self.agents:
            try:
                writer = agent["writer"]
                writer.write(shutdown_payload.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print(f"[{Fore.RED}!{Fore.RESET}] Error closing agent {agent['id']}: {e}")

        self.agents.clear() # Empty the list
        print(f"[{Fore.GREEN}✓{Fore.RESET}] All connections severed.")
   


    async def send(self, agent_id: int, message: str) -> None:
        agent = next((a for a in self.agents if a["id"] == agent_id), None)
        if agent is None:
            print(f"{Fore.YELLOW}[!] Agent with id {agent_id} not found")
            return
        writer = agent["writer"]
        try:
            if not message.endswith("\n"):
                message += "\n"
            writer.write(message.encode())  
            await writer.drain()            
        except Exception as e:
            print(f"{Fore.RED}[!] Error sending to agent {agent['id']}: {e}")

    async def send_multi(self, agent_ids: List[int], message:str):
        for id in agent_ids:
            await self.send(id, message)

    async def start(self):
        self.loop = asyncio.get_running_loop()
        ssl_context = self.ssl_setup()
        
        try:
            server = await asyncio.start_server(
                self.handle_client,
                self.HOST,  
                self.PORT,
                ssl=ssl_context
            )
        except OSError as e:
            print(f"{Fore.RED}[!] Failed to bind to port {self.PORT}: {e}")
            return

        addr = server.sockets[0].getsockname()
        proto = "TLS" if ssl_context else "TCP"
        print(f"[{Fore.GREEN}+{Fore.RESET}] {Fore.GREEN}{proto}{Fore.RESET} server listening on {Fore.BLUE}{addr[0]}{Fore.RESET}:{Fore.BLUE}{addr[1]}{Fore.RESET}")

        async with server:
            await server.serve_forever()

