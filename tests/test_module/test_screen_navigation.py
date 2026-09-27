"""界面导航在预期路径与实际画面不同时的行为。"""

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


def _load_screen_class():
    stubs = {
        "utils.color": _stub("utils.color", green=lambda value: value),
        "utils.singleton": _stub("utils.singleton", SingletonMeta=type),
        "utils.logger.logger": _stub("utils.logger.logger", Logger=object),
        "module.automation": _stub("module.automation", auto=object()),
        "module.config": _stub("module.config", cfg=object()),
    }
    path = Path(__file__).parents[2] / "module" / "screen" / "screen.py"
    spec = importlib.util.spec_from_file_location("screen_navigation_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module.Screen


def _load_navigation_module(screen):
    stubs = {
        "module.screen": _stub("module.screen", screen=screen),
        "utils.color": _stub("utils.color", green=lambda value: value),
    }
    path = Path(__file__).parents[2] / "tasks" / "power" / "relic_navigation.py"
    spec = importlib.util.spec_from_file_location("relic_navigation_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


def test_unexpected_known_screen_replans_without_automatic_escape():
    screen_class = _load_screen_class()
    screen = object.__new__(screen_class)
    screen.logger = MagicMock()
    screen.current_screen = "guide"
    screen.screen_map = {
        "guide": {"name": "生存索引", "actions": [{"target_screen": "menu", "actions_list": ["escape_guide"]}]},
        "main": {"name": "主界面", "actions": [{"target_screen": "menu", "actions_list": ["open_menu"]}]},
        "menu": {"name": "手机菜单", "actions": [{"target_screen": "bag", "actions_list": ["open_bag"]}]},
        "bag": {"name": "遗器背包", "actions": []},
    }
    actual = {"screen": "guide"}
    executed = []

    def perform(operations):
        operation = operations[0]
        executed.append(operation)
        actual["screen"] = {
            "escape_guide": "main",  # 游戏直接回主界面，跳过预期的手机菜单。
            "open_menu": "menu",
            "open_bag": "bag",
        }[operation]

    def recognize(autotry=False):
        assert autotry is False
        screen.current_screen = actual["screen"]
        return True

    def wait_for_expected(next_screen):
        if actual["screen"] == next_screen:
            screen.current_screen = next_screen
            return True
        return False

    screen.perform_operations = perform
    screen.get_current_screen = recognize
    screen._handle_autotry = MagicMock()
    screen.log_and_raise = MagicMock(side_effect=RuntimeError("导航失败"))
    navigation = _load_navigation_module(screen)
    navigation._wait_for_target = wait_for_expected

    navigation.navigate_to("bag")

    assert executed == ["escape_guide", "open_menu", "open_bag"]
    assert screen.current_screen == "bag"
    screen._handle_autotry.assert_not_called()


def test_unknown_screen_recovers_at_most_three_times():
    screen_class = _load_screen_class()
    screen = object.__new__(screen_class)
    screen.get_current_screen = MagicMock(return_value=False)
    screen._handle_autotry = MagicMock()
    screen.log_and_raise = MagicMock(side_effect=RuntimeError("无法识别当前游戏界面"))
    navigation = _load_navigation_module(screen)

    with pytest.raises(RuntimeError, match="无法识别当前游戏界面"):
        navigation.navigate_to("bag")

    assert screen._handle_autotry.call_count == 3


def test_known_but_stuck_screen_has_separate_operation_limit():
    screen_class = _load_screen_class()
    screen = object.__new__(screen_class)
    screen.logger = MagicMock()
    screen.current_screen = "main"
    screen.screen_map = {
        "main": {"name": "主界面", "actions": [{"target_screen": "bag", "actions_list": ["click"]}]},
        "bag": {"name": "遗器背包", "actions": []},
    }
    screen.get_current_screen = MagicMock(return_value=True)
    screen.perform_operations = MagicMock()
    screen._handle_autotry = MagicMock()
    screen.log_and_raise = MagicMock(side_effect=RuntimeError("操作次数超限"))
    navigation = _load_navigation_module(screen)
    navigation._wait_for_target = MagicMock(return_value=False)

    with pytest.raises(RuntimeError, match="操作次数超限"):
        navigation.navigate_to("bag")

    assert screen.perform_operations.call_count == 12
    screen._handle_autotry.assert_not_called()


def test_existing_change_to_keeps_original_navigation_behavior():
    screen_class = _load_screen_class()
    screen = object.__new__(screen_class)
    screen.current_screen = "guide"
    screen.screen_map = {"guide": {"name": "生存索引"}, "bag": {"name": "遗器背包"}}
    screen.ensure_current_screen_is_clean = MagicMock()
    screen.find_shortest_path = MagicMock(return_value=["guide", "bag"])
    screen._navigate_through_path = MagicMock()
    screen.get_current_screen = MagicMock()

    screen.change_to("bag")

    screen.ensure_current_screen_is_clean.assert_called_once_with()
    screen._navigate_through_path.assert_called_once_with(["guide", "bag"], 2)
    screen.get_current_screen.assert_not_called()
