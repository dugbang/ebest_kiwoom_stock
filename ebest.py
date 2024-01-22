from ebest_query import EBestPack
from my_logger import logger
from session import Session
from xing_basic import XASession


class EBest(Session):
    def __init__(self, parent):
        super().__init__(parent)

        self.__xing: XASession = XASession()
        self.__xing.initial(self._c.server_address)
        self.__account_numbers = list()

        self.__tr: None | EBestPack = None

    def initial(self, parent):
        self._a = parent.accounts
        self.__tr = EBestPack(self._c.demo, self._match)

    def _st_load_balance(self, a_id) -> list:
        self.__tr.st_0424.download(self._a[a_id].a_no, self._c.apw)
        return self.__tr.st_0424.results

    def _fo_load_balance(self, a_id) -> list:
        self.__tr.fo_0441.download(self._a[a_id].a_no, self._c.apw)
        return self.__tr.fo_0441.results

    def _st_matching_items(self, a_id) -> list:
        self.__tr.st_13700.download(self._a[a_id].a_no, self._c.apw)
        return self.__tr.st_13700.results

    def _fo_matching_items(self, a_id) -> list:
        self.__tr.fo_00600.download(self._a[a_id].a_no, self._c.apw)
        return self.__tr.fo_00600.results

    def __real_register(self, code):
        if len(code) == len('000660'):     # 주식
            self.__tr.real_st.register(code)
        elif len(code) == len('101V3000'):  # 선옵
            self.__tr.real_fo.register(code)
        else:
            raise Exception(f"Not Support Type; {code}")

    def cur_price(self, code) -> int | float:
        if code not in self.__tr.real:
            self.__real_register(code)
        return self.__tr.real[code].cur_price

    def buy_price(self, code) -> int | float:
        if code not in self.__tr.real:
            self.__real_register(code)
        return self.__tr.real[code].buy_price

    def sell_price(self, code) -> int | float:
        if code not in self.__tr.real:
            self.__real_register(code)
        return self.__tr.real[code].sell_price

    def order(self, a_id, mode, code, qty, price):
        if a_id not in self._a:
            self._exception(self._w_msg('order', f"account id error; {a_id}"))
        if mode not in ('buy', 'sell'):
            self._exception(self._w_msg('order', f"Error mode; {mode}"))
        logger.info(f"order; {a_id, mode, code, qty, price}")

        match self._a[a_id].a_type:
            case 'stock':
                self.__tr.st_00600.order(self._a[a_id].a_no, self._c.apw,
                                         1 if mode == 'sell' else 2, code, qty, price)
            case 'fo':
                self.__tr.fo_00100.order(self._a[a_id].a_no, self._c.apw,
                                         1 if mode == 'sell' else 2, code, qty, price)
            case _:
                self._exception(self._w_msg('order', f"not support account type; {self._a[a_id].a_type}"))

    def modify(self, a_id, _mode, code, qty, price, org_order_no):
        if a_id not in self._a:
            self._exception(self._w_msg('modify', f"account id error; {a_id}"))
        logger.info(f"modify; {a_id, code, qty, price, org_order_no}")

        match self._a[a_id].a_type:
            case 'stock':
                self.__tr.st_00700.modify(self._a[a_id].a_no, self._c.apw, code, qty, price, org_order_no)
            case 'fo':
                self.__tr.fo_00200.modify(self._a[a_id].a_no, self._c.apw, code, qty, price, org_order_no)
            case _:
                self._exception(self._w_msg('modify', f"not support account type; {self._a[a_id].a_type}"))

    def cancel(self, a_id, _mode, code, qty, org_order_no):
        if a_id not in self._a:
            self._exception(self._w_msg('cancel', f"account id error; {a_id}"))
        logger.info(f"cancel; {a_id, code, qty, org_order_no}")

        match self._a[a_id].a_type:
            case 'stock':
                self.__tr.st_00800.cancel(self._a[a_id].a_no, self._c.apw, code, qty, org_order_no)
            case 'fo':
                self.__tr.fo_00300.cancel(self._a[a_id].a_no, self._c.apw, code, qty, org_order_no)
            case _:
                self._exception(self._w_msg('cancel', f"not support account type; {self._a[a_id].a_type}"))

    def account_validation(self, acc_no: str) -> bool:
        return acc_no in self.__account_numbers

    def login(self):
        if self.__xing.login_state is True:
            return

        self.__xing.__event = False
        if self.__xing.ConnectServer(self._c.server_address, 0) is False:
            raise Exception(f"{self._c.server_address} 연결실패")

        self.__xing.__event = False
        self.__xing.Login(self._c.id, self._c.pw, self._c.ppw, 0, False)
        self.__xing.wait_receive_message()
        if self.__xing.login_state is False:
            raise Exception(f"{self._c.server_address} 로그인 실패")

        self.__account_numbers = list()
        for i in range(self.__xing.GetAccountListCount()):
            self.__account_numbers.append(self.__xing.GetAccountList(i))
            logger.debug(f"account; {self.__account_numbers[-1]}")

    def __disconnect(self):
        logger.info(f"disconnect 시작")
        self.__xing.__event = False
        self.__xing.DisconnectServer()
        # self.__session.wait_receive_message()     # 이벤트가 발생하지 않음.
        logger.info(f"disconnect 종료")

    def stop(self):
        if self.__tr:
            self.__tr.stop()

    def logout(self):
        self.__xing.Logout()
        self.__disconnect()
