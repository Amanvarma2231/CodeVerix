"""
Unit tests for CodeVerix LLM-to-LLM Communication System.
Run: python test_system.py
(Tests mock the LLM API so no real key needed)
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Set dummy env so imports work
os.environ.setdefault("LLM_PROVIDER",     "gemini")
os.environ.setdefault("GEMINI_API_KEY",   "test-key")
os.environ.setdefault("CODER_MODEL",      "gemini-1.5-flash")
os.environ.setdefault("VALIDATOR_MODEL",  "gemini-1.5-pro")

from llm_agents import Message, CoderLLM, ValidatorLLM
from orchestrator import ConversationOrchestrator


# ─── Mock LLM response ───────────────────────────────────────────────────────

MOCK_CODE_RESPONSE = """EXPLANATION:
Using a simple loop to find prime numbers.

```python
def is_prime(n: int) -> bool:
    \"\"\"Return True if n is a prime number.\"\"\"
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def primes_up_to(limit: int) -> list:
    \"\"\"Return all prime numbers up to limit.\"\"\"
    return [n for n in range(2, limit + 1) if is_prime(n)]
```

NOTES:
Time complexity O(n√n), suitable for small N.
"""

MOCK_VALIDATION_PASS = """VALIDATION RESULT: PASS ✅

SCORE: 9/10

ISSUES FOUND:
None

SUGGESTIONS:
- Could use Sieve of Eratosthenes for better performance on large N.

VERDICT:
The code is correct, well-commented, and follows PEP8 conventions. Good to use.
"""

MOCK_VALIDATION_FAIL = """VALIDATION RESULT: FAIL ❌

SCORE: 5/10

ISSUES FOUND:
- Missing type hints in function signature (severity: LOW)
- No input validation for negative numbers (severity: MEDIUM)

SUGGESTIONS:
- Add input validation: raise ValueError for n < 0

VERDICT:
The code has minor issues that should be fixed before production use.
"""


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestMessage(unittest.TestCase):
    def test_message_creation(self):
        m = Message("CoderLLM", "coder", "Hello", "code")
        self.assertEqual(m.sender,   "CoderLLM")
        self.assertEqual(m.role,     "coder")
        self.assertEqual(m.content,  "Hello")
        self.assertEqual(m.msg_type, "code")
        self.assertIsNotNone(m.timestamp)

    def test_to_dict(self):
        m   = Message("Test", "system", "hi", "text")
        d   = m.to_dict()
        for key in ("sender", "role", "content", "msg_type", "timestamp"):
            self.assertIn(key, d)


class TestCoderLLM(unittest.TestCase):
    @patch("llm_agents.call_llm", return_value=MOCK_CODE_RESPONSE)
    def test_code_generation(self, mock_llm):
        coder = CoderLLM()
        msg   = coder.code("Write a prime function")
        self.assertIsInstance(msg, Message)
        self.assertEqual(msg.role, "coder")
        self.assertEqual(msg.msg_type, "code")
        self.assertIn("```python", msg.content)

    @patch("llm_agents.call_llm", return_value=MOCK_CODE_RESPONSE)
    def test_code_with_feedback(self, mock_llm):
        coder = CoderLLM()
        msg   = coder.code("Write a prime function", validator_feedback="Fix edge cases")
        self.assertIsInstance(msg, Message)
        # The call should have included feedback in prompt
        call_args = mock_llm.call_args
        self.assertIn("Fix edge cases", call_args[0][2])  # 3rd arg = user_message


class TestValidatorLLM(unittest.TestCase):
    @patch("llm_agents.call_llm", return_value=MOCK_VALIDATION_PASS)
    def test_validation_pass(self, mock_llm):
        validator = ValidatorLLM()
        code_msg  = Message("CoderLLM", "coder", MOCK_CODE_RESPONSE, "code")
        val_msg   = validator.validate("Write a prime function", code_msg.content)
        self.assertIsInstance(val_msg, Message)
        self.assertEqual(val_msg.role, "validator")
        self.assertTrue(validator.is_pass(val_msg))

    @patch("llm_agents.call_llm", return_value=MOCK_VALIDATION_FAIL)
    def test_validation_fail(self, mock_llm):
        validator = ValidatorLLM()
        code_msg  = Message("CoderLLM", "coder", MOCK_CODE_RESPONSE, "code")
        val_msg   = validator.validate("Write a prime function", code_msg.content)
        self.assertFalse(validator.is_pass(val_msg))


class TestOrchestrator(unittest.TestCase):
    @patch("llm_agents.call_llm")
    def test_pass_on_first_round(self, mock_llm):
        """Validation passes on the first round → 1 code + 1 validation message."""
        mock_llm.side_effect = [MOCK_CODE_RESPONSE, MOCK_VALIDATION_PASS]
        orch   = ConversationOrchestrator(max_rounds=3)
        result = orch.run_coding_task("Write a prime function")
        self.assertTrue(result["passed"])
        self.assertEqual(result["rounds"], 1)
        # Coder + Validator + system messages
        code_msgs = [m for m in orch.history if m.role == "coder"]
        val_msgs  = [m for m in orch.history if m.role == "validator"]
        self.assertEqual(len(code_msgs), 1)
        self.assertEqual(len(val_msgs),  1)

    @patch("llm_agents.call_llm")
    def test_fail_then_pass(self, mock_llm):
        """Validation fails once, then passes on round 2."""
        mock_llm.side_effect = [
            MOCK_CODE_RESPONSE,  # coder round 1
            MOCK_VALIDATION_FAIL,  # validator round 1 → FAIL
            MOCK_CODE_RESPONSE,  # coder round 2 (fix)
            MOCK_VALIDATION_PASS,  # validator round 2 → PASS
        ]
        orch   = ConversationOrchestrator(max_rounds=3)
        result = orch.run_coding_task("Write a prime function")
        self.assertTrue(result["passed"])
        self.assertEqual(result["rounds"], 2)
        code_msgs = [m for m in orch.history if m.role == "coder"]
        val_msgs  = [m for m in orch.history if m.role == "validator"]
        self.assertEqual(len(code_msgs), 2)
        self.assertEqual(len(val_msgs),  2)

    @patch("llm_agents.call_llm")
    def test_always_fail(self, mock_llm):
        """Validation always fails → passed=False after max_rounds."""
        mock_llm.side_effect = [
            MOCK_CODE_RESPONSE, MOCK_VALIDATION_FAIL,
            MOCK_CODE_RESPONSE, MOCK_VALIDATION_FAIL,
        ]
        orch   = ConversationOrchestrator(max_rounds=2)
        result = orch.run_coding_task("Write a prime function")
        self.assertFalse(result["passed"])
        self.assertEqual(result["rounds"], 2)

    @patch("llm_agents.call_llm")
    def test_on_message_callback(self, mock_llm):
        """Callback fires for every message."""
        mock_llm.side_effect = [MOCK_CODE_RESPONSE, MOCK_VALIDATION_PASS]
        received = []
        def cb(msg): received.append(msg)
        orch = ConversationOrchestrator(max_rounds=2, on_message=cb)
        orch.run_coding_task("task")
        self.assertGreater(len(received), 0)
        self.assertEqual(received, orch.history)

    @patch("llm_agents.call_llm")
    def test_history_dict_format(self, mock_llm):
        """History dicts contain required keys."""
        mock_llm.side_effect = [MOCK_CODE_RESPONSE, MOCK_VALIDATION_PASS]
        orch   = ConversationOrchestrator(max_rounds=2)
        result = orch.run_coding_task("task")
        for entry in result["history"]:
            for key in ("sender", "role", "content", "msg_type", "timestamp"):
                self.assertIn(key, entry)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
