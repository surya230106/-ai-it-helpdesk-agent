from app.agent import agent
import json

import httpx
import pytest

from app.agent import llm_provider
from app.agent.llm_provider import OllamaProvider
from app.agent.ollama_tools import TOOLS


def test_ollama_tool_catalog_exposes_diagnostic_and_support_tools():
    names = {item["function"]["name"] for item in TOOLS}
    assert {"search_knowledge_base", "classify_issue", "estimate_priority", "generate_troubleshooting_steps", "create_ticket", "suggest_escalation"} <= names
    assert {"diagnose_wifi", "diagnose_bluetooth", "diagnose_camera", "diagnose_gpu", "diagnose_storage", "diagnose_battery", "diagnose_audio", "diagnose_display", "diagnose_windows", "diagnose_printer"} <= names


def test_ollama_tool_schemas_are_json_serializable_complete_and_unique():
    json.dumps(TOOLS)
    names = [tool["function"]["name"] for tool in TOOLS]
    assert len(names) == len(set(names))

    def check_schema(schema):
        if schema.get("type") == "object":
            assert isinstance(schema.get("properties"), dict)
            assert set(schema.get("required", [])) <= set(schema["properties"])
            for child in schema["properties"].values():
                check_schema(child)
        if schema.get("type") == "array" and "items" in schema:
            check_schema(schema["items"])

    for tool in TOOLS:
        function = tool["function"]
        assert tool["type"] == "function"
        assert function.get("name") and function.get("description")
        check_schema(function["parameters"])


def test_local_model_format_removes_private_thinking_and_old_duplicate_headings():
    value = "<think>private notes</think>\nWHAT IS HAPPENING?\nWi-Fi is connected.\nMOST LIKELY REASON:\nA network issue is likely."
    cleaned = agent._clean_model_text(value)
    assert "private notes" not in cleaned
    assert "WHAT IS HAPPENING?" not in cleaned
    assert "MOST LIKELY REASON:" not in cleaned


def test_wifi_definition_has_a_relevant_rule_based_fallback():
    answer = agent._info_answer("Explain Wi-Fi in simple words", "explanation", [])
    assert "without a cable" in answer
    assert "Manager status" not in answer


def test_qwen_tool_loop_executes_requested_tool_and_returns_real_result(monkeypatch):
    class FakeProvider:
        def __init__(self): self.calls = 0
        def chat(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "classify_issue", "arguments": {"text": "Wi-Fi is not working"}}}]}
            tool_message = next(message for message in messages if message.get("role") == "tool")
            tool_index = messages.index(tool_message)
            assert messages[tool_index - 1]["role"] == "assistant"
            assert messages[tool_index - 1]["tool_calls"][0]["function"]["name"] == "classify_issue"
            assert '"Network"' in tool_message["content"]
            return {"role": "assistant", "content": "WHY THIS IS HAPPENING:\nThe Wi-Fi problem is a network issue.\n\nLET'S CHECK:\nCheck another device.\n\nWHAT YOU SHOULD SEE:\nIt should connect.\n\nTELL ME WHICH ONE:\nA. It works\nB. It fails"}

    fake = FakeProvider()
    monkeypatch.setattr(agent, "configured_provider", lambda: fake)
    state = {"active": False, "issue_domain": "Network", "issue_type": "Wi-Fi is not working", "current_diagnostic_step": None}
    diagnosis = {"likely_cause": "Possible network issue", "confidence": "medium", "next_check": None}
    result, tools = agent._qwen_answer(None, 1, "Wi-Fi is not working", [], state, diagnosis, [])
    assert result and result.count("WHY THIS IS HAPPENING:") == 1
    assert tools == ["classify_issue"]
    assert fake.calls == 2


def test_ordinary_question_uses_qwen_without_sending_tools(monkeypatch):
    class FakeProvider:
        def chat(self, messages, tools=None):
            assert tools is None
            assert messages[-1]["role"] == "user"
            assert '"diagnostic_result": null' in messages[-1]["content"]
            assert '"rule_based_grounded_draft": null' in messages[-1]["content"]
            return {"role": "assistant", "content": "Wi-Fi connects a device to a network without a cable."}

    monkeypatch.setattr(agent, "configured_provider", lambda: FakeProvider())
    state = {"active": False, "issue_domain": "Network", "issue_type": "What is Wi-Fi?", "current_diagnostic_step": None}
    result, used_tools = agent._qwen_answer(None, 1, "What is Wi-Fi?", [], state, {"likely_cause": "No diagnosis needed"}, [])
    assert result.startswith("Wi-Fi connects")
    assert used_tools == []


def test_already_tried_reply_cannot_repeat_the_previous_action(monkeypatch):
    class RepeatingProvider:
        def chat(self, messages, tools=None):
            assert tools is None
            return {"role": "assistant", "content": "WHY THIS IS HAPPENING:\nThe issue remains.\n\nLET'S CHECK:\nRight-click Start > Device Manager > Display adapters. Read the names shown and look for a yellow warning sign.\n\nWHAT YOU SHOULD SEE:\nA warning sign may appear.\n\nTELL ME WHICH ONE:\nA. It is listed\nB. Warning"}

    monkeypatch.setattr(agent, "configured_provider", lambda: RepeatingProvider())
    action = "You already tried this check. Please tell me what you saw: A. It is listed / B. Warning"
    state = {"active": True, "turn": 1, "issue_domain": "Hardware", "issue_type": "NVIDIA GPU missing", "current_diagnostic_step": {"key": "gpu_device", "action": action, "expected": "The result shows what Windows sees.", "choices": ["A. It is listed", "B. Warning"]}, "steps_already_tried": ["gpu_device"]}
    result, tools = agent._qwen_answer(None, 1, "I already tried that", [], state, {"likely_cause": "You already checked this."}, [])
    assert result is None
    assert tools == []


def test_tool_execution_error_is_returned_to_model_safely(monkeypatch, caplog):
    class FakeProvider:
        def __init__(self): self.calls = 0
        def chat(self, messages, tools):
            self.calls += 1
            assert tools
            if self.calls == 1:
                return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "classify_issue", "arguments": {"text": "Wi-Fi is down"}}}]}
            tool_message = next(message for message in messages if message.get("role") == "tool")
            assert "could not be completed" in tool_message["content"]
            return {"role": "assistant", "content": "WHY THIS IS HAPPENING:\nThe Wi-Fi issue needs one check.\n\nLET'S CHECK:\nTry another device on the same Wi-Fi.\n\nWHAT YOU SHOULD SEE:\nThis shows whether other devices are affected.\n\nTELL ME WHICH ONE:\nA. It works\nB. It does not work"}

    monkeypatch.setattr(agent, "configured_provider", lambda: FakeProvider())
    monkeypatch.setattr(agent, "execute_ollama_tool", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("sensitive tool detail")))
    state = {"active": True, "issue_domain": "Network", "issue_type": "Wi-Fi is down", "current_diagnostic_step": {"key": "wifi", "action": "Check another device on the same Wi-Fi.", "expected": "The other device shows whether the issue affects the network.", "choices": ["A. It works", "B. It does not work"]}}
    result, used_tools = agent._qwen_answer(None, 1, "Wi-Fi is down", [], state, {"likely_cause": "Network problem"}, [])
    assert result and used_tools == ["classify_issue"]
    assert "sensitive tool detail" not in caplog.text


def test_tool_loop_stops_at_round_limit(monkeypatch, caplog):
    class LoopingProvider:
        def __init__(self): self.calls = 0
        def chat(self, messages, tools):
            self.calls += 1
            return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "classify_issue", "arguments": {"text": "Wi-Fi is down"}}}]}

    fake = LoopingProvider()
    monkeypatch.setattr(agent, "configured_provider", lambda: fake)
    monkeypatch.setattr(agent, "execute_ollama_tool", lambda *args, **kwargs: {"category": "Network"})
    state = {"active": True, "issue_domain": "Network", "issue_type": "Wi-Fi is down", "current_diagnostic_step": {"key": "wifi", "action": "Check another device.", "expected": "It shows if other devices are affected.", "choices": ["A", "B"]}}
    result, tools = agent._qwen_answer(None, 1, "Wi-Fi is down", [], state, {"likely_cause": "Network issue"}, [])
    assert result is None
    assert len(tools) == agent.MAX_TOOL_ROUNDS
    assert fake.calls == agent.MAX_TOOL_ROUNDS + 1
    assert "ollama_tool_round_limit_reached" in caplog.text


def test_http_error_logs_status_safe_body_and_request_metadata(monkeypatch, caplog):
    request = httpx.Request("POST", "http://ollama/api/chat")
    response = httpx.Response(400, json={"error": "Invalid API_KEY=topsecret for user@example.com after protected user phrase"}, request=request)

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs): return response

    monkeypatch.setattr(llm_provider.httpx, "Client", FakeClient)
    provider = OllamaProvider(base_url="http://ollama:11434", model="qwen3:8b")
    messages = [{"role": "user", "content": "protected user phrase"}]
    with pytest.raises(httpx.HTTPStatusError):
        provider.chat(messages, TOOLS[:1])
    logs = caplog.text
    assert "status_code=400" in logs
    assert "response_body=" in logs and "Invalid" in logs
    assert "endpoint=/api/chat" in logs and "model=qwen3:8b" in logs
    assert "tools_included=True" in logs and "tool_count=1" in logs and "message_roles=['user']" in logs
    assert "topsecret" not in logs and "user@example.com" not in logs and "protected user phrase" not in logs


def test_transient_ollama_runner_exit_is_retried_once(monkeypatch, caplog):
    request = httpx.Request("POST", "http://ollama/api/chat")
    error = httpx.Response(500, json={"error": "llama-server process has terminated: CUDA error"}, request=request)
    success = httpx.Response(200, json={"message": {"role": "assistant", "content": "Recovered."}}, request=request)

    class FakeClient:
        def __init__(self, *args, **kwargs): self.responses = [error, success]
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs): return self.responses.pop(0)

    monkeypatch.setattr(llm_provider.httpx, "Client", FakeClient)
    reply = OllamaProvider(base_url="http://ollama:11434").chat([{"role": "user", "content": "Explain Wi-Fi."}])
    assert reply["content"] == "Recovered."
    assert "status_code=500" in caplog.text
    assert "ollama_chat_retrying_after_runner_exit" in caplog.text


def test_provider_defaults_to_configured_local_qwen_model(monkeypatch):
    monkeypatch.setattr("app.agent.llm_provider.settings.ollama_base_url", "http://host.docker.internal:11434")
    monkeypatch.setattr("app.agent.llm_provider.settings.ollama_chat_model", "qwen3:8b")
    provider = OllamaProvider()
    assert provider.base_url == "http://host.docker.internal:11434"
    assert provider.model == "qwen3:8b"
