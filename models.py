"""Pydantic models for fence estimate requests and responses."""

from typing import List, Optional

from pydantic import BaseModel, Field


class EstimateRequest(BaseModel):
    """Request model for fence estimation."""

    length_ft: float = Field(..., gt=0, description="Total fence length in feet")
    height_ft: float = Field(..., gt=0, description="Fence height in feet")
    material_type: str = Field(..., description="Fence material (e.g., cedar, vinyl, chain-link, aluminum)")
    gate_count: int = Field(..., ge=0, description="Number of gates")
    terrain: str = Field("flat", description="Terrain type (flat, sloped, rocky, mixed)")


class LineItem(BaseModel):
    """A single line item in the estimate."""

    item: str
    quantity: float
    unit_cost: float
    total_cost: float


class EstimateResponse(BaseModel):
    """Response model for fence estimation."""

    line_items: List[LineItem]
    labor_hours: float
    total_material_cost: float
    total_labor_cost: float
    grand_total: float
    notes: str
    estimated_installation_days: int