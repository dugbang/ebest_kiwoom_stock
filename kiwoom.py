from session import Session
from kiwoom_ocx import KiwoomOcx
from my_logger import logger


class Kiwoom(Session):
    def __init__(self, parent):
        super().__init__(parent)

        self.__ocx: KiwoomOcx = KiwoomOcx(self._c, self._match)

    def _st_load_balance(self, a_id) -> list:
        self.__ocx.tr.opw00018.download(self._a[a_id].a_no)
        return self.__ocx.tr.opw00018.results

    def _fo_load_balance(self, a_id) -> list:
        self.__ocx.tr.opw20007.download(self._a[a_id].a_no)
        return self.__ocx.tr.opw20007.results

    def _st_matching_items(self, a_id) -> list:
        self.__ocx.tr.opt10075.download(self._a[a_id].a_no)
        return self.__ocx.tr.opt10075.results

    def _fo_matching_items(self, a_id) -> list:
        self.__ocx.tr.opw20004.download(self._a[a_id].a_no)
        return self.__ocx.tr.opw20004.results

    def initial(self, parent):
        self._a = parent.accounts

    def login(self):
        self.__ocx.login()

    def stop(self):
        pass

    def cur_price(self, code) -> int | float:
        return self.__ocx.cur_price(code)

    def buy_price(self, code) -> int | float:
        return self.__ocx.buy_price(code)

    def sell_price(self, code) -> int | float:
        return self.__ocx.sell_price(code)

    def order(self, a_id, mode, code, qty, price):
        if a_id not in self._a:
            self._exception(self._w_msg('order', f"account id error; {a_id}"))
        if mode not in ('buy', 'sell'):
            self._exception(self._w_msg('order', f"error mode; {mode}"))

        logger.info(f"order; {a_id, mode, code, qty, price}")
        match self._a[a_id].a_type:
            case 'stock':
                self.__ocx.tr.send_order.order(acc_no=self._a[a_id].a_no, mode=mode,
                                               code=code, qty=qty, price=price)
            case 'fo':
                self.__ocx.tr.send_order_fo.order(acc_no=self._a[a_id].a_no, mode=mode,
                                                  code=code, qty=qty, price=price)
            case _:
                self._exception(self._w_msg('order', f"not support account type; {self._a[a_id].a_type}"))

    def modify(self, a_id, mode, code, qty, price, org_order_no):
        if a_id not in self._a:
            self._exception(self._w_msg('modify', f"account id error; {a_id}"))
        if mode not in ('buy', 'sell'):
            self._exception(self._w_msg('modify', f"error mode; {mode}"))

        logger.info(f"modify; {a_id, mode, code, qty, price}")
        match self._a[a_id].a_type:
            case 'stock':
                self.__ocx.tr.send_order.modify(acc_no=self._a[a_id].a_no, mode=mode,
                                                code=code, qty=qty, price=price, org_order_no=org_order_no)
            case 'fo':
                self.__ocx.tr.send_order_fo.modify(acc_no=self._a[a_id].a_no, mode=mode,
                                                   code=code, qty=qty, price=price, org_order_no=org_order_no)
            case _:
                self._exception(self._w_msg('order', f"not support account type; {self._a[a_id].a_type}"))

    def cancel(self, a_id, mode, code, qty, org_order_no):
        if a_id not in self._a:
            self._exception(self._w_msg('cancel', f"account id error; {a_id}"))
        if mode not in ('buy', 'sell'):
            self._exception(self._w_msg('cancel', f"error mode; {mode}"))

        logger.info(f"cancel; {a_id, mode, code, qty}")
        match self._a[a_id].a_type:
            case 'stock':
                self.__ocx.tr.send_order.cancel(acc_no=self._a[a_id].a_no, mode=mode,
                                                code=code, qty=qty, org_order_no=org_order_no)
            case 'fo':
                self.__ocx.tr.send_order_fo.cancel(acc_no=self._a[a_id].a_no, mode=mode,
                                                   code=code, qty=qty, org_order_no=org_order_no)
            case _:
                self._exception(self._w_msg('order', f"not support account type; {self._a[a_id].a_type}"))

    def account_validation(self, acc_no: str) -> bool:
        return self.__ocx.account_validation(acc_no)

    def logout(self):
        pass
