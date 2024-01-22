from dataclasses import dataclass, field
from datetime import datetime, timedelta, date

from my_logger import logger


@dataclass(unsafe_hash=True)
class EventMessage:
    t_id: str
    s_id: str
    cmd: str
    active_timer: float
    data: list = field(default_factory=list)

    def __repr__(self):
        d = ''
        for r in self.data:
            d += f"{r} "
        return f"{self.s_id} > {self.t_id}, {self.cmd}, [{d[:-1]}], {int(self.active_timer)}"


@dataclass(unsafe_hash=True)
class RealPrice:
    cur_price: float
    sell_price: float
    buy_price: float

    def __repr__(self):
        return f"{self.cur_price:7}, {self.sell_price:7}, {self.buy_price:7}"


@dataclass(unsafe_hash=True)
class BalanceItemStock:
    """
    주식 >> '코드', '종목명', '청산수량', '현재가', '평균단가', '평가금액', '수익율'
    """
    code: str
    name: str
    qty: int
    price: int
    mean: int
    eval: int
    rate: float

    def __lt__(self, other):
        return self.code < other.code

    def __repr__(self):
        return f"[{self.code}, {self.qty:3d}, {self.price:6d}, {self.mean:6d}, " \
               f"{self.eval:8d}, {100 * self.rate:5.1f}%, {self.name}]"


@dataclass(unsafe_hash=True)
class BalanceItemFO:
    """
    파생 >> '구분'(1;매도/2;매수), '종목', '청산수량', '현재가', '평균단가', '평가손익', '수익율'
    """
    mode: int
    code: str
    qty: int
    price: float
    mean: float
    profit: int
    rate: float

    def __lt__(self, other):
        return self.code < other.code

    def __repr__(self):
        return f"[{self.mode}, {self.code}, {self.qty:2d}, {self.price:6.2f}, " \
               f"{self.mean:6.2f}, {self.profit:8d}, {100 * self.rate:5.1f}%]"


@dataclass(unsafe_hash=True)
class MatchItemStock:
    """
    주식 >> 주문번호, 매매구분, 종목코드, 주문가격, 체결수량, 미체결수량
    """
    ord_no: int
    mode: str
    code: str
    price: int
    qty_m: int
    qty_um: int

    def __lt__(self, other):
        return self.ord_no < other.ord_no

    def __repr__(self):
        return f"[{self.ord_no:7}, {self.mode:3}, {self.code}, " \
               f"{self.price:7}, {self.qty_m:3}, {self.qty_um:3}]"


@dataclass(unsafe_hash=True)
class MatchItemFO:
    """
    파생 >> 주문번호, 매매구분(1;매도/2;매수), 종목코드, 주문가격, 체결수량, 미체결수량
    """
    ord_no: int
    mode: int
    code: str
    price: float
    qty_m: int
    qty_um: int
    key: str = ''

    def __lt__(self, other):
        return self.ord_no < other.ord_no

    def __repr__(self):
        return f"[{self.ord_no:7}, {self.mode}, {self.code}, " \
               f"{self.price:6.2f}, {self.qty_m:3}, {self.qty_um:3}]"


def now_h_m(minutes=0) -> str:
    return (datetime.now() + timedelta(minutes=minutes)).strftime('%H:%M')


def is_future(code) -> bool:
    return True if code[0] == '1' else False


def is_call(code) -> bool:
    return True if code[0] == '2' else False


def is_put(code) -> bool:
    return True if code[0] == '3' else False


def code_type(code) -> str:
    if is_future(code):
        return 'f' if code[:3] == '101' else 'mf'
    elif is_call(code):
        return 'c'
    elif is_put(code):
        return 'p'
    else:
        raise Exception(f"__code_type [f, mf, c, p] Error; {code}")


class MatchMassage:
    def __init__(self, start=10000):
        self.__key = 0

        self.__match = dict()
        self.__counter = start

    @property
    def counter(self) -> int:
        self.__counter += 1
        return self.__counter

    @property
    def key(self) -> int:
        return self.__key

    def new_key(self):
        self.__key = self.counter

    def first(self, key=None, first=None):
        if key is None:
            if self.__key in self.__match:
                self.__match[self.__key][0] = first
            else:
                self.__match[self.__key] = [first, None]
        else:
            if key in self.__match:
                self.__match[key][0] = first
            else:
                self.__match[key] = [first, None]

    def second(self, key=None, second=None):
        if key is None:
            if self.__key in self.__match:
                self.__match[self.__key][1] = second
            else:
                self.__match[self.__key] = [None, second]
        else:
            if key in self.__match:
                self.__match[key][1] = second
            else:
                self.__match[key] = [None, second]

    def pair(self) -> list:
        records = list()
        rm_key = set()
        for k, v in self.__match.items():
            if v[0] is None or v[1] is None:
                continue
            records.append(v)
            rm_key.add(k)
        for key in rm_key:
            del self.__match[key]
        return records

    def output(self):
        for k, v in self.__match.items():
            logger.debug(f"{k, v}")


class StoreInfo:
    def __init__(self, parent, a_id):
        self.__store: dict = parent.store

        if self.__class__.__name__ not in self.__store:
            self.__store[self.__class__.__name__] = dict()
        if a_id not in self.__store[self.__class__.__name__]:
            self.__store[self.__class__.__name__][a_id] = dict()

        self._info = self.__store[self.__class__.__name__][a_id]

    @property
    def keys(self) -> set:
        return {key for key in self._info}

    def get(self, key) -> int | float:
        return self._info[key]

    def match_keys(self, s_keys: set):
        rm_key = self.keys - s_keys
        for k in rm_key:
            self.delete(k)

    def delete(self, key):
        if key in self._info:
            del self._info[key]


class MaxInfo(StoreInfo):
    def __init__(self, parent, a_id):
        super().__init__(parent, a_id)

    def update(self, code, price):
        if code not in self._info:
            self._info[code] = price
            return
        self._info[code] = max(self._info[code], price)


class TrailingStopActive(StoreInfo):
    def __init__(self, parent, a_id):
        super().__init__(parent, a_id)

    def get(self, code) -> bool:
        if code not in self._info:
            self._info[code] = False
        return self._info[code]

    def set(self, code):
        if code not in self._info:
            self._info[code] = True
            return
        self._info[code] = True


class MinInfo(StoreInfo):
    pass


class FutureMean(StoreInfo):
    pass
