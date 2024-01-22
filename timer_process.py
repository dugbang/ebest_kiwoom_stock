from dataclasses import dataclass
from time import sleep
from timeit import default_timer

from my_logger import logger


@dataclass(unsafe_hash=True)
class _CallbackTimer:
    counter: int
    callback: object


class TimerProcess:
    def __init__(self, config):
        self.__c = config

        self.__counter = 0
        self.__prev_counter = 0
        self.__interval_timer = 0

        self.__single = set()
        self.__period = set()

    @property
    def __interval(self) -> float:
        return self.__c.row['timer']['interval']

    @property
    def __loop_sleep(self) -> float:
        return self.__c.row['timer']['loop_sleep']

    def add_period(self, counter: int, callback: object):
        self.__period.add(_CallbackTimer(counter, callback))

    def add_single(self, counter: int, callback: object):
        self.__single.add(_CallbackTimer(counter + self.__counter, callback))

    def sleep_and_processing(self, delay: float):
        if self.__interval_timer == 0:
            self.__start()
        time_out = delay + default_timer()
        while time_out > default_timer():
            self.processing()
            sleep(self.__loop_sleep)

    def processing(self):
        if self.__interval_timer == 0:
            self.__start()
        if self.__time_validate() is False:
            return
        self.__counter += 1

        for e in [e for e in self.__single if e.counter <= self.__counter]:
            e.callback()
        self.__single = {e for e in self.__single if e.counter > self.__counter}

        for e in [e for e in self.__period if self.__match_counter(e.counter)]:
            e.callback()

    def __start(self):
        self.__interval_timer = default_timer() + self.__interval

    def __time_validate(self) -> bool:
        if self.__interval_timer > default_timer():
            return False
        self.__interval_timer += self.__interval
        self.__prev_counter = self.__counter
        while self.__interval_timer < default_timer():
            logger.warning(f"  !!! OVER TIMER COUNTER !!!")
            self.__interval_timer += self.__interval
            self.__counter += 1
        return True

    def __match_counter(self, event_counter) -> bool:
        if self.__counter % event_counter == 0:
            return True
        c_mod = self.__counter // event_counter
        p_mod = self.__prev_counter // event_counter
        return False if c_mod == p_mod else True


if __name__ == '__main__':
    from configuration import Configuration

    t = TimerProcess(Configuration())
    c = 4
    t.add_single(c, lambda: logger.debug(f"single; {c}"))
    t.add_period(3, lambda: logger.debug(f"period; 3"))
    t.sleep_and_processing(1)
    t.add_period(3, lambda: logger.debug(f"period; 3"))
    t.add_single(2, lambda: logger.debug(f"single; 2"))
    t.add_period(1, lambda: logger.debug(f"period; 1"))
    t.sleep_and_processing(10)
    t.processing()
    logger.debug(f"end...")
