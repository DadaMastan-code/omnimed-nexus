"""Pre-built Cypher queries for the OmniMed knowledge graph."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from config import settings


def _driver():
    return GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))


def run_query(cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with _driver().session() as session:
        result = session.run(cypher, **(params or {}))
        return [dict(r) for r in result]


def get_repo_graph(repo: str) -> dict[str, Any]:
    """Return a repo's full subgraph: findings, relationships, models."""
    findings = run_query(
        "MATCH (r:Repo {name: $repo})-[:HAS_FINDING]->(f:Finding) RETURN f",
        {"repo": repo},
    )
    relationships = run_query(
        "MATCH (r:Repo {name: $repo})-[rel]->(other) RETURN type(rel) as type, other.name as target",
        {"repo": repo},
    )
    return {"repo": repo, "findings": findings, "relationships": relationships}


def cross_repo_concepts() -> list[dict[str, Any]]:
    """Find concepts that appear in more than one repo's knowledge base."""
    return run_query(
        """
        MATCH (c:Concept)<-[:MENTIONS]-(r:Repo)
        WITH c, collect(r.name) as repos
        WHERE size(repos) > 1
        RETURN c.name as concept, repos
        ORDER BY size(repos) DESC
        LIMIT 20
        """
    )
