from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    expires_at: str
    display_name: str


class MeOut(BaseModel):
    logged_in: bool
    display_name: str = ""
    remote_data: bool = False  # Supabase 고객사 자료를 읽을 수 있는 상태인지
