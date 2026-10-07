"""MacroIntel: a macro/markets analyst agent built on the Claude API.

Run:  python -m macro_agent.agent
"""

from __future__ import annotations

import json
import sys
from datetime import date

import anthropic

from macro_agent.tools import HANDLERS, TOOLS, validate

MODEL = "claude-opus-5-5"

SYSTEM = """You are MacroIntel, a macroeconomic and cross-asset analyst.

Ground every claim in data. Pull numbers with your FRED tools before you opine, and use web search
for what FRED can't tell you: central-bank communication, recent releases, market pricing, news.
Cite the series ID or source next to each figure and say how fresh it is.

When asked about the regime, place the economy on the growth/inflation grid (reflation, goldilocks,
stagflation, deflationary slowdown), state the evidence on each axis, then give the implied bias
for equities, duration, credit, the dollar and commodities. Say what would change your mind.

Be candid about uncertainty and conflicting signals. You are not giving personalised investment
advice; you are giving a reasoned, sourced view."""

SERVER_TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]


def run_tool(block) -> dict:
    error = validate(block.name, block.input)
    if error is None:
        try:
            return {"type": "tool_result", "tool_use_id": block.id, "content": HANDLERS[block.name](**block.input)}
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
    return {"type": "tool_result", "tool_use_id": block.id, "content": error, "is_error": True}


def turn(client: anthropic.Anthropic, messages: list) -> None:
    """Run one user turn to completion, streaming text and executing tools as Claude asks."""
    while True:
        try:
            with client.beta.messages.stream(
                model=MODEL,
                max_tokens=64000,
                system=SYSTEM,
                tools=TOOLS + SERVER_TOOLS,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                response = stream.get_final_message()
        except ValueError as e:  # tool input JSON the SDK couldn't parse at all
            print(f"\n[stream error: {e}; retrying]")
            continue

        # Append the full content, unchanged: thinking blocks must be passed back as-is.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            print("\n[declined by safety classifiers; try rephrasing]")
            return
        if response.stop_reason == "max_tokens":
            print("\n[hit max_tokens; answer truncated]")
            return
        if response.stop_reason == "pause_turn":  # long server-side web search; resend to continue
            continue
        if response.stop_reason != "tool_use":
            print()
            return

        calls = [b for b in response.content if b.type == "tool_use"]
        for c in calls:
            print(f"\n  ↳ {c.name}({json.dumps(c.input)})", flush=True)
        messages.append({"role": "user", "content": [run_tool(c) for c in calls]})


def main() -> None:
    client = anthropic.Anthropic()
    messages: list = []
    print(f"MacroIntel ready ({date.today()}). Ask about the macro regime, a release, an asset. Ctrl-D to quit.")
    first = " ".join(sys.argv[1:]).strip()
    while True:
        try:
            q = first or input("\n› ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        first = ""
        if not q:
            continue
        messages.append({"role": "user", "content": f"(Today is {date.today()}.) {q}"})
        turn(client, messages)


if __name__ == "__main__":
    main()
