# Created by Metrum AI for AMD

import uuid

from app.db.models import Brand
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/brands", tags=["brands"])


class BrandCreate(BaseModel):
    """Request body for creating a new brand."""

    user_id: uuid.UUID
    name: str
    logo_url: str | None = None
    colors: dict = {}
    fonts: dict = {}
    reference_images: list[str] = []


class BrandUpdate(BaseModel):
    """Request body for partial brand updates."""

    name: str | None = None
    logo_url: str | None = None
    colors: dict | None = None
    fonts: dict | None = None
    reference_images: list[str] | None = None


class BrandOut(BaseModel):
    """Serialised brand returned by the API."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    logo_url: str | None
    colors: dict
    fonts: dict
    reference_images: list[str]


@router.post("", response_model=BrandOut, status_code=201)
async def create_brand(body: BrandCreate, db: AsyncSession = Depends(get_db)):
    """Persist a new brand and return it."""
    brand = Brand(**body.model_dump())
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


@router.get("", response_model=list[BrandOut])
async def list_brands(
    user_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return all brands, optionally filtered by user_id."""
    stmt = select(Brand).order_by(Brand.created_at.desc())
    if user_id:
        stmt = stmt.where(Brand.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{brand_id}", response_model=BrandOut)
async def get_brand(brand_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetch a single brand by primary key."""
    brand = await db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    return brand


@router.put("/{brand_id}", response_model=BrandOut)
async def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Apply partial updates to an existing brand."""
    brand = await db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(brand, key, val)

    await db.commit()
    await db.refresh(brand)
    return brand


@router.delete("/{brand_id}", status_code=204)
async def delete_brand(
    brand_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """Delete a brand by primary key."""
    brand = await db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    await db.delete(brand)
    await db.commit()
