from typing import Any, Dict

import httpx
from pydantic import ValidationError

from .config import API_GATEWAY_URL
from .llm_client import structured_chat
from .schemas import MultirotorConfigProposal, SolveProposal, SolveResponse

SYSTEM_PROMPT = """You are an expert multirotor drone design engineer. Given a plain-English \
goal, propose a concrete set of physical component parameters (frame, motor, propeller, \
battery, ESC, flight controller, weights). You do NOT compute performance yourself - a \
deterministic physics engine will simulate your proposed parameters and return the real \
numbers. Use realistic, commercially-available component values (typical motor KV ranges \
1000-2700 for small multirotors, standard prop sizes in inches, standard LiPo cell/capacity \
combinations). Respond only with the requested JSON structure."""


async def _propose_config(goal: str, retry_error: str = None) -> SolveProposal:
    user_prompt = f"Design goal: {goal}"
    if retry_error:
        user_prompt += (
            f"\n\nYour previous proposal was invalid: {retry_error}\n"
            "Fix the proposal and respond again with the full corrected JSON structure."
        )

    raw = await structured_chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_schema=SolveProposal.model_json_schema(),
    )
    return SolveProposal.model_validate(raw)


async def _run_multirotor_simulation(config: MultirotorConfigProposal) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/aero/multirotor",
            json=config.model_dump(),
        )
        response.raise_for_status()
        return response.json()


async def solve_multirotor(goal: str) -> SolveResponse:
    try:
        proposal = await _propose_config(goal)
    except (ValidationError, ValueError) as e:
        try:
            proposal = await _propose_config(goal, retry_error=str(e))
        except (ValidationError, ValueError) as e2:
            return SolveResponse(
                reasoning="",
                proposed_config={},
                error=f"AI proposed an invalid configuration twice: {e2}",
            )

    try:
        results = await _run_multirotor_simulation(proposal.proposed_config)
    except httpx.HTTPStatusError as e:
        return SolveResponse(
            reasoning=proposal.reasoning,
            proposed_config=proposal.proposed_config.model_dump(),
            error=f"Simulation rejected the proposed config: {e.response.text}",
        )
    except httpx.HTTPError as e:
        return SolveResponse(
            reasoning=proposal.reasoning,
            proposed_config=proposal.proposed_config.model_dump(),
            error=f"Could not reach the simulation engine: {e}",
        )

    target_met = None
    notes = None
    required = proposal.proposed_config.required_flight_time
    if required and required > 0:
        achieved = results.get("cruise_flight_time_min") or results.get("max_flight_time_min")
        if achieved is not None:
            target_met = achieved >= required
            notes = (
                f"Target flight time of {required:.0f} min "
                + ("met" if target_met else "not met")
                + f" (simulated: {achieved:.1f} min)."
            )

    return SolveResponse(
        reasoning=proposal.reasoning,
        proposed_config=proposal.proposed_config.model_dump(),
        simulated_results=results,
        target_met=target_met,
        notes=notes,
    )
