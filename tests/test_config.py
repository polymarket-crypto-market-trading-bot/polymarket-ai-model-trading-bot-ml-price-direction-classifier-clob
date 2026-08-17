"""Config validation tests."""

from config.settings import Settings


def test_default_paper_mode():
    settings = Settings()
    assert settings.bot_mode == "paper"
    assert settings.enable_live_trading is False


def test_live_blocked_by_default():
    settings = Settings(enable_live_trading=False)
    try:
        settings.assert_live_allowed()
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_feature_windows_parsed():
    settings = Settings(feature_windows="5,10,20")
    assert settings.feature_window_list == [5, 10, 20]
