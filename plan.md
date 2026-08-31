1. Explore current code state.
2. The HTML/CSS/JS template was already moved to `templates/index.html` by PR 3.
3. Address the second review comment: add a dedicated JSON info endpoint (e.g., `/info`) that returns the original JSON info: `{"service": "Fence Estimate Tool", "status": "ok", "endpoints": ["/estimate", "/info", "/health"]}` or something similar.
