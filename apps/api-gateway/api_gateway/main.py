from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(
    title="AeroCalc & DFM Analyzer API",
    description="Modular API Gateway for Aerospace Calculations and Manufacturing Analysis",
    version="1.0.0"
)

# Configure CORS. Auth uses a Bearer token in the Authorization header, not
# cookies, so allow_credentials is not needed - and per the CORS spec browsers
# reject allow_origins=["*"] combined with allow_credentials=True outright
# (every cross-origin request fails preflight). Keep these mutually exclusive.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify domains
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api_gateway.routers import aero, dfm, propulsion, auth, projects, aircraft

# Include Routers
app.include_router(aero.router)
app.include_router(dfm.router)
app.include_router(propulsion.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(aircraft.router)

@app.get("/")
def root():
    return {"message": "AeroCalc & DFM Analyzer API Gateway is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
