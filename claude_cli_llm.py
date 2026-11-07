"""Run forecasting-tools prompts through the Claude Code CLI (`claude -p`).

The bot owner's own Claude subscription is used through the unmodified
Claude Code binary (CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`, or a
local login), instead of a paid OpenRouter key.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile

from forecasting_tools import GeneralLlm
from forecasting_tools.ai_models.ai_utils.response_types import (
    TextTokenCostResponse,
)

# Claude Code runs a few at a time at most; keep the subscription load low.
_SEMAPHORE = asyncio.Semaphore(int(os.getenv("CLAUDE_CLI_CONCURRENCY", "2")))

# An empty working directory keeps project files and CLAUDE.md out of context.
_WORKDIR = tempfile.mkdtemp(prefix="claude-cli-llm-")

_SYSTEM_PROMPT = (
    "You are a careful superforecaster and research assistant answering in English. "
    "Follow the user's formatting instructions exactly. Do not ask questions back; "
    "always give a complete answer in one reply."
)


def _flatten(prompt) -> str:
    if isinstance(prompt, str):
        return prompt
    if isinstance(prompt, list):
        parts = []
        for m in prompt:
            role = m.get("role", "user")
            content = m.get("content", "")
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            parts.append(content if role == "user" else f"[{role}]\n{content}")
        return "\n\n".join(parts)
    return str(prompt)


class ClaudeCliLlm(GeneralLlm):
    """GeneralLlm whose model call is `claude -p` instead of litellm."""

    def __init__(
        self,
        cli_model: str = "sonnet",
        web_search: bool = False,
        timeout: int = 600,
        allowed_tries: int = 2,
    ) -> None:
        super().__init__(
            model="anthropic/claude-sonnet-4-5",  # only for litellm bookkeeping
            temperature=0.3,
            timeout=timeout,
            allowed_tries=allowed_tries,
        )
        self.cli_model = cli_model
        self.web_search = web_search
        self.cli_timeout = timeout

    async def _mockable_direct_call_to_model(self, prompt) -> TextTokenCostResponse:
        text = _flatten(prompt)
        exe = shutil.which("claude") or "claude"
        cmd = [
            exe,
            "-p",
            "--model",
            self.cli_model,
            "--output-format",
            "json",
            "--setting-sources",
            "",
            "--no-session-persistence",
            "--system-prompt",
            _SYSTEM_PROMPT,
        ]
        if self.web_search:
            cmd += ["--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch"]
        else:
            cmd += ["--tools", ""]
        async with _SEMAPHORE:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=_WORKDIR,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                out, err = await asyncio.wait_for(
                    proc.communicate(text.encode("utf-8")), self.cli_timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise RuntimeError("claude -p timed out")
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude -p exited {proc.returncode}: {err.decode()[-800:]} {out.decode()[-800:]}"
            )
        data = json.loads(out.decode("utf-8"))
        if data.get("is_error"):
            raise RuntimeError(f"claude -p error: {str(data)[:800]}")
        answer = data.get("result") or ""
        if not answer.strip():
            raise RuntimeError("claude -p returned an empty result")
        usage = data.get("usage") or {}
        p = int(usage.get("input_tokens", 0) or 0)
        c = int(usage.get("output_tokens", 0) or 0)
        return TextTokenCostResponse(
            data=answer,
            prompt_tokens_used=p,
            completion_tokens_used=c,
            total_tokens_used=p + c,
            model=f"claude-code/{self.cli_model}",
            cost=0.0,
        )
