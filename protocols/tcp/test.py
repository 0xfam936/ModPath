from rich.console import Console
from rich.prompt import Prompt

console = Console()
history = []

while True:
    msg = Prompt.ask("[bold cyan]You")

    if msg == "exit":
        break

    history.append(("You", msg))
    history.append(("Bot", f"Echo -> {msg}"))

    console.clear()
    console.rule("Chat")

    for user, text in history:
        console.print(f"[bold green]{user}:[/bold green] {text}")
