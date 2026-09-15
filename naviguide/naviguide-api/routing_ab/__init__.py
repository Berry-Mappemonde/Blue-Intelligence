"""NAVIGUIDE sea-routing A/B bench (Problem A).

Compares cargo graphs (searoute, scgraph) and an enriched sailing graph
(catamaran gates + offset off corridors). Does not change the production
``GET /route`` endpoint.
"""

from .legs import BENCHMARK_LEGS

__all__ = ["BENCHMARK_LEGS"]
