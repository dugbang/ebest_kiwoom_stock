from abc import abstractmethod

from config_dir import ConfigDir
from my_logger import logger
from utils import now_h_m, is_future


class TrailingStop:
    """
    # note; 기존에 있었던 종목의 가격 정보는 무시하고 프로그램 동작 시점부터 계산된다.
    """
    def __init__(self, account, queue):
        self._a = account
        self._q = queue

        self._title = list()
        self._ts_records = list()
        self._ref_records = list()

        self._balance_qty = dict()
        self._price_cur = dict()
        self._price_mean = dict()
        self._balance_mode = dict()

        self.load_file()

    def _w_msg(self, f: str, p: str) -> str:
        return f"{self.__class__.__name__}.{f} > {p}"

    @property
    def __ts_enable(self) -> bool:
        return self._a.config['trailing_stop']['enable'] == 1

    @property
    def __ts_start(self) -> str:
        return self._a.config['trailing_stop']['start']

    @property
    def __ts_end(self) -> str:
        return self._a.config['trailing_stop']['end']

    @property
    def __ref_ts(self) -> str:
        return self._a.config['trailing_stop']['ref']

    @property
    def __ts_file(self) -> str:
        return self._a.config['trailing_stop']['file']

    @property
    def _is_active(self) -> bool:
        if not self.__ts_enable:
            return False
        if not self.__ts_start <= now_h_m() < self.__ts_end:
            return False
        return True

    @property
    def _ts_codes(self) -> set:
        return {r[2] for r in self._ts_records}

    def load_file(self):
        self._ts_records = self._load_ts_format(self.__ts_file)
        self._ref_records = self._load_ts_format(self.__ref_ts)

    def _save_file(self):
        # sorting code, priority
        self._ts_records.sort(key=lambda x: (x[2], x[1]))
        records = list()
        records.extend(self._title)
        records.extend(self._ts_records)
        ConfigDir.save_csv(self.__ts_file, records)

    def _valid_priority(self, code, priority):
        for r in [r for r in self._ts_records if r[0] == 1 and r[1] >= priority and r[2] == code]:
            r[0] = 0

    def _validation(self, r, price_rate):
        _, priority, code, _, loss_cut, ts_active, rate, percent = r
        if self._a.ts_active.get(code):
            if price_rate < rate:
                logger.info(f"trailing stop; {code, priority, self._balance_qty[code] * percent // 100}")
                self._post_cmd(code, priority, self._balance_qty[code] * percent // 100)
        else:
            if price_rate < loss_cut:
                logger.info(f"loss_cut; {code, priority, self._balance_qty[code]}")
                self._post_cmd(code, priority, self._balance_qty[code])

    def _post_cmd(self, code, priority, qty, mode='sell'):
        self._valid_priority(code, priority)
        self._q.post(self._a.a_id, 'order', [self._a.a_id, 'i', mode, code, qty])
        self._q.post(self._a.a_id, '-qty', [code, qty, ])
        for e_id in self._a.ts_listener:
            self._q.post(e_id, 'ts_msg', [mode, code, qty, ], s_id=self._a.a_id)

    @abstractmethod
    def _load_ts_format(self, file) -> list:
        pass


class TrailingStopStock(TrailingStop):
    def __init__(self, account=None, queue=None):
        super().__init__(account, queue)

    def update_codes(self):
        """
        # csv >> enable,priority,code,name,loss_cut,ts_active,rate,percent
        """
        names = {d.code: d.name for d in self._a.balance if d.qty}
        self._ts_records = [r for r in self._ts_records if r[2] in names]

        for code in {d.code for d in self._a.balance if d.code not in self._ts_codes}:
            self._add_item(code)

        for r in self._ts_records:
            r[3] = names[r[2]]
        self._save_file()

    def _add_item(self, code):
        if code in self._ts_codes:
            return
        for r in self._ref_records:
            new_r = r[:]
            new_r[2] = code
            self._ts_records.append(new_r)

    def _load_ts_format(self, file) -> list:
        records = ConfigDir.load_csv(file)
        # enable,priority,code,name,loss_cut,ts_active,rate,percent,expiry
        try:
            for r in records[1:]:
                r[0] = int(r[0])
                r[1] = int(r[1])
                r[4] = float(r[4])
                r[5] = float(r[5])
                r[6] = float(r[6])
                r[7] = float(r[7])
        except Exception:
            raise Exception(self._w_msg(f='_load_ts_format', p=f"csv format error; {file}"))

        self._title = records[:1]
        result = records[1:]
        # sorting priority, code
        result.sort(key=lambda x: (x[1], x[2]))
        return result

    def apply(self):
        if not self._is_active:
            return

        self._balance_qty = {d.code: d.qty for d in self._a.balance if d.qty}
        self._price_cur = {d.code: d.price for d in self._a.balance if d.qty}
        self._price_mean = {d.code: d.mean for d in self._a.balance if d.qty}

        # enable,priority,code,name,loss_cut,ts_active,rate,percent
        for r in [r for r in self._ts_records if r[0] == 1 and r[2] in self._price_mean]:
            _, priority, code, _, loss_cut, ts_active, rate, percent = r

            if self._price_cur[code] / self._price_mean[code] > ts_active:
                self._a.ts_active.set(code)

            self._a.max_info.update(code, self._price_cur[code])
            price_rate = self._price_cur[code] / self._a.max_info.get(code)
            self._validation(r, price_rate)


class TrailingStopFO(TrailingStop):
    pass
