from pydantic import BaseModel, EmailStr

class GoogleLoginRequest(BaseModel):
    # Frontend가 Google에서 받은 ID Token
    credential: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"