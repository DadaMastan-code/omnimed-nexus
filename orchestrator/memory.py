"""Neo4j-backed long-term memory for the meta-agent."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver

from config import settings

log = structlog.get_logger()


class NexusMemory:
    """Stores interactions, findings, and cross-repo links in Neo4j."""

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await self._ensure_schema()

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()

    async def _ensure_schema(self) -> None:
        async with self._driver.session() as session:
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:Interaction) REQUIRE i.id IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:Finding) REQUIRE f.id IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repo) REQUIRE r.name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:Model) REQUIRE m.id IS UNIQUE")

    async def store_interaction(
        self,
        session_id: str,
        query: str,
        targets: list[str],
        response_summary: str,
    ) -> None:
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (i:Interaction {id: $id})
                SET i.query = $query,
                    i.targets = $targets,
                    i.response_summary = $response_summary,
                    i.timestamp = $ts
                """,
                id=session_id,
                query=query,
                targets=targets,
                response_summary=response_summary,
                ts=datetime.now(UTC).isoformat(),
            )

    async def store_finding(
        self,
        repo: str,
        finding_type: str,  # "code_issue" | "model_drift" | "clinical_flag"
        description: str,
        severity: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        finding_id = f"{repo}_{finding_type}_{datetime.now(UTC).timestamp()}"
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (r:Repo {name: $repo})
                CREATE (f:Finding {
                    id: $id,
                    type: $type,
                    description: $description,
                    severity: $severity,
                    metadata: $metadata,
                    timestamp: $ts,
                    resolved: false
                })
                CREATE (r)-[:HAS_FINDING]->(f)
                """,
                repo=repo,
                id=finding_id,
                type=finding_type,
                description=description,
                severity=severity,
                metadata=str(metadata or {}),
                ts=datetime.now(UTC).isoformat(),
            )
        log.info("finding_stored", id=finding_id, repo=repo, type=finding_type)
        return finding_id

    async def link_repos(self, source_repo: str, target_repo: str, relationship: str) -> None:
        """Record a dependency/relationship between repos in the graph."""
        async with self._driver.session() as session:
            await session.run(
                """
                MERGE (s:Repo {name: $source})
                MERGE (t:Repo {name: $target})
                MERGE (s)-[r:RELATES_TO {type: $rel}]->(t)
                SET r.updated = $ts
                """,
                source=source_repo,
                target=target_repo,
                rel=relationship,
                ts=datetime.now(UTC).isoformat(),
            )

    async def get_open_findings(self, repo: str | None = None) -> list[dict[str, Any]]:
        query = (
            "MATCH (r:Repo)-[:HAS_FINDING]->(f:Finding) "
            "WHERE f.resolved = false"
        )
        params: dict[str, Any] = {}
        if repo:
            query += " AND r.name = $repo"
            params["repo"] = repo
        query += " RETURN r.name as repo, f ORDER BY f.timestamp DESC LIMIT 50"

        async with self._driver.session() as session:
            result = await session.run(query, **params)
            return [{"repo": r["repo"], **dict(r["f"])} async for r in result]

    async def mark_finding_resolved(self, finding_id: str) -> None:
        async with self._driver.session() as session:
            await session.run(
                "MATCH (f:Finding {id: $id}) SET f.resolved = true, f.resolved_at = $ts",
                id=finding_id,
                ts=datetime.now(UTC).isoformat(),
            )


memory = NexusMemory()
