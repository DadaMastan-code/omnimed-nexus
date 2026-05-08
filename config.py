from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")

    # GitHub
    github_app_id: int = Field(0, alias="GITHUB_APP_ID")
    github_app_private_key_path: str = Field("./github-app.pem", alias="GITHUB_APP_PRIVATE_KEY_PATH")
    github_webhook_secret: str = Field("", alias="GITHUB_WEBHOOK_SECRET")
    github_token: str = Field("", alias="GITHUB_TOKEN")

    # Repos
    codesense_repo: str = Field("DadaMastan-code/codesense-ai", alias="CODESENSE_REPO")
    medfusion_repo: str = Field("DadaMastan-code/MedFusion-Leuk", alias="MEDFUSION_REPO")
    medbrain_repo: str = Field("DadaMastan-code/medbrain-ai", alias="MEDBRAIN_REPO")
    nexus_repo: str = Field("DadaMastan-code/omnimed-nexus", alias="NEXUS_REPO")

    # Service URLs
    codesense_api_url: str = Field("http://localhost:8001", alias="CODESENSE_API_URL")
    medfusion_api_url: str = Field("http://localhost:8002", alias="MEDFUSION_API_URL")
    medbrain_api_url: str = Field("http://localhost:8003", alias="MEDBRAIN_API_URL")

    # Qdrant
    qdrant_host: str = Field("localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(6333, alias="QDRANT_PORT")
    qdrant_api_key: str = Field("", alias="QDRANT_API_KEY")

    # Neo4j
    neo4j_uri: str = Field("bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field("neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field("omnimed-nexus", alias="NEO4J_PASSWORD")

    # MLflow
    mlflow_tracking_uri: str = Field("http://localhost:5001", alias="MLFLOW_TRACKING_URI")
    mlflow_experiment_name: str = Field("omnimed-nexus", alias="MLFLOW_EXPERIMENT_NAME")

    @property
    def all_repos(self) -> list[str]:
        return [self.codesense_repo, self.medfusion_repo, self.medbrain_repo]

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()
