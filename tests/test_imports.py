import importlib

import pytest

MODULES = ["kripto.hl", "kripto.data", "kripto.backtest", "kripto.metrics",
           "kripto.strategies", "kripto.research", "kripto.paper", "kripto.venue_bn", "kripto.collect", "kripto.live",
           "scripts.health", "scripts.guard", "scripts.forward_score", "scripts.dash"]


@pytest.mark.parametrize("mod", MODULES)
def test_module_imports(mod):
    # catches syntax errors (e.g. py3.12-only f-strings on the 3.11 server) that killed the trader once
    importlib.import_module(mod)
