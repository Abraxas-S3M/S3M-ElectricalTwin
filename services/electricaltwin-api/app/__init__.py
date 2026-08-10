"""The ElectricalTwin advisory API service.

A thin, read-only FastAPI service that surfaces the platform's safety posture,
vocabularies, engine contract and grounding rules. It performs no reasoning and
holds no control-write path; every endpoint is a ``GET``.
"""S3M ElectricalTwin API service (advisory, read-only).

Placeholder package for the read-only advisory API. This service exposes
observations and analytics only; it exposes no endpoint that writes to,
commands, or actuates any control system or field device.
"""
