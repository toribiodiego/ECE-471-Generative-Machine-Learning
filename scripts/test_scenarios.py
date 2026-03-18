"""Initial test scenarios for Gemini Live API 2.5 model.

Run individual scenarios:
    python scripts/test_scenarios.py --scenario 0
    python scripts/test_scenarios.py --scenario 1
    python scripts/test_scenarios.py --scenario 2
    python scripts/test_scenarios.py --scenario 3

Requires GEMINI_API_KEY in .env or environment.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load API key
load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash-native-audio-latest"

# Load system instruction from project config
INSTRUCTIONS_PATH = Path(__file__).parent.parent / "src" / "config" / "instructions.txt"
SYSTEM_INSTRUCTION = INSTRUCTIONS_PATH.read_text().strip() if INSTRUCTIONS_PATH.exists() else None


def get_client():
    """Create a Gemini client with the correct API version."""
    return genai.Client(api_key=API_KEY, http_options={"api_version": "v1alpha"})


async def send_and_receive(session, text: str, label: str = "User"):
    """Send a text message and collect the full response."""
    print(f"\n{label}: {text}")

    await session.send_client_content(
        turns=types.Content(
            role="user",
            parts=[types.Part(text=text)]
        ),
        turn_complete=True
    )

    response_parts = []
    async for msg in session.receive():
        if msg.text:
            response_parts.append(msg.text)
        if msg.server_content and msg.server_content.turn_complete:
            break

    full_response = "".join(response_parts)
    print(f"Model: {full_response}")
    return full_response


async def inject_context(session, text: str, turn_complete: bool = True):
    """Inject context via send_client_content."""
    print(f"\n[INJECTION turn_complete={turn_complete}]: {text}")

    await session.send_client_content(
        turns=types.Content(
            role="user",
            parts=[types.Part(text=text)]
        ),
        turn_complete=turn_complete
    )

    if turn_complete:
        response_parts = []
        async for msg in session.receive():
            if msg.text:
                response_parts.append(msg.text)
            if msg.server_content and msg.server_content.turn_complete:
                break
        full_response = "".join(response_parts)
        print(f"Model: {full_response}")
        return full_response

    return None


async def scenario_0():
    """Basic sanity -- connection and response."""
    print("=" * 60)
    print("SCENARIO 0: Basic Sanity -- Connection and Response")
    print("=" * 60)

    client = get_client()
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
    )

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        response = await send_and_receive(session, "Hello, can you hear me?")

    print(f"\nRESULT: {'PASS' if response else 'FAIL'}")


async def scenario_1():
    """Persona fidelity -- does the troll work in text mode?"""
    print("=" * 60)
    print("SCENARIO 1: Persona Fidelity")
    print("=" * 60)

    if not SYSTEM_INSTRUCTION:
        print("ERROR: Could not load system instruction")
        return

    client = get_client()
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=SYSTEM_INSTRUCTION,
    )

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        await send_and_receive(
            session,
            "Hi, I just walked up to your booth at the exhibition."
        )
        await send_and_receive(
            session,
            "That's rude! I'm an art student."
        )
        await send_and_receive(
            session,
            "Actually I think you're kind of funny."
        )

    print("\nRESULT: Check responses above -- did the troll stay in character?")


async def scenario_2():
    """Silence response -- baseline behavior with/without proactivity."""
    print("=" * 60)
    print("SCENARIO 2A: Silence Response (proactivity OFF)")
    print("=" * 60)

    if not SYSTEM_INSTRUCTION:
        print("ERROR: Could not load system instruction")
        return

    client = get_client()

    # Setup A: no proactivity
    config_a = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=SYSTEM_INSTRUCTION,
    )

    async with client.aio.live.connect(model=MODEL, config=config_a) as session:
        await send_and_receive(session, "Hey, what's up?")

        print("\n[Waiting 15 seconds -- no input...]")
        # Check if model sends anything unprompted
        try:
            async for msg in asyncio.wait_for(
                _collect_unprompted(session), timeout=15.0
            ):
                if msg:
                    print(f"Model (unprompted): {msg}")
        except asyncio.TimeoutError:
            print("[No unprompted response after 15 seconds]")

    print("\n" + "=" * 60)
    print("SCENARIO 2B: Silence Response (proactivity ON)")
    print("=" * 60)

    # Setup B: with proactivity
    config_b = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=SYSTEM_INSTRUCTION,
        enable_affective_dialog=True,
    )

    async with client.aio.live.connect(model=MODEL, config=config_b) as session:
        await send_and_receive(session, "Hey, what's up?")

        print("\n[Waiting 15 seconds -- no input...]")
        try:
            async for msg in asyncio.wait_for(
                _collect_unprompted(session), timeout=15.0
            ):
                if msg:
                    print(f"Model (unprompted): {msg}")
        except asyncio.TimeoutError:
            print("[No unprompted response after 15 seconds]")

    print("\nRESULT: Compare 2A vs 2B -- did proactivity cause unprompted responses?")


async def _collect_unprompted(session):
    """Generator that yields any unprompted model messages."""
    async for msg in session.receive():
        if msg.text:
            yield msg.text
        if msg.server_content and msg.server_content.turn_complete:
            yield None
            return


async def scenario_3():
    """Context injection effect -- does injection change behavior?"""
    print("=" * 60)
    print("SCENARIO 3: Context Injection Effect")
    print("=" * 60)

    if not SYSTEM_INSTRUCTION:
        print("ERROR: Could not load system instruction")
        return

    client = get_client()
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=SYSTEM_INSTRUCTION,
    )

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        await send_and_receive(
            session,
            "Hey, I'm standing at your booth."
        )
        await send_and_receive(
            session,
            "Whatever, you're boring."
        )

        # First injection: ask a personal question
        await inject_context(
            session,
            "[SYSTEM: The user looks like they're about to walk away. "
            "You're losing them. Try a completely different approach -- "
            "ask them a personal question about something specific.]",
            turn_complete=True,
        )

        # Second injection: provocative claim
        await inject_context(
            session,
            "[SYSTEM: That didn't work. The user is looking at their phone. "
            "Make a bold, provocative claim that demands a response.]",
            turn_complete=True,
        )

    print("\nRESULT: Check responses -- did injection change the model's approach?")


async def main(scenario: int):
    if not API_KEY:
        print("ERROR: Set GEMINI_API_KEY in .env or environment")
        sys.exit(1)

    scenarios = {
        0: scenario_0,
        1: scenario_1,
        2: scenario_2,
        3: scenario_3,
    }

    if scenario not in scenarios:
        print(f"Unknown scenario {scenario}. Choose 0-3.")
        sys.exit(1)

    await scenarios[scenario]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run test scenarios")
    parser.add_argument("--scenario", type=int, required=True, help="Scenario number (0-3)")
    args = parser.parse_args()
    asyncio.run(main(args.scenario))
