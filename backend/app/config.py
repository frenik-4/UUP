from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://uup:uup_dev_pw@localhost:5432/uup"
    secret_key: str = "dev-secret-change-in-prod"
    seed_on_start: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
