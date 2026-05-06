"""
Pydantic schemas for Card operations.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class OpCardCreate(BaseModel):
    """Schema for manual card creation via POST /onepiecetcg/cards/add."""

    opcar_opset_id: str = Field(..., min_length=1, description='Set ID (must exist in database)')
    opcar_id: str = Field(..., min_length=1, description='Card ID (alphanumeric)')
    opcar_version: str = Field('p0', min_length=1, description='Card version (default: p0)')
    opcar_name: str = Field(..., min_length=1, description='Card name')
    opcar_category: Optional[str] = Field(None, description='Card category (e.g. Leader, Character)')
    opcar_color: Optional[str] = Field(None, description='Card color (e.g. Red, Blue)')
    opcar_rarity: Optional[str] = Field(None, description='Card rarity (e.g. Common, Rare)')
    opcar_cost: Optional[int] = Field(None, ge=0, description='Card cost (non-negative)')
    opcar_life: Optional[int] = Field(None, description='Card life')
    opcar_power: Optional[int] = Field(None, description='Card power')
    opcar_counter: Optional[int] = Field(None, ge=0, description='Card counter (non-negative)')
    opcar_attribute: Optional[str] = Field(None, description='Card attribute')
    opcar_type: Optional[str] = Field(None, description='Card type')
    opcar_effect: Optional[str] = Field(None, description='Card effect text')
    image_src: Optional[str] = Field(None, description='Image filename')
    opcar_banned: Optional[str] = Field(None, description='Banned status (e.g. Y/N)')
    opcar_block_icon: Optional[int] = Field(None, description='Block icon number')

    @field_validator('opcar_opset_id')
    @classmethod
    def strip_set_id(cls, v: str) -> str:
        return v.strip()

    @field_validator('opcar_id')
    @classmethod
    def strip_card_id(cls, v: str) -> str:
        return v.strip()

    @field_validator('opcar_name')
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()
