from typing import Optional
from pydantic import BaseModel, Field

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

class ChangePasswordResponse(BaseModel):
    success: bool
    message: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="The refresh token")

class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AdminLoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class AdminUserResponse(BaseModel):
    id: str
    email: str

class AdminLoginResponse(BaseModel):
    message: str
    token: str
    user: AdminUserResponse
