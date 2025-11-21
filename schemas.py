"""
Database Schemas for Sanctuary Builder

Each Pydantic model corresponds to a MongoDB collection with the collection
name being the lowercase of the class name, e.g. User -> "user".

This app supports bilingual content (English + Chinese). For text fields that
are shown to end users, provide both language variants when applicable.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# =============== CORE USER & IDENTITY ===============

class User(BaseModel):
    """User profile and settings
    Collection: user
    """
    email: str = Field(..., description="Email address")
    name: str = Field(..., description="Display name")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    locale: str = Field("en", description="Preferred language: en or zh")
    is_active: bool = Field(True)
    roles: List[str] = Field(default_factory=lambda: ["user"], description="Roles such as user, admin")

# =============== DEVOTIONAL CONTENT ===============

class Devotional(BaseModel):
    """Daily devotional content for a specific calendar date
    Collection: devotional
    """
    day: str = Field(..., description="Calendar day for this devotional (YYYY-MM-DD)")
    title_en: str = Field(...)
    title_zh: str = Field(...)
    passage_en: Optional[str] = Field(None, description="Scripture or theme (EN)")
    passage_zh: Optional[str] = Field(None, description="Scripture or theme (ZH)")
    content_en: str = Field(..., description="Main devotional text (EN)")
    content_zh: str = Field(..., description="Main devotional text (ZH)")
    reflection_prompt_en: Optional[str] = Field(None)
    reflection_prompt_zh: Optional[str] = Field(None)

# =============== PROGRESS, STREAKS, REWARDS ===============

class Progress(BaseModel):
    """User progress per day
    Collection: progress
    """
    user_id: str = Field(...)
    day: str = Field(..., description="YYYY-MM-DD")
    completed: bool = Field(True)
    points_earned: int = Field(0)

class Reward(BaseModel):
    """Earned rewards/badges
    Collection: reward
    """
    user_id: str = Field(...)
    reward_type: str = Field(..., description="badge, milestone, coupon, etc.")
    name_en: str = Field(...)
    name_zh: str = Field(...)
    description_en: Optional[str] = Field(None)
    description_zh: Optional[str] = Field(None)
    points: int = Field(0)

# =============== MARKETPLACE ===============

class Product(BaseModel):
    """Digital marketplace item
    Collection: product
    """
    sku: str = Field(..., description="Unique product code")
    title_en: str = Field(...)
    title_zh: str = Field(...)
    description_en: Optional[str] = Field(None)
    description_zh: Optional[str] = Field(None)
    price: float = Field(..., ge=0)
    currency: str = Field("USD")
    categories: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list, description="Images or previews")
    attributes: Dict[str, str] = Field(default_factory=dict)
    status: str = Field("active", description="active, hidden, archived")

class Order(BaseModel):
    """Simple order record for digital goods
    Collection: order
    """
    user_id: str = Field(...)
    items: List[Dict[str, Any]] = Field(..., description="List of {sku, qty, price}")
    total_amount: float = Field(..., ge=0)
    currency: str = Field("USD")
    status: str = Field("pending", description="pending, paid, refunded, cancelled")

# =============== COMMUNITY (FUTURE) ===============

class Post(BaseModel):
    """Optional community post structure
    Collection: post
    """
    user_id: str = Field(...)
    content: str = Field(...)
    locale: str = Field("en")
    tags: List[str] = Field(default_factory=list)
