"""
Orchestrator: manages the full LLM-to-LLM conversation loop.
- Maintains a shared conversation history (visible to humans)
- Runs: CoderLLM codes → ValidatorLLM validates → loop until PASS or max rounds
"""

import json
import time
from typing import List, Callable, Optional
from llm_agents import CoderLLM, ValidatorLLM, Message


class ConversationOrchestrator:
    """
    Orchestrates multi-round LLM-to-LLM conversations.
    Every message is appended to self.history so the human can watch live.
    """

    def __init__(
        self,
        max_rounds: int = 3,
        on_message: Optional[Callable[[Message], None]] = None,
    ):
        self.coder     = CoderLLM()
        self.validator = ValidatorLLM()
        self.history: List[Message] = []
        self.max_rounds = max_rounds
        self.on_message = on_message  # callback so UI can update in real-time

    # ── internal helpers ─────────────────────────────────────────────────────

    def _add(self, msg: Message):
        """Append message to history and fire callback."""
        self.history.append(msg)
        if self.on_message:
            self.on_message(msg)

    def _system_msg(self, text: str):
        """Add an orchestrator status message."""
        m = Message("🔄 Orchestrator", "system", text, msg_type="system")
        self._add(m)

    # ── public API ───────────────────────────────────────────────────────────

    def run_coding_task(self, task: str) -> dict:
        """
        Full coding loop:
          1. CoderLLM generates code
          2. ValidatorLLM validates
          3. If FAIL and rounds left → CoderLLM fixes → repeat
          4. Return summary dict
        """
        self.history.clear()

        # Announce task
        self._system_msg(f"📋 New Task Received:\n{task}")
        time.sleep(0.3)
        self._system_msg(f"🤖 Sending task to {self.coder.name}...")

        validator_feedback = None
        passed = False
        final_code_msg = None
        final_validation_msg = None

        for round_num in range(1, self.max_rounds + 1):
            self._system_msg(f"─── Round {round_num} / {self.max_rounds} ───")

            # Step 1: CoderLLM codes
            self._system_msg(f"✍️  {self.coder.name} is writing code...")
            code_msg = self.coder.code(task, validator_feedback)
            self._add(code_msg)
            final_code_msg = code_msg
            time.sleep(0.3)

            # Step 2: ValidatorLLM validates
            self._system_msg(f"🔍 Passing code to {self.validator.name} for validation...")
            val_msg = self.validator.validate(task, code_msg.content)
            self._add(val_msg)
            final_validation_msg = val_msg
            time.sleep(0.3)

            # Step 3: Check result
            if self.validator.is_pass(val_msg):
                self._system_msg(
                    f"✅ VALIDATION PASSED on round {round_num}! Code is ready."
                )
                passed = True
                break
            else:
                if round_num < self.max_rounds:
                    self._system_msg(
                        f"❌ Validation FAILED. Sending feedback back to {self.coder.name} for fixes..."
                    )
                    validator_feedback = val_msg.content
                else:
                    self._system_msg(
                        f"⚠️  Max rounds reached. Final validation status: FAIL."
                    )

        return {
            "task":            task,
            "passed":          passed,
            "rounds":          round_num,
            "final_code":      final_code_msg.content if final_code_msg else "",
            "final_validation": final_validation_msg.content if final_validation_msg else "",
            "history":         [m.to_dict() for m in self.history],
        }

    def run_chat(self, task: str) -> dict:
        """
        Simple single-turn: CoderLLM responds → ValidatorLLM comments.
        Used when user sends a non-coding question.
        """
        self.history.clear()
        self._system_msg(f"💬 Chat mode — task: {task}")

        code_msg = self.coder.code(task)
        self._add(code_msg)

        val_msg = self.validator.validate(task, code_msg.content)
        self._add(val_msg)

        return {
            "task":    task,
            "passed":  self.validator.is_pass(val_msg),
            "history": [m.to_dict() for m in self.history],
        }

    def export_history(self, filepath: str = "conversation_log.json"):
        """Save full conversation history to JSON."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                [m.to_dict() for m in self.history],
                f,
                indent=2,
                ensure_ascii=False,
            )
        return filepath
