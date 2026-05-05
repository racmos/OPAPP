"""
Pydantic schemas for request validation and @validate_json decorator.
"""
from functools import wraps
from typing import Optional
from flask import request, jsonify
from pydantic import BaseModel, ValidationError, Field, field_validator


# ============== Validation Decorator ==============


def validate_json(schema: type[BaseModel]):
    """
    Decorator to validate JSON request body against a Pydantic schema.

    Usage:
        @validate_json(LoginSchema)
        def login():
            data = request.validated_data  # Validated and parsed data
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Bad Request',
                    'message': 'Content-Type must be application/json'
                }), 400

            try:
                data = request.get_json()
                validated = schema(**data)
                request.validated_data = validated
            except ValidationError as e:
                errors = e.errors()
                return jsonify({
                    'success': False,
                    'error': 'Validation Error',
                    'message': 'Invalid request data',
                    'details': [
                        {
                            'field': '.'.join(str(loc) for loc in err['loc']),
                            'message': err['msg'],
                            'type': err['type']
                        }
                        for err in errors
                    ]
                }), 400
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': 'Bad Request',
                    'message': str(e)
                }), 400

            return f(*args, **kwargs)
        return wrapper
    return decorator


# ============== Auth Schemas ==============


class LoginSchema(BaseModel):
    """Schema for login requests."""
    email: str = Field(..., min_length=1, max_length=120, description="User email")
    password: str = Field(..., min_length=1, max_length=128, description="User password")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate and strip email."""
        v = v.strip()
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v


class RegisterSchema(BaseModel):
    """Schema for registration requests."""
    username: str = Field(..., min_length=1, max_length=64, description="Username")
    email: str = Field(..., min_length=1, max_length=120, description="User email")
    password: str = Field(..., min_length=6, max_length=128, description="User password")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate and strip email."""
        v = v.strip()
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @field_validator('username')
    @classmethod
    def strip_username(cls, v: str) -> str:
        """Strip whitespace from username."""
        return v.strip()


# ============== Domain Schemas ==============


class SetCreate(BaseModel):
    """Schema for creating a new set."""
    opset_id: str = Field(..., min_length=1, max_length=32, description="Set ID")
    opset_name: str = Field(..., min_length=1, max_length=255, description="Set name")
    opset_ncard: Optional[int] = Field(None, description="Number of cards in set")
    opset_outdat: Optional[str] = Field(None, description="Release date (YYYY-MM-DD)")

    @field_validator('opset_id')
    @classmethod
    def strip_id(cls, v: str) -> str:
        return v.strip()

    @field_validator('opset_name')
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class SetUpdate(BaseModel):
    """Schema for updating an existing set. All fields optional."""
    opset_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Set name")
    opset_ncard: Optional[int] = Field(None, description="Number of cards in set")
    opset_outdat: Optional[str] = Field(None, description="Release date (YYYY-MM-DD)")


class CollectionAdd(BaseModel):
    """Schema for adding a card to collection."""
    opcol_opset_id: str = Field(..., min_length=1, description="Set ID")
    opcol_opcar_id: str = Field(..., min_length=1, description="Card ID")
    opcol_opcar_version: str = Field('p0', min_length=1, description="Card version")
    opcol_foil: str = Field('N', description="Foil flag (N/Y/S)")
    opcol_quantity: int = Field(1, ge=0, description="Quantity to add")
    opcol_selling: Optional[str] = Field('N', description="Is selling? (Y/N)")
    opcol_sell_price: Optional[float] = Field(None, description="Sell price")
    opcol_condition: Optional[str] = Field(None, max_length=8, description="Card condition")
    opcol_language: Optional[str] = Field(None, max_length=40, description="Card language")


class DeckSave(BaseModel):
    """Schema for saving/updating a deck."""
    opdck_name: str = Field(..., min_length=1, max_length=255, description="Deck name")
    opdck_description: Optional[str] = Field(None, description="Deck description")
    opdck_mode: Optional[str] = Field('1v1', description="Game mode")
    opdck_format: Optional[str] = Field('Standard', description="Deck format")
    opdck_max_set: Optional[str] = Field(None, description="Max set in deck")
    opdck_cards: Optional[dict] = Field(None, description="Deck cards JSON")


# ============== Price / Scraper Schemas ==============


class OpExtractSet(BaseModel):
    """Single set selection for extraction."""
    id: str = Field(..., description="Dropdown value ID (e.g. '569302')")
    code: Optional[str] = Field(None, description="Set code (e.g. 'PRB-02')")
    name: Optional[str] = Field(None, description="Human set name")


class OpExtract(BaseModel):
    """Schema for One Piece card extraction request."""
    sets: list[OpExtractSet] = Field(default_factory=list, description="List of sets to extract (empty = all)")


class IgnoredAdd(BaseModel):
    """Schema for adding a product to the ignored list."""
    id_product: int = Field(..., ge=1, description="Cardmarket idProduct")
    name: str = Field(..., min_length=1, description="Product name")


class IgnoredRestore(BaseModel):
    """Schema for removing a product from the ignored list."""
    id_product: int = Field(..., ge=1, description="Cardmarket idProduct")
    name: str = Field(..., min_length=1, description="Product name")


class AutoMatchPairing(BaseModel):
    """Schema for a single pairing in the selective auto-match apply."""
    id_product: int = Field(..., ge=1, description="Cardmarket idProduct")
    rbset_id: str = Field(..., min_length=1, description="Internal set ID")
    rbcar_id: str = Field(..., min_length=1, description="Internal card ID")
    rbcar_version: str = Field('p0', min_length=1, description="Internal card version")
    foil: Optional[str] = Field(None, description="'N' | 'S' | null")

    @field_validator('foil')
    @classmethod
    def validate_foil(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, '', 'null'):
            return None
        if v not in ('N', 'S'):
            raise ValueError("foil must be 'N', 'S', or null")
        return v


class AutoMatchApply(BaseModel):
    """Schema for the selective auto-match apply request."""
    pairings: list[AutoMatchPairing] = Field(..., min_length=1, description="List of pairings to apply")
