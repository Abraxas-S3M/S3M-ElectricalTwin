"""Advisory, read-only API service for S3M ElectricalTwin.

This service exposes read-only, advisory views over the canonical electrical
model. It never writes to, commands or actuates any control system or field
device; see :mod:`canonical_electrical_model.safety` for the platform
invariant. Request handlers are added in later work-package chunks.
"""

from __future__ import annotations
