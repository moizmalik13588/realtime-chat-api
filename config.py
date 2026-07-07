from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str
    algorithm: str
    database_url: str

    class Config:
        env_file = ".env"


settings = Settings()