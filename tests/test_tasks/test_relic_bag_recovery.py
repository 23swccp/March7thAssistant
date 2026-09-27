"""背包满后只分解四星及以下遗器并重试一次。"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _stub(name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


def _load_instance():
    relicset = MagicMock()
    stubs = {
        "module.screen": _stub("module.screen", screen=MagicMock()),
        "module.automation": _stub("module.automation", auto=MagicMock()),
        "module.logger": _stub("module.logger", log=MagicMock()),
        "module.config": _stub("module.config", cfg=MagicMock()),
        "module.notification.notification": _stub("module.notification.notification", NotificationLevel=MagicMock()),
        "module.localization": _stub("module.localization", get_raw_instance_names=MagicMock()),
        "tasks.base.base": _stub("tasks.base.base", Base=MagicMock()),
        "tasks.base.team": _stub("tasks.base.team", Team=MagicMock()),
        "tasks.power.character": _stub("tasks.power.character", Character=MagicMock()),
        "tasks.power.relicset": _stub("tasks.power.relicset", Relicset=relicset),
        "tasks.power.relic_navigation": _stub("tasks.power.relic_navigation", navigate_to=MagicMock()),
    }
    path = Path(__file__).parents[2] / "tasks" / "power" / "instance.py"
    spec = importlib.util.spec_from_file_location("tasks.power.instance_recovery_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module, relicset


def test_successful_salvage_restarts_once_and_repeated_toast_stops():
    module, relicset = _load_instance()
    relicset.run.return_value = True
    recovery = {"attempted": False, "instance_name": "测试关卡"}

    with patch.object(module.Instance, "prepare_instance", return_value=True) as prepare, patch.object(
        module.Instance, "start_instance", return_value=True
    ) as start:
        module.Instance.recover_full_relic_bag("侵蚀隧洞", 2, recovery)
        with pytest.raises(module.RelicBagFullError, match="仍提示"):
            module.Instance.recover_full_relic_bag("侵蚀隧洞", 2, recovery)

    relicset.run.assert_called_once_with(replan_navigation=True)
    prepare.assert_called_once_with("侵蚀隧洞", "测试关卡", replan_navigation=True)
    start.assert_called_once_with("侵蚀隧洞", 2, recovery)


def test_failed_salvage_does_not_retry_challenge():
    module, relicset = _load_instance()
    relicset.run.return_value = False
    recovery = {"attempted": False, "instance_name": "测试关卡"}

    with patch.object(module.Instance, "prepare_instance") as prepare:
        with pytest.raises(module.RelicBagFullError, match="分解未成功"):
            module.Instance.recover_full_relic_bag("侵蚀隧洞", 2, recovery)

    prepare.assert_not_called()


def test_skip_returns_to_main_or_stops_if_navigation_fails():
    module, _ = _load_instance()
    error = module.RelicBagFullError("背包仍满")

    module.navigate_to.return_value = None
    module.Instance.leave_full_relic_bag_screen(error)
    module.navigate_to.assert_called_once_with('main')

    module.navigate_to.side_effect = RuntimeError("无法识别")
    with pytest.raises(module.RelicBagFullError) as raised:
        module.Instance.leave_full_relic_bag_screen(error)
    assert raised.value.safe_to_continue is False


def test_echo_of_war_keeps_legacy_full_bag_flow():
    module, relicset = _load_instance()
    relicset.run.return_value = False

    assert module.Instance.recover_full_relic_bag_legacy("历战余响", 1) is False

    relicset.run.assert_called_once_with()
    module.Base.send_notification_with_screenshot.assert_called_once()


def test_echo_of_war_run_does_not_enable_new_recovery():
    module, _ = _load_instance()
    module.cfg.instance_team_enable = False
    module.cfg.tp_before_instance = False

    with patch.object(module.Instance, "prepare_instance", return_value=True), patch.object(
        module.Instance, "start_instance", return_value=True
    ) as start, patch.object(module.Instance, "wait_fight", return_value=True) as wait, patch.object(
        module.Instance, "complete_run"
    ):
        assert module.Instance.run("历战余响", "测试关卡", 1, 1) is True

    start.assert_called_once_with("历战余响", 1, None)
    wait.assert_called_once_with(1, relic_bag_recovery_enabled=False)
