"""遗器背包满时使用的有限次数界面导航。"""

import time

from module.screen import screen
from utils.color import green


def _wait_for_target(next_screen):
    for _ in range(10):
        screen.logger.debug(f"等待：{screen.get_name(next_screen)}")
        if screen.check_screen(next_screen):
            screen.logger.info(f"切换到：{green(screen.get_name(next_screen))}")
            time.sleep(screen.wait_screen_change_time)
            return True
        time.sleep(0.5)
    return False


def navigate_to(target_screen):
    """从实际识别到的界面重新规划，只在背包满恢复流程中调用。"""
    unknown_attempts = 0
    operations_count = 0
    max_operations = 12

    # 不使用 get_current_screen 默认的自动 Esc；恢复操作在此显式计数。
    while not screen.get_current_screen(autotry=False):
        if unknown_attempts >= 3:
            screen.log_and_raise("连续三次无法识别当前游戏界面", "无法识别当前游戏界面")
        unknown_attempts += 1
        screen._handle_autotry()

    unknown_attempts = 0
    while screen.current_screen != target_screen:
        if operations_count >= max_operations:
            screen.log_and_raise(f"切换到 {screen.get_name(target_screen)} 的操作次数超限", "无法切换到指定游戏界面")

        path = screen.find_shortest_path(screen.current_screen, target_screen)
        if not path:
            screen.log_and_raise(
                f"无法从 {screen.get_name(screen.current_screen)} 切换到 {screen.get_name(target_screen)}",
                "无法切换到指定游戏界面",
            )

        current_screen, next_screen = path[:2]
        screen.logger.info(f"当前界面：{green(screen.get_name(current_screen))}")
        screen.perform_operations(screen.get_operations(current_screen, next_screen))
        operations_count += 1

        if _wait_for_target(next_screen):
            unknown_attempts = 0
            continue

        # 预期画面未出现时先识别实际位置，已收录界面不消耗未知次数。
        recognized = screen.get_current_screen(autotry=False)
        if recognized and screen.current_screen != current_screen:
            unknown_attempts = 0
            screen.logger.warning(f"实际到达 {screen.get_name(screen.current_screen)}，重新规划路线")
            continue

        timeout_operations = screen.get_timeout_operations(current_screen, next_screen)
        if timeout_operations:
            if operations_count >= max_operations:
                screen.log_and_raise(f"切换到 {screen.get_name(target_screen)} 的操作次数超限", "无法切换到指定游戏界面")
            screen.perform_operations(timeout_operations)
            operations_count += 1
            if _wait_for_target(next_screen):
                unknown_attempts = 0
                continue
            recognized = screen.get_current_screen(autotry=False)

        if recognized:
            unknown_attempts = 0
            screen.logger.warning(f"实际仍在 {screen.get_name(screen.current_screen)}，重新规划路线")
            continue

        unknown_attempts += 1
        if unknown_attempts >= 3:
            screen.log_and_raise("连续三次操作后仍无法识别界面", "无法识别当前游戏界面")
        while unknown_attempts < 3:
            screen._handle_autotry()
            if screen.get_current_screen(autotry=False):
                unknown_attempts = 0
                screen.logger.warning(f"恢复后到达 {screen.get_name(screen.current_screen)}，重新规划路线")
                break
            unknown_attempts += 1
        if unknown_attempts >= 3:
            screen.log_and_raise("连续三次操作后仍无法识别界面", "无法识别当前游戏界面")
