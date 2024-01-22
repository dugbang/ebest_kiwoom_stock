from my_logger import logger
from xing_basic import XAReal


class _RealBase:
    def __init__(self, name, tr1101):
        self._com = XAReal(name, handler=self.__receive_data)
        self.__real = tr1101.real

    def __receive_data(self, com, tr_code):
        code = com.GetFieldData('OutBlock', 'shcode')
        try:
            tmp = com.GetFieldData('OutBlock', 'offerho1')
            if len(tmp):
                self.__real[code].sell_price = int(tmp)
                self.__real[code].cur_price = self.__real[code].sell_price
            tmp = com.GetFieldData('OutBlock', 'bidho1')
            if len(tmp):
                self.__real[code].buy_price = int(tmp)
        except (KeyError, ValueError, Exception):
            logger.warning(f"Exception; RealBase > {code}")

    def add_field(self, name, code):
        self._com.add_field(name, code)

    def start(self):
        self._com.start()

    def stop(self):
        self._com.stop()

    def join(self):
        self._com.join()


class _RealH1(_RealBase):
    """
    KOSPI 호가잔량
    """
    def __init__(self, tr1101):
        super().__init__('KOSPI 호가잔량', tr1101)
        self._com.LoadFromResFile('Res\\H1_.res')


class _RealHA(_RealBase):
    """
    KOSDAQ 호가잔량
    """
    def __init__(self, tr1101):
        super().__init__('KOSDAQ 호가잔량', tr1101)
        self._com.LoadFromResFile('Res\\HA_.res')


class RealStock:
    def __init__(self, tr1101, all_stock_codes):
        self.__tr1101 = tr1101
        self.__real_kospi = _RealH1(self.__tr1101)
        self.__real_kosdaq = _RealHA(self.__tr1101)

        self.__kospi_codes = [r[0] for r in all_stock_codes if r[4] == 1]

    def stop(self):
        self.__real_kospi.stop()
        self.__real_kospi.join()

        self.__real_kosdaq.stop()
        self.__real_kosdaq.join()

    def register(self, code):
        if code in self.__tr1101.real:
            return
        logger.debug(f"stock code register; {code}")
        self.__tr1101.download(code)
        if code in self.__kospi_codes:
            self.__real_kospi.start()
            self.__real_kospi.add_field('shcode', code)
        else:
            self.__real_kosdaq.start()
            self.__real_kosdaq.add_field('shcode', code)


