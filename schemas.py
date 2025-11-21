"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

# Example schemas (you can keep these for reference or remove later)
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Music upload app schemas
class Track(BaseModel):
    """
    Tracks collection schema
    Collection name: "track"
    """
    title: str = Field(..., description="Track title")
    artist: Optional[str] = Field(None, description="Artist name")
    album: Optional[str] = Field(None, description="Album name")
    genre: Optional[str] = Field(None, description="Genre")
    cover_url: Optional[HttpUrl] = Field(None, description="Optional cover image URL")
    filename: str = Field(..., description="Stored filename on server")
    original_filename: str = Field(..., description="Original uploaded filename")
    content_type: str = Field(..., description="MIME type of the uploaded file")
    file_size: int = Field(..., ge=0, description="Size in bytes")
