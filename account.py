from abc import abstractmethod

from datetime import datetime, timedelta

from config_dir import ConfigDir
from my_logger import logger
from trailing_stop import TrailingStopStock, TrailingStopFO
from utils import MaxInfo, TrailingStopActive, is_future, code_type, MinInfo, FutureMean


class ConfigAccount:
    def __init__(self, file):
        self.__file = file
        self.__config = ConfigDir.load_yaml(self.__file, sub='account')

    def _load_file(self):
        self.__config = ConfigDir.load_yaml(self.__file, sub='account')

    @property
    def config(self) -> dict:
        return self.__config

    @property
    def a_type(self) -> str:
        return self.__config['a_type']

    @property
    def a_no(self) -> int:
        return self.__config['a_no']

    @property
    def e_id(self) -> str:
        return self.__config['e_id']

    @property
    def a_id(self) -> str:
        return self.e_id

    @property
    def ts_listener(self) -> list:
        return self.__config['ts_listener']

    @abstractmethod
    def event_processing(self):
        pass


class Account(ConfigAccount):
    def __init__(self, parent, file):
        super().__init__(file)

        self._c = parent.config
        self._s = parent.session
        self._q = parent.queue
        self._t = parent.telegram
        self._match = parent.match

        self._balance = list()

        self.__ts_active = TrailingStopActive(parent, self.a_id)
        self._trailing_stop = None
        self._max_info = None
        self._min_info = None
        self._fut_mean = None

    @property
    def min_info(self) -> MinInfo | None:
        return self._min_info

    @property
    def max_info(self) -> MaxInfo:
        return self._max_info

    @property
    def ts_active(self) -> TrailingStopActive:
        return self.__ts_active

    @property
    def fut_mean(self) -> FutureMean | None:
        return self._fut_mean

    def reload(self):
        self._load_file()
        self._trailing_stop.load_file()

    @property
    def balance(self) -> list:
        return self._balance

    def _exception(self, msg_):
        self._t.send_msg(msg_)
        raise Exception(msg_)

    def _w_msg(self, f: str, p: str) -> str:
        return f"{self.__class__.__name__}.{f} > {p}"

    def initial(self):
        self._load_balance()
        self._trailing_stop.update_codes()

    def event_processing(self):
        for e in self._q.get(self.e_id):
            logger.debug(f"{self.__class__.__name__}.event_processing; {e}")
            if e.cmd in ('order', 'modify', 'cancel', 'timer'):
                self._match.new_key()
                self._match.first(first=e.s_id)
            match e.cmd:
                case 'order':
                    """
                    /o a_id [m/a/i] sell code qty money/price
                    """
                    self.__event_order(e)
                case 'modify':
                    """
                    /m a_id mode code qty price org_ord_no
                    """
                    self._s.modify(e.data[0], e.data[1], e.data[2], e.data[3], e.data[4], e.data[5])
                case 'cancel':
                    """
                    /c a_id mode code qty org_ord_no
                    """
                    self._s.cancel(e.data[0], e.data[1], e.data[2], e.data[3], e.data[4])
                case 'timer':
                    self.__event_timer(e)
                case 'lm':
                    self.__event_lm(e)
                case 'ls':
                    self.__event_ls(e)
                case 'load_balance':
                    self._load_balance()
                case '-qty':
                    for d in [d for d in self._balance if d.code == e.data[0]]:
                        d.qty -= int(e.data[1])
                case _:
                    logger.warning(self._w_msg('_event_processing',
                                               f"not match cmd; {e.cmd}"))

    def __event_lm(self, e):
        data = list()
        data.append('ok')
        data.append(self.a_id)
        data.append(self.a_type)
        records = self._s.matching_items(self.a_id)
        data.append(len(records))
        for d in records:
            data.append(d)
        self._q.post(t_id=e.s_id, cmd='r_lm', data=data)

    def __event_ls(self, e):
        self._load_balance()
        data = list()
        data.append('ok')
        data.append(self.a_id)
        data.append(self.a_type)
        data.append(len(self._balance))
        for d in self._balance:
            data.append(d)
        self._q.post(t_id=e.s_id, cmd='r_ls', data=data)

    def __event_timer(self, e):
        """
        /t 1145 a_id [m/a/i] sell code qty money/price
        """
        def compute_delay() -> float:
            h_ = int(e.data[0]) // 100 - datetime.now().hour
            m_ = int(e.data[0]) % 100 - datetime.now().minute
            delay_ = (timedelta(hours=h_) + timedelta(minutes=m_)).total_seconds()
            if delay_ < 0:
                self._exception(self._w_msg('__event_timer.compute_delay',
                                            f"error timer setting delay; {delay_:0.f} second"))
            return delay_

        delay = compute_delay()
        logger.debug(f"post event; {self.e_id, 'order', e.data[1:], delay}")
        self._q.post(self.e_id, 'order', e.data[1:], delay=delay, s_id=e.s_id)
        logger.debug(f"second; order event; {delay // 60} min later")
        self._match.second(second=f"order event >> {delay // 60} min later")

    def __event_order(self, e):
        a_id = e.data[0]
        match e.data[1]:
            case 'm' | 'manual':
                if len(e.data) != 6:
                    self._exception(self._w_msg('__event_order', f"error order cmd; {e.data}"))
                self._s.order(a_id, e.data[2], e.data[3], e.data[4], e.data[5])
                self._q.post(e.s_id, 'msg',
                             [f"order > {a_id, e.data[2], e.data[3], e.data[4], e.data[5]}", ])
            case 'a' | 'auto' | 'i' | 'imminent':
                code, mode, price, qty = self._order_data(e)
                self._s.order(a_id, mode, code, qty, price)
                self._q.post(e.s_id, 'msg', [f"order > {a_id, mode, code, qty, price}", ])
            case _:
                self._exception(self._w_msg('__event_order',
                                            f"order mode error; {a_id} not defined"))

    def _load_balance(self):
        self._balance = self._s.load_balance(self.a_id)
        self._update_price()
        self._trailing_stop.update_codes()

    def stop(self):
        self._trailing_stop.update_codes()

        self.ts_active.match_keys({d.code for d in self._balance})
        self._max_info.match_keys({d.code for d in self._balance})
        if self._min_info:
            self._min_info.match_keys({d.code for d in self._balance})
        if self._fut_mean:
            self._fut_mean.match_keys({d.code for d in self._balance})

    @abstractmethod
    def _update_price(self):
        pass

    @abstractmethod
    def _order_data(self, e):
        pass


class AccountStock(Account):
    def __init__(self, parent, file):
        super().__init__(parent, file)

        self._max_info = MaxInfo(parent, self.a_id)
        self._trailing_stop = TrailingStopStock(self, self._q)

    def _order_data(self, e) -> tuple:
        opt = e.data[1]
        mode = e.data[2]
        code = e.data[3]
        qty = int(e.data[4])
        if opt in ('a', 'auto'):
            price = self._s.buy_price(code) if mode == 'buy' else self._s.sell_price(code)
        else:   # i, imminent
            price = self._s.sell_price(code) if mode == 'buy' else self._s.buy_price(code)
        if price == 0:
            self._exception(self._w_msg('_order_data', f"ERROR > PRICE; {price}"))
        qty_ = int(e.data[5]) // price if qty == 0 else qty
        if qty_ == 0:
            self._exception(self._w_msg('_order_data', f"ERROR > QTY; {qty_}"))
        return code, mode, price, qty_

    def background(self):
        self._update_price()
        self._trailing_stop.apply()

    def _update_price(self):
        for d in self._balance:
            price = self._s.cur_price(d.code)
            if price == 0:
                continue
            d.price = price
            d.eval = d.price * d.qty
            try:
                d.rate = d.price / d.mean - 1.
            except ZeroDivisionError:
                d.rate = 0.


class AccountFO(Account):
    pass
