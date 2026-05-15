from staticfloww.core.main import StaticflowwCore

def test_core_init():
    core = StaticflowwCore()
    assert core.initialized is True
