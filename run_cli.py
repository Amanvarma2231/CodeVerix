"""
CodeVerix CLI Runner
Run the LLM-to-LLM session from the terminal with rich output.

Usage:
    python run_cli.py "Write a Python function to find prime numbers up to N"
    python run_cli.py  (interactive mode)
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH = True
except ImportError:
    RICH = False

from orchestrator import ConversationOrchestrator
from llm_agents import Message

console = Console() if RICH else None

COLORS = {
    "system":    "cyan",
    "coder":     "blue",
    "validator": "green",
}


def print_message(msg: Message):
    if RICH:
        role  = msg.role
        color = COLORS.get(role, "white")
        title = f"[{color} bold]{msg.sender}[/{color} bold]  [dim]{msg.timestamp}[/dim]"
        content = msg.content

        if msg.msg_type == "code" and "```python" in content:
            # Print explanation
            parts = content.split("```python")
            console.print(Panel(parts[0].strip(), title=title, border_style=color))
            code = parts[1].split("```")[0].strip()
            syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="📝 Generated Code", border_style=color))
            if len(parts[1].split("```")) > 1:
                console.print(Panel(parts[1].split("```")[1].strip(), border_style=color))
        elif msg.msg_type == "validation":
            is_pass = "VALIDATION RESULT: PASS" in content.upper()
            border  = "green" if is_pass else "red"
            icon    = "✅" if is_pass else "❌"
            console.print(Panel(content, title=f"{icon} {title}", border_style=border))
        elif role == "system":
            console.print(f"  [dim cyan]🔄 {msg.content}[/dim cyan]")
        else:
            console.print(Panel(content, title=title, border_style=color))
    else:
        # Plain fallback
        sep = "─" * 60
        print(f"\n{sep}")
        print(f"[{msg.sender}] {msg.timestamp}")
        print(msg.content)
        print(sep)


def run(task: str, max_rounds: int = 2):
    """Run the full LLM-to-LLM coding session."""
    if RICH:
        console.rule("[bold blue]🤖 CodeVerix – LLM↔LLM Communication System[/bold blue]")
        console.print(f"\n[bold]Task:[/bold] {task}\n")
        console.print(f"[dim]Provider: {os.getenv('LLM_PROVIDER','gemini')} | "
                      f"Coder: {os.getenv('CODER_MODEL','?')} | "
                      f"Validator: {os.getenv('VALIDATOR_MODEL','?')} | "
                      f"Max rounds: {max_rounds}[/dim]\n")

    orchestrator = ConversationOrchestrator(
        max_rounds=max_rounds,
        on_message=print_message,
    )

    result = orchestrator.run_coding_task(task)

    # Summary
    if RICH:
        console.rule("[bold]📊 Session Summary[/bold]")
        status_color = "green" if result["passed"] else "red"
        console.print(f"  Status  : [{status_color}]{'PASSED ✅' if result['passed'] else 'FAILED ❌'}[/{status_color}]")
        console.print(f"  Rounds  : {result['rounds']}")
        console.print(f"  Messages: {len(result['history'])}")
    else:
        print(f"\n=== SUMMARY ===")
        print(f"Status : {'PASSED' if result['passed'] else 'FAILED'}")
        print(f"Rounds : {result['rounds']}")

    # Save log
    log_file = f"conversation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    orchestrator.export_history(log_file)
    if RICH:
        console.print(f"\n[dim]💾 Conversation saved to {log_file}[/dim]")
    else:
        print(f"\nConversation saved to {log_file}")


def interactive_mode():
    """Interactive REPL for the CLI."""
    if RICH:
        console.print("[bold green]🤖 CodeVerix Interactive Mode[/bold green]")
        console.print("[dim]Type a coding task, or 'quit' to exit.[/dim]\n")
    else:
        print("CodeVerix Interactive Mode. Type a task or 'quit' to exit.\n")

    max_rounds = 2
    while True:
        try:
            if RICH:
                task = console.input("[bold yellow]📋 Task > [/bold yellow]").strip()
            else:
                task = input("Task > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not task or task.lower() in ("quit", "exit", "q"):
            break

        run(task, max_rounds=max_rounds)
        print()


if __name__ == "__main__":
    # Check API key
    provider = os.getenv("LLM_PROVIDER", "gemini")
    key_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
    if not os.getenv(key_name, "").strip():
        print(f"ERROR: {key_name} not set.")
        print("Copy .env.example to .env and add your API key.")
        sys.exit(1)

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        run(task)
    else:
        interactive_mode()
