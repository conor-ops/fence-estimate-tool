"""FastAPI fence estimate tool — uses Gemini via Vertex AI (litellm) to generate itemized estimates."""

import json
import os
import re
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from models import EstimateRequest, EstimateResponse, LineItem

app = FastAPI(
    title="Fence Estimate Tool",
    description="AI-powered fence material & cost estimation via Gemini on Vertex AI.",
    version="1.0.0",
)

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

LANDING_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>208 Fence and Gate | Original Fence Estimates</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: rgba(15, 23, 42, 0.88);
      --panel-strong: rgba(30, 41, 59, 0.95);
      --line: rgba(148, 163, 184, 0.2);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #f59e0b;
      --accent-2: #38bdf8;
      --good: #22c55e;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, Arial, sans-serif;
      background:
        radial-gradient(circle at top, rgba(56, 189, 248, 0.18), transparent 32%),
        radial-gradient(circle at right, rgba(245, 158, 11, 0.22), transparent 28%),
        linear-gradient(180deg, #020617 0%, var(--bg) 100%);
      color: var(--text);
      min-height: 100vh;
    }
    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }
    .badge, .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.72);
    }
    .badge { padding: 10px 16px; }
    .pill { padding: 8px 12px; }
    .hero {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 24px;
      align-items: stretch;
      margin-top: 28px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      backdrop-filter: blur(12px);
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
    }
    h1 {
      font-size: clamp(2.5rem, 6vw, 5rem);
      line-height: 0.96;
      letter-spacing: -0.06em;
      margin: 18px 0;
    }
    p {
      color: var(--muted);
      line-height: 1.6;
      margin: 0;
    }
    .hero-copy p {
      font-size: 1.05rem;
      max-width: 60ch;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 24px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 14px 18px;
      border-radius: 14px;
      border: 1px solid transparent;
      font-weight: 700;
      text-decoration: none;
      transition: transform 0.2s ease, opacity 0.2s ease;
    }
    .btn:hover { transform: translateY(-1px); }
    .btn-primary {
      background: linear-gradient(135deg, var(--accent), #fb7185);
      color: #111827;
    }
    .btn-secondary {
      border-color: var(--line);
      color: var(--text);
      background: rgba(15, 23, 42, 0.45);
    }
    .hero-grid, .stats-grid {
      display: grid;
      gap: 14px;
    }
    .hero-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 22px; }
    .stats-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 18px; }
    .stat {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
    }
    .stat strong {
      display: block;
      font-size: 1.5rem;
      margin-top: 8px;
    }
    .calculator label {
      display: block;
      font-size: 0.94rem;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .field { margin-bottom: 18px; }
    input[type="range"], select {
      width: 100%;
      accent-color: var(--accent);
    }
    select {
      background: var(--panel-strong);
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px;
    }
    .fine {
      font-size: 0.9rem;
      color: var(--muted);
      margin-top: 12px;
    }
    .footer-note {
      margin-top: 24px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
    @media (max-width: 920px) {
      .hero { grid-template-columns: 1fr; }
      .hero-grid, .stats-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <div class="badge">🪵 Built by 208 Fence and Gate · Original workflow energy only</div>

    <section class="hero">
      <div class="panel hero-copy">
        <span class="pill">⚡ FastAPI + Gemini on Vertex AI</span>
        <h1>Fence estimates with backbone.</h1>
        <p>
          Welcome to the fence tool with enough personality to measure a yard, price the rails,
          and gently side-eye any suspiciously familiar “innovations” drifting through search ads.
        </p>
        <div class="hero-grid">
          <div class="stat">
            <span>Originality rating</span>
            <strong>100%</strong>
            <p>Fresh boards. Fresh workflow. Zero copycat seasoning.</p>
          </div>
          <div class="stat">
            <span>Comedic relief</span>
            <strong>Heavy</strong>
            <p>Because sometimes the most professional move is a perfectly timed eyebrow raise.</p>
          </div>
        </div>
        <div class="actions">
          <a class="btn btn-primary" href="/docs">Launch the API docs</a>
          <a class="btn btn-secondary" href="/health">Health check</a>
        </div>
        <div class="footer-note">
          <span class="pill">📐 Real estimate API at <code>POST /estimate</code></span>
          <span class="pill">🛡️ Copycats remain outside the gate</span>
        </div>
      </div>

      <div class="panel calculator">
        <h2>Interactive hype builder</h2>
        <p>Drag a few controls and watch the landing page riff in real time.</p>

        <div class="field">
          <label for="length">Fence length: <strong id="lengthValue">120 ft</strong></label>
          <input id="length" type="range" min="40" max="400" step="10" value="120" />
        </div>

        <div class="field">
          <label for="height">Fence height: <strong id="heightValue">6 ft</strong></label>
          <input id="height" type="range" min="4" max="8" step="1" value="6" />
        </div>

        <div class="field">
          <label for="gates">Gates: <strong id="gatesValue">1</strong></label>
          <input id="gates" type="range" min="0" max="4" step="1" value="1" />
        </div>

        <div class="field">
          <label for="terrain">Terrain</label>
          <select id="terrain">
            <option value="flat">Flat</option>
            <option value="sloped">Sloped</option>
            <option value="rocky">Rocky</option>
            <option value="mixed">Mixed</option>
          </select>
        </div>

        <div class="stats-grid">
          <div class="stat">
            <span>Estimated posts</span>
            <strong id="postsValue">16</strong>
          </div>
          <div class="stat">
            <span>Preview rails</span>
            <strong id="railsValue">45</strong>
          </div>
          <div class="stat">
            <span>Copycat pressure</span>
            <strong id="moodValue">Mild</strong>
          </div>
        </div>

        <p class="fine" id="quip">
          Crisp layout. Clean math. The kind of workflow people tend to “admire” from a distance.
        </p>
      </div>
    </section>
  </main>

  <script>
    const length = document.getElementById("length");
    const height = document.getElementById("height");
    const gates = document.getElementById("gates");
    const terrain = document.getElementById("terrain");

    const lengthValue = document.getElementById("lengthValue");
    const heightValue = document.getElementById("heightValue");
    const gatesValue = document.getElementById("gatesValue");
    const postsValue = document.getElementById("postsValue");
    const railsValue = document.getElementById("railsValue");
    const moodValue = document.getElementById("moodValue");
    const quip = document.getElementById("quip");

    const quips = {
      flat: "Flat terrain: smooth install, smooth operator, smooth little grin.",
      sloped: "Sloped terrain: still classy, just with more contour and more dramatic music.",
      rocky: "Rocky terrain: for when the ground fights back but the estimate stays composed.",
      mixed: "Mixed terrain: a little chaos, a lot of confidence, zero borrowed ideas."
    };

    function update() {
      const lengthFt = Number(length.value);
      const heightFt = Number(height.value);
      const gateCount = Number(gates.value);
      const estimatedPosts = Math.ceil(lengthFt / 8) + 1 + gateCount;
      const estimatedRails = Math.ceil(lengthFt / 8) * (heightFt >= 6 ? 3 : 2);

      lengthValue.textContent = `${lengthFt} ft`;
      heightValue.textContent = `${heightFt} ft`;
      gatesValue.textContent = String(gateCount);
      postsValue.textContent = String(estimatedPosts);
      railsValue.textContent = String(estimatedRails);

      const moodScore = estimatedPosts + estimatedRails + gateCount * 4;
      moodValue.textContent = moodScore > 80 ? "Intense" : moodScore > 55 ? "Spicy" : "Mild";
      quip.textContent = quips[terrain.value];
    }

    [length, height, gates].forEach((element) => {
      element.addEventListener("input", update);
    });
    terrain.addEventListener("change", update);

    update();
  </script>
</body>
</html>
"""


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
async def root():
    """Serve the interactive landing page."""
    return LANDING_PAGE_HTML


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