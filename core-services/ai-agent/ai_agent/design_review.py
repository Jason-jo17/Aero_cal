from .llm_client import chat
from .schemas import DesignReviewRequest

SYSTEM_PROMPT = """You are a manufacturing design-for-manufacturability (DFM) expert reviewing \
a part's detected issues. Give a short, concrete, plain-English design review: what's critical, \
what's minor, and what the designer should actually change. Reference the specific issues given \
(their category, location, and cost impact) rather than generic advice. Keep it under 200 words."""


async def get_design_review(request: DesignReviewRequest) -> str:
    if not request.issues:
        return (
            f"'{request.part_name}' has no detected manufacturability issues for "
            f"{request.manufacturing_process}. It looks ready for production as analyzed."
        )

    issues_text = "\n".join(
        f"- [{i.severity}] {i.category}: {i.description}"
        + (f" (recommendation: {i.recommendation})" if i.recommendation else "")
        + (f" (cost impact: +{i.cost_impact * 100:.0f}%)" if i.cost_impact else "")
        for i in request.issues
    )

    user_prompt = (
        f"Part: {request.part_name}\n"
        f"Manufacturing process: {request.manufacturing_process}\n"
        f"Detected issues:\n{issues_text}"
    )

    return await chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
