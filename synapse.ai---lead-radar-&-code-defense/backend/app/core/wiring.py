"""
Dependency wiring (composition root).

Binds the ports declared by a consuming module to implementations published by the owning
module, so modules never import each other:

    Voice Defense  --LeaderboardPublisher-->  Leaderboard   (publishes session results)
    Voice Defense  --RepositoryLookup------>  Code Verifier (reads repository facts)
"""

from fastapi import FastAPI

from app.modules import code_verifier, leaderboard, voice_defense


def wire_dependencies(app: FastAPI) -> None:
    recorder = leaderboard.LeaderboardRecorder()
    directory = code_verifier.RepositoryDirectory()
    app.dependency_overrides[voice_defense.get_leaderboard_publisher] = lambda: recorder
    app.dependency_overrides[voice_defense.get_repository_lookup] = lambda: directory
