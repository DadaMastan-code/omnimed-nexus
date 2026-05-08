"""Ingest repository metadata into the Neo4j knowledge graph."""

from __future__ import annotations

import httpx
import structlog
from neo4j import GraphDatabase

from config import settings

log = structlog.get_logger()


def _driver():
    return GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))


async def ingest_repo_metadata(repo: str) -> None:
    """Fetch repo metadata from GitHub and store in Neo4j."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}",
            headers={"Authorization": f"Bearer {settings.github_token}"},
        )
        if resp.status_code != 200:
            log.warning("repo_metadata_fetch_failed", repo=repo)
            return

        data = resp.json()

    with _driver().session() as session:
        session.run(
            """
            MERGE (r:Repo {name: $name})
            SET r.description = $description,
                r.language = $language,
                r.stars = $stars,
                r.url = $url,
                r.updated = $updated
            """,
            name=repo,
            description=data.get("description", ""),
            language=data.get("language", ""),
            stars=data.get("stargazers_count", 0),
            url=data.get("html_url", ""),
            updated=data.get("updated_at", ""),
        )

    log.info("repo_ingested", repo=repo)


async def link_dependencies(source_repo: str, target_repo: str, rel_type: str = "DEPENDS_ON") -> None:
    with _driver().session() as session:
        session.run(
            f"""
            MERGE (s:Repo {{name: $source}})
            MERGE (t:Repo {{name: $target}})
            MERGE (s)-[:{rel_type}]->(t)
            """,
            source=source_repo,
            target=target_repo,
        )
    log.info("repos_linked", source=source_repo, target=target_repo, rel=rel_type)
