"""The ElectricalTwin advisory API service.

A thin, read-only FastAPI service that surfaces the platform's safety posture,
vocabularies, engine contract and grounding rules. It performs no reasoning and
holds no control-write path; every endpoint is a ``GET``.
"""
