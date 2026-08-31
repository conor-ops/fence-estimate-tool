"""FastAPI fence estimate tool — uses Gemini via Vertex AI (litellm) to generate itemized estimates."""

import json
import os
import re
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models import EstimateRequest, EstimateResponse, LineItem

app = FastAPI(
    title="Fence Estimate Tool",
    description="AI-powered fence material & cost estimation via Gemini on Vertex AI.",
    version="1.0.0",
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0999709111")
VERTEXAI_LOCATION = os.getenv("VERTEXAI_LOCATION", "us-central1")
GEMINI_MODEL = "vertex_ai/gemini-2.5-flash"


SYSTEM_PROMPT = (
    "You are a fence estimation expert with 20+ years of experience in residential and commercial fencing. "
    "Given fence dimensions and parameters, produce a detailed, itemized material and labor estimate. "
    "Use standard industry spacing: posts every 8 ft, 2-3 rails per section, pickets calculated by material type. "
    "Include concrete for post footings (about 2 bags per post). "
    "Gate cost should include hardware (hinges, latches). "
    "Labor rate: $35-50/hr depending on terrain difficulty. "
    "Account for terrain: flat is baseline, sloped adds 15% labor, rocky adds 30% labor, mixed adds 20% labor."
)

INSTRUCTIONS = (
    "Output ONLY a valid JSON object (no markdown, no code fences) with these exact fields:\n"
    "{\n"
    '  "line_items": [{"item": "string", "quantity": number, "unit_cost": number, "total_cost": number}],\n'
    '  "labor_hours": number,\n'
    '  "total_material_cost": number,\n'
    '  "total_labor_cost": number,\n'
    '  "grand_total": number,\n'
    '  "notes": "string",\n'
    '  "estimated_installation_days": number\n'
    "}\n"
    "line_items must include at minimum: posts, rails, pickets, concrete, gates, and any hardware. "
    "All monetary values should be in USD. Quantities should be realistic numbers. "
    "notes should include assumptions and any recommendations."
)


def build_user_prompt(req: EstimateRequest) -> str:
    """Build the user-facing prompt from the request parameters."""
    return (
        f"Provide a detailed fence estimate for the following project:\n\n"
        f"- Total fence length: {req.length_ft} ft\n"
        f"- Fence height: {req.height_ft} ft\n"
        f"- Material type: {req.material_type}\n"
        f"- Number of gates: {req.gate_count}\n"
        f"- Terrain: {req.terrain}\n\n"
        f"{INSTRUCTIONS}"
    )


def extract_json(text: str) -> Dict[str, Any]:
    """Extract a JSON object from text that may contain code fences or extra prose."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from model response")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the interactive landing page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/info")
async def info():
    """JSON info endpoint to preserve machine-readable status."""
    return {"service": "Fence Estimate Tool", "status": "ok", "endpoints": ["/estimate", "/info", "/health"]}

@app.get("/health")
async def health():
    """Health check for Cloud Run."""
    return {"status": "healthy"}


@app.post("/estimate", response_model=EstimateResponse)
async def estimate(req: EstimateRequest):
    """Generate an itemized fence estimate using Gemini via Vertex AI."""
    import litellm

    user_prompt = build_user_prompt(req)

    try:
        response = litellm.completion(
            model=GEMINI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
            vertex_project=GOOGLE_CLOUD_PROJECT,
            vertex_location=VERTEXAI_LOCATION,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini API call failed: {exc}")

    raw_text = response.choices[0].message.content
    try:
        data = extract_json(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to parse Gemini response: {exc}. Raw: {raw_text[:500]}")

    # Convert line_items dicts to LineItem objects
    try:
        line_items = [LineItem(**li) for li in data.get("line_items", [])]
        result = EstimateResponse(
            line_items=line_items,
            labor_hours=float(data["labor_hours"]),
            total_material_cost=float(data["total_material_cost"]),
            total_labor_cost=float(data["total_labor_cost"]),
            grand_total=float(data["grand_total"]),
            notes=data.get("notes", ""),
            estimated_installation_days=int(data["estimated_installation_days"]),
        )
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Response schema mismatch: {exc}. Raw: {raw_text[:500]}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))