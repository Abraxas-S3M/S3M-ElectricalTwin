"""Repository-root conftest.

Its presence anchors the pytest rootdir at the repository root and puts that
directory on ``sys.path`` so ``import packages.electrical_engineering`` resolves
without an installed distribution.
"""
