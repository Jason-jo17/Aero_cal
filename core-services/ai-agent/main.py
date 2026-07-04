from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai_agent.design_review import get_design_review
from ai_agent.schemas import DesignReviewRequest, DesignReviewResponse, SolveRequest, SolveResponse
from ai_agent.solve import solve_multirotor

app = FastAPI(title="AI Agent Service for AeroCalc Suite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ai/design-review", response_model=DesignReviewResponse)
async def design_review(request: DesignReviewRequest):
    try:
        summary = await get_design_review(request)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI provider error: {e}")
    return DesignReviewResponse(summary=summary)


@app.post("/ai/solve", response_model=SolveResponse)
async def solve(request: SolveRequest):
    if request.domain == "multirotor":
        return await solve_multirotor(request.goal)
    raise HTTPException(status_code=400, detail=f"Unsupported domain: {request.domain}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
