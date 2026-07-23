"""
title: Save to Journal
author: going-analogue homelab
author_url: https://github.com/going-analogue
version: 0.1.0
license: MIT
description: Adds a "Save to Journal" button under a chat message that POSTs the current
    coaching conversation into Memos as a #journal entry. Saving this way intentionally
    re-enters the n8n "journal-analyze" loop, so the saved memo receives a reflection comment.
required_open_webui_version: 0.5.0
"""

# Open WebUI *Action* Function (a class named `Action` with an async `action` method makes
# this an action button, rendered under each assistant message).
#
# Anti-drift: this file is the source of truth. It is INSTALLED into the rig Open WebUI via
# POST /api/v1/functions/create (id "save_to_journal"), then toggled active and given its
# MEMOS_TOKEN valve from vault journaling.memos.api_token. The Memos base URL + token are
# read from Valves (never hardcoded); defaults point at the mini's Memos over the LAN.
#
# Memos 0.29 create-memo API (verified journal-05): POST {base}/api/v1/memos with body
# {"content","visibility"} and Bearer PAT -> 200 {"name":"memos/<uid>", ...}. Memos parses
# hashtags out of the content, so a leading "#journal" is enough to arm the n8n webhook.

import json
import requests
from pydantic import BaseModel, Field


class Action:
    class Valves(BaseModel):
        MEMOS_BASE_URL: str = Field(
            default="http://192.168.10.2:5230",
            description="Base URL of the Memos instance (the mini over the LAN by default; "
            "https://memos.tabaska.us also works over the tailnet).",
        )
        MEMOS_TOKEN: str = Field(
            default="",
            description="Memos personal access token (vault journaling.memos.api_token). "
            "Set this in the function's valves; never commit the value.",
        )
        JOURNAL_TAGS: str = Field(
            default="#journal",
            description="Hashtags prepended to the saved memo. Must include #journal so the "
            "n8n journal-analyze webhook picks it up.",
        )
        VISIBILITY: str = Field(
            default="PRIVATE",
            description="Memo visibility: PRIVATE, PROTECTED, or PUBLIC.",
        )
        INCLUDE_COACH_TURNS: bool = Field(
            default=True,
            description="Include the coach's (assistant) replies in the saved transcript. "
            "Turn off to save only your own words.",
        )
        TIMEOUT: int = Field(
            default=15, description="HTTP timeout (seconds) for the Memos call."
        )

    def __init__(self):
        self.valves = self.Valves()

    def _text(self, content) -> str:
        """Flatten a message content that may be a string or a multimodal parts list."""
        if isinstance(content, list):
            parts = [
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            return " ".join(parts).strip()
        return (content or "").strip()

    async def action(
        self,
        body: dict,
        __user__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> None:
        async def status(description: str, done: bool = False, err: bool = False):
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": description,
                            "done": done,
                            "status": "error" if err else ("complete" if done else "in_progress"),
                        },
                    }
                )

        async def toast(content: str, kind: str = "success"):
            if __event_emitter__:
                await __event_emitter__(
                    {"type": "notification", "data": {"type": kind, "content": content}}
                )

        token = (self.valves.MEMOS_TOKEN or "").strip()
        if not token:
            await status("Save to Journal: MEMOS_TOKEN valve is not set.", done=True, err=True)
            await toast("Save to Journal: MEMOS_TOKEN valve is not set.", "error")
            return

        await status("Saving this conversation to your journal…")

        messages = body.get("messages", []) or []
        lines = []
        for m in messages:
            role = m.get("role")
            text = self._text(m.get("content"))
            if not text:
                continue
            if role == "user":
                lines.append(f"**Me:** {text}")
            elif role == "assistant" and self.valves.INCLUDE_COACH_TURNS:
                lines.append(f"**Coach:** {text}")

        if not lines:
            await status("Nothing to save — the conversation is empty.", done=True, err=True)
            await toast("Nothing to save — the conversation is empty.", "warning")
            return

        tags = (self.valves.JOURNAL_TAGS or "").strip()
        if "#journal" not in tags.split():
            tags = ("#journal " + tags).strip()

        memo = f"{tags}\n\n_🪞 Journaling Coach session_\n\n" + "\n\n".join(lines)
        base = self.valves.MEMOS_BASE_URL.rstrip("/")

        try:
            resp = requests.post(
                f"{base}/api/v1/memos",
                data=json.dumps({"content": memo, "visibility": self.valves.VISIBILITY}),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=self.valves.TIMEOUT,
            )
            resp.raise_for_status()
            name = ""
            try:
                name = resp.json().get("name", "")
            except Exception:
                pass
            label = name or "your journal"
            await status(
                f"Saved to {label}. A reflection comment will appear shortly.",
                done=True,
            )
            await toast(f"Saved to Journal ({label}).", "success")
        except Exception as e:
            await status(f"Save to Journal failed: {e}", done=True, err=True)
            await toast(f"Save to Journal failed: {e}", "error")

        return
