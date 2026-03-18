"""Session logger for Gemini Live API test sessions.

Captures every message field to JSONL for post-hoc analysis.
Each line is a JSON object with timestamp, message index, and
all non-None fields from the LiveServerMessage.

Usage:
    from session_logger import SessionLogger

    logger = SessionLogger("output/logs/test_001.jsonl")
    async for msg in session.receive():
        logger.log(msg)
        ...
    logger.close()
"""

import json
import time
from pathlib import Path
from typing import Optional


class SessionLogger:
    """Logs Live API messages to JSONL."""

    def __init__(self, path: str, metadata: Optional[dict] = None):
        """Initialize logger.

        Args:
            path: Output JSONL file path.
            metadata: Optional dict written as first line (session config, etc.)
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, "w")
        self.msg_count = 0
        self.start_time = time.monotonic()

        if metadata:
            self._write({"type": "session_metadata", **metadata})

    def log(self, msg) -> dict:
        """Log a LiveServerMessage. Returns the parsed dict."""
        self.msg_count += 1
        elapsed = time.monotonic() - self.start_time

        entry = {
            "type": "message",
            "index": self.msg_count,
            "elapsed_sec": round(elapsed, 3),
        }

        # server_content
        sc = msg.server_content
        if sc:
            entry["has_server_content"] = True

            if sc.model_turn:
                parts = []
                for p in sc.model_turn.parts:
                    if p.text:
                        parts.append({"type": "text", "text": p.text})
                    if p.inline_data:
                        parts.append({
                            "type": "audio",
                            "bytes": len(p.inline_data.data),
                            "mime_type": getattr(p.inline_data, "mime_type", None),
                        })
                if parts:
                    entry["model_turn_parts"] = parts

            if sc.turn_complete:
                entry["turn_complete"] = True

            if sc.generation_complete:
                entry["generation_complete"] = True

            if sc.interrupted:
                entry["interrupted"] = True

            if hasattr(sc, "output_transcription") and sc.output_transcription:
                t = sc.output_transcription
                if hasattr(t, "text") and t.text:
                    entry["output_transcription"] = t.text
                if hasattr(t, "finished") and t.finished is not None:
                    entry["transcription_finished"] = t.finished

            if hasattr(sc, "input_transcription") and sc.input_transcription:
                t = sc.input_transcription
                if hasattr(t, "text") and t.text:
                    entry["input_transcription"] = t.text

            if hasattr(sc, "turn_complete_reason") and sc.turn_complete_reason:
                entry["turn_complete_reason"] = str(sc.turn_complete_reason)

            if hasattr(sc, "waiting_for_input") and sc.waiting_for_input:
                entry["waiting_for_input"] = True

        # tool_call
        if msg.tool_call:
            entry["tool_call"] = True
            calls = []
            for fc in msg.tool_call.function_calls:
                calls.append({
                    "name": fc.name,
                    "args": dict(fc.args) if fc.args else {},
                    "id": fc.id,
                })
            entry["function_calls"] = calls

        # tool_call_cancellation
        if msg.tool_call_cancellation:
            entry["tool_call_cancellation"] = True
            if msg.tool_call_cancellation.ids:
                entry["cancelled_tool_ids"] = msg.tool_call_cancellation.ids

        # usage_metadata
        if msg.usage_metadata:
            um = msg.usage_metadata
            usage = {}
            for field in ["prompt_token_count", "response_token_count",
                          "total_token_count", "thoughts_token_count",
                          "tool_use_prompt_token_count", "cached_content_token_count"]:
                val = getattr(um, field, None)
                if val is not None:
                    usage[field] = val
            if usage:
                entry["usage_metadata"] = usage

        # voice activity
        if msg.voice_activity:
            entry["voice_activity"] = str(msg.voice_activity)

        if msg.voice_activity_detection_signal:
            entry["vad_signal"] = str(msg.voice_activity_detection_signal)

        # session resumption
        if msg.session_resumption_update:
            entry["session_resumption"] = True

        # go_away
        if msg.go_away:
            entry["go_away"] = True

        self._write(entry)
        return entry

    def log_event(self, event_type: str, **kwargs):
        """Log a custom event (user action, injection, etc.)."""
        elapsed = time.monotonic() - self.start_time
        entry = {
            "type": event_type,
            "elapsed_sec": round(elapsed, 3),
            **kwargs,
        }
        self._write(entry)

    def _write(self, entry: dict):
        self.f.write(json.dumps(entry) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
