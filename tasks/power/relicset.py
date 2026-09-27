from module.automation import auto
from module.screen import screen
from module.logger import log
from .relic_navigation import navigate_to
import time


class Relicset:
    ENTER_BREAK_IMAGE = "./assets/images/zh_CN/relicset/enter_break.png"
    SCREEN_IMAGE = "./assets/images/zh_CN/relicset/screen.png"
    SELECT_IMAGE = "./assets/images/zh_CN/relicset/select.png"
    LEVEL_FOUR_IMAGE = "./assets/images/zh_CN/relicset/level_four.png"
    CONFIRM_IMAGE = "./assets/images/zh_CN/base/confirm.png"
    BREAK_IMAGE = "./assets/images/zh_CN/relicset/break.png"
    CLICK_CLOSE_IMAGE = "./assets/images/zh_CN/base/click_close.png"

    @staticmethod
    def run(replan_navigation=False):
        """
        执行分解四星及以下遗器操作。
        返回值：
          True  - 成功分解了遗器
          False - 未找到可分解的遗器（背包内无低星遗器）或流程出错
        """
        log.hr("准备分解四星及以下遗器", 2)

        if not replan_navigation:
            # 常规自动分解保留原有操作顺序；背包满时才使用恢复导航。
            if not Relicset.change_to_relicset():
                return False
            if not Relicset.prepare_break_down_relicset():
                return False
            result = Relicset.start_break_down_relicset()
            auto.press_key("esc")
            screen.wait_for_screen_change('bag_relicset')
            return result

        try:
            if not Relicset.change_to_relicset(navigate_to):
                return False
            if not Relicset.prepare_break_down_relicset():
                return False
            return Relicset.start_break_down_relicset()
        finally:
            # 筛选失败也可能停在弹窗或分解页，必须先回到可识别的界面。
            auto.press_key('esc')
            time.sleep(0.5)
            for _ in range(2):
                if not auto.find_element(Relicset.SCREEN_IMAGE, "image", 0.9, max_retries=1):
                    break
                auto.press_key('esc')
                time.sleep(0.5)
            navigate_to('bag_relicset')

    @staticmethod
    def change_to_relicset(navigate=None):
        (navigate or screen.change_to)("bag_relicset")
        auto.click_element(Relicset.ENTER_BREAK_IMAGE, "image", 0.9, max_retries=10)
        if auto.find_element(Relicset.SCREEN_IMAGE, "image", 0.9, max_retries=10):
            return True
        log.error("切换到遗器分解界面失败")
        return False

    @staticmethod
    def prepare_break_down_relicset():
        if auto.click_element(Relicset.SELECT_IMAGE, "image", 0.9, max_retries=10):
            time.sleep(1)
            if auto.find_element(Relicset.LEVEL_FOUR_IMAGE, "image", 0.9, max_retries=10):
                # 多次判断避免误操作
                if auto.click_element("4星及以下", "text", max_retries=10):
                    if auto.click_element(Relicset.CONFIRM_IMAGE, "image", 0.9, max_retries=10):
                        if auto.find_element(Relicset.SCREEN_IMAGE, "image", 0.9, max_retries=10):
                            log.info("筛选遗器成功")
                            return True
        log.error("筛选遗器失败")
        return False

    @staticmethod
    def start_break_down_relicset():
        if not auto.click_element(Relicset.BREAK_IMAGE, "image", 0.9, max_retries=5):
            log.warning("未找到分解按钮，可能没有可分解的四星及以下遗器")
            return False

        time.sleep(1)
        if auto.click_element(Relicset.CONFIRM_IMAGE, "image", 0.9, max_retries=10):
            if auto.click_element(Relicset.CLICK_CLOSE_IMAGE, "image", 0.8, max_retries=10):
                if auto.find_element(Relicset.SCREEN_IMAGE, "image", 0.9, max_retries=10):
                    log.info("分解遗器成功")
                    return True
        log.error("分解遗器失败")
        return False
