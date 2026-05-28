# Copyright Advanced Micro Devices, Inc.
#
# SPDX-License-Identifier: MIT

import uuid
from urllib.parse import quote

from app.db.models import Campaign, CampaignExport
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/campaigns", tags=["exports"])


@router.post("/{campaign_id}/export")
async def trigger_export(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a ZIP export of all campaign assets."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    from app.workers.tasks.export import export_campaign

    task = export_campaign.delay(str(campaign_id))
    return {"task_id": task.id, "status": "started"}


@router.get("/{campaign_id}/exports")
async def list_exports(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all completed exports for a campaign."""
    result = await db.execute(
        select(CampaignExport)
        .where(CampaignExport.campaign_id == campaign_id)
        .order_by(CampaignExport.created_at.desc())
    )
    exports = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "asset_url": e.asset_url,
            "download_url": f"/backend/api/assets/download?asset_url={quote(e.asset_url, safe='')}",
            "format": e.format,
            "created_at": e.created_at.isoformat(),
        }
        for e in exports
    ]
