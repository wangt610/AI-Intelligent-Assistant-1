import logging

from fastapi import APIRouter

from runtime_config import RuntimeSettingsStore
from models.schemas import RuntimeSettingsResponse, RuntimeSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=RuntimeSettingsResponse)
async def get_runtime_settings():
    data = RuntimeSettingsStore.all()
    return RuntimeSettingsResponse(**data)


@router.put("", response_model=RuntimeSettingsResponse)
async def update_runtime_settings(body: RuntimeSettingsUpdate):
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        RuntimeSettingsStore.set(key, value)
    if updates:
        logger.info("运行时配置更新: %s", ", ".join(updates.keys()))
        RuntimeSettingsStore.save()
    data = RuntimeSettingsStore.all()
    return RuntimeSettingsResponse(**data)
