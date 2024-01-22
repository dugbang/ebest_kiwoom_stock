from fo_kiwoom import Opw20007, SendOrderFO, Opt50001Real, Opw20004
from my_logger import logger
from utils import BalanceItemStock, MatchItemStock


class KiwoomPack:
    """
    - TR 묶음.
    """
    def __init__(self, ocx, match):
        self.opw00018 = Opw00018(ocx)    # 계좌평가잔고내역요청
        self.opt10075 = Opt10075(ocx)    # 미체결요청

        self.opt10004_real = Opt10004Real(ocx)    # 주식호가요청 - real 전용
        self.send_order = SendOrder(ocx, match)

        # ============================================================================
        self.opt10085 = Opt10085(ocx)    # 계좌수익률요청
        self.opt10001 = Opt10001(ocx)    # 주식기본정보요청
        self.opt10081 = Opt10081(ocx)    # 주식일봉차트조회요청
        self.opt20001_real = Opt20001Real(ocx)    # 업종현재가요청 - real 전용


# =================================================================================
# =================================================================================
# =================================================================================
class Opt10004Real:
    """
    [ OPT10004 : 주식호가요청 ]

    1. Open API 조회 함수 입력값을 설정합니다.
        종목코드 = 전문 조회할 종목코드
        SetInputValue("종목코드"	,  "입력값 1");

    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPT10004"	,  "0"	,  "화면번호");
    """
    def __init__(self, ocx):
        self.__rq_name = 'opt10004_req'
        self.__tr_code = 'opt10004'
        self.__next = '0'
        self.__code = ''

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

    def download(self, code):
        self.__next = '0'
        self.__code = code
        self.__ocx.set_input_value('종목코드', code)
        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        pass
        # logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        sell_0 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '매도최우선호가')
        buy_0 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '매수최우선호가')

        if self.__code in self.__ocx.real:
            self.__ocx.real[self.__code].sell_price = abs(int(sell_0))
            self.__ocx.real[self.__code].buy_price = abs(int(buy_0))
            self.__ocx.real[self.__code].cur_price = abs(int(buy_0))
        else:
            logger.warning(f"Error Real Key; {self.__code}, price; {buy_0}")


class Opw00018:
    """
    [ OPW00018 : 계좌평가잔고내역요청 ]

    [ 주의 ]
    "수익률%" 데이터는 모의투자에서는 소숫점표현, 실거래서버에서는 소숫점으로 변환 필요 합니다.

    1. Open API 조회 함수 입력값을 설정합니다.
        계좌번호 = 전문 조회할 보유계좌번호
        SetInputValue("계좌번호"	,  "입력값 1");

        비밀번호 = 사용안함(공백)
        SetInputValue("비밀번호"	,  "입력값 2");

        비밀번호입력매체구분 = 00
        SetInputValue("비밀번호입력매체구분"	,  "입력값 3");

        조회구분 = 1:합산, 2:개별
        SetInputValue("조회구분"	,  "입력값 4");

    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPW00018"	,  "0"	,  "화면번호");
    """
    def __init__(self, ocx):
        self.__rq_name = 'opw00018_req'
        self.__tr_code = 'opw00018'
        self.__next = '0'

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, acc_no, gubun=1):
        self.__records = list()
        self.__next = '0'
        self.__ocx.set_input_value('계좌번호', acc_no)
        self.__ocx.set_input_value('비밀번호', '')       # 사용안함(공백)
        self.__ocx.set_input_value('비밀번호입력매체구분', '00')
        self.__ocx.set_input_value('조회구분', gubun)    # 1:합산, 2:개별
        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

        while self.is_next:
            self.__ocx.set_input_value('계좌번호', acc_no)
            self.__ocx.set_input_value('비밀번호', '')  # 사용안함(공백)
            self.__ocx.set_input_value('비밀번호입력매체구분', '00')
            self.__ocx.set_input_value('조회구분', gubun)  # 1:합산, 2:개별
            self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        # self.buy_money = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '총매입금액'))
        # self.eval_money = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '총평가금액'))
        # self.total_profit = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '총평가손익금액'))
        # self.total_ratio = float(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '총수익률(%)'))
        # self.predict_asset = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '추정예탁자산'))
        # self.total_lend = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '총대출금'))
        # self.total_lend_2 = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '총대주금액'))
        # self.count = int(self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '조회건수'))
        #
        # self.total_ratio = self.total_ratio if self.__ocx.config.demo else self.total_ratio / 100
        # logger.debug(f"{self.buy_money, self.eval_money, self.total_profit, self.total_ratio}, "
        #              f"{self.predict_asset, self.total_lend, self.total_lend_2, self.count}")

        for i in range(self.__ocx.get_repeat_cnt(self.__tr_code, self.__rq_name)):
            code = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '종목번호')
            name = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '종목명')
            # profit = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '평가손익')
            rate = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '수익률(%)')
            # prev_close = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '전일종가')
            qty = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매매가능수량')
            price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '현재가')
            # p_qty_1 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '전일매도수량')
            # p_qty_2 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '전일매수수량')
            # t_qty_1 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '금일매도수량')
            # t_qty_2 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '금일매수수량')
            money_i = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매입금액')
            # fee_i = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매입수수료')
            money_e = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '평가금액')
            # fee_e = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '평가수수료')
            # tax = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '세금')
            # fee = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '수수료합')
            # portion = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '보유비중(%)')
            # credit_b = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '신용구분')
            # credit_m = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '신용구분명')
            # ex_date = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '대출일')

            self.__records.append(BalanceItemStock(code=code[1:], name=name, qty=int(qty),
                                                   price=int(price), mean=int(money_i) // int(qty),
                                                   eval=int(money_e), rate=float(rate)))
            # self.results.append((code[1:], name, int(profit), rate, int(prev_close), int(qty),
            #                      int(price), int(p_qty_1), int(p_qty_2), int(t_qty_1), int(t_qty_2),
            #                      int(money_i), int(fee_i), int(money_e), int(fee_e), int(tax), int(fee),
            #                      float(portion), credit_b, credit_m, ex_date))

    def output(self):
        logger.debug(f"{self.__class__.__name__} > record size; {len(self.__records)}")
        for r in self.__records:
            logger.debug(f"{r}")


class SendOrder:
    def __init__(self, ocx, match):
        self.__rq_name = 'send_order_req'
        self.__tr_code = 'send_order'
        self.__next = '0'

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

        self.__match = match

    def order(self, acc_no, mode, code, qty, price) -> int:
        order_type = 1 if mode == 'buy' else 2
        return self.__ocx.send_order(self.__rq_name, acc_no,
                                     code, qty, price, order_type)

    def cancel(self, acc_no, mode, code, qty, org_order_no) -> int:
        order_type = 3 if mode == 'buy' else 4
        return self.__ocx.send_order(self.__rq_name, acc_no,
                                     code, qty, 0, order_type, org_order_no=org_order_no)

    def modify(self, acc_no, mode, code, qty, price, org_order_no) -> int:
        order_type = 5 if mode == 'buy' else 6
        return self.__ocx.send_order(self.__rq_name, acc_no,
                                     code, qty, price, order_type, org_order_no=org_order_no)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}, match key; {self.__match.key}")
        self.__match.second(second=f"SendOrder >> {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")


class Opt10075:
    """
    [ OPT10075 : 미체결요청 ]

    1. Open API 조회 함수 입력값을 설정합니다.
        계좌번호 = 전문 조회할 보유계좌번호
        SetInputValue("계좌번호"	,  "입력값 1");

        전체종목구분 = 0:전체, 1:종목
        SetInputValue("전체종목구분"	,  "입력값 2");

        매매구분 = 0:전체, 1:매도, 2:매수
        SetInputValue("매매구분"	,  "입력값 3");

        종목코드 = 전문 조회할 종목코드 (공백허용, 공백입력시 전체종목구분 "0" 입력하여 전체 종목 대상으로 조회)
        SetInputValue("종목코드"	,  "입력값 4");

        체결구분 = 0:전체, 2:체결, 1:미체결
        SetInputValue("체결구분"	,  "입력값 5");


    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPT10075"	,  "0"	,  "화면번호");
    """
    def __init__(self, ocx):
        self.__rq_name = 'opt10075_req'
        self.__tr_code = 'opt10075'
        self.__next = '0'

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, acc_no):
        self.__records = list()
        self.__next = '0'
        self.__ocx.set_input_value('계좌번호', acc_no)
        self.__ocx.set_input_value('전체종목구분', 0)    # 0:전체, 1:종목
        self.__ocx.set_input_value('매매구분', 0)   # 0:전체, 1:매도, 2:매수
        self.__ocx.set_input_value('종목코드', 0)   # 전문 조회할 종목코드 (공백허용, 공백입력시 전체종목구분 "0" 입력하여 전체 종목 대상으로 조회)
        self.__ocx.set_input_value('체결구분', 0)   # 0:전체, 2:체결, 1:미체결
        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

        while self.is_next:
            self.__ocx.set_input_value('계좌번호', acc_no)
            self.__ocx.set_input_value('전체종목구분', 0)  # 0:전체, 1:종목
            self.__ocx.set_input_value('매매구분', 0)  # 0:전체, 1:매도, 2:매수
            self.__ocx.set_input_value('종목코드', 0)  # 전문 조회할 종목코드 (공백허용, 공백입력시 전체종목구분 "0" 입력하여 전체 종목 대상으로 조회)
            self.__ocx.set_input_value('체결구분', 0)  # 0:전체, 2:체결, 1:미체결
            self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        for i in range(self.__ocx.get_repeat_cnt(self.__tr_code, self.__rq_name)):
            # acc_no = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '계좌번호')
            order_no = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '주문번호')
            # private_no = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '관리사번')
            code = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '종목코드')
            # gubun = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '업무구분')
            # o_state = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '주문상태')
            # name = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '종목명')
            o_qty = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '주문수량')
            o_price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '주문가격')
            m_qty = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '미체결수량')
            # m_money = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '체결누계금액')
            # org_order_no = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '원주문번호')
            o_gubun = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '주문구분')
            # o_gubun_1 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매매구분')
            # time_ = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '시간')
            # ch_no = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '체결번호')
            # ch_price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '체결가')
            # price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '현재가')
            # ho_price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매도호가')
            # h1_price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매수호가')
            # u_price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '단위체결가')
            # u_qty = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '단위체결량')
            # fee = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '당일매매수수료')
            # tex = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '당일매매세금')
            # private = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '개인투자자')

            self.__records.append(MatchItemStock(ord_no=int(order_no), mode=o_gubun, code=code,
                                                 price=int(o_price), qty_m=int(o_qty) - int(m_qty),
                                                 qty_um=int(m_qty)))
            # self.results.append((acc_no, order_no, private_no, code, gubun, o_state, name, o_qty, o_price, m_qty,
            #                      m_money, org_order_no, o_gubun, o_gubun_1, time_, ch_no, ch_price,
            #                      price, ho_price, h1_price, u_price, u_qty, fee, tex, private))

    def output(self):
        logger.debug(f"{self.__class__.__name__} > record size; {len(self.__records)}")
        for r in self.__records:
            logger.debug(r)


class Opt10085:
    """
    [ OPT10085 : 계좌수익률요청 ]

    1. Open API 조회 함수 입력값을 설정합니다.
        계좌번호 = 전문 조회할 보유계좌번호
        SetInputValue("계좌번호"	,  "입력값 1");

    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPT10085"	,  "0"	,  "화면번호");
    """
    def __init__(self, ocx):
        self.__rq_name = 'opt10085_req'
        self.__tr_code = 'opt10085'
        self.__next = '0'

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, acc_no):
        self.__records = list()
        self.__next = '0'
        self.__ocx.set_input_value('계좌번호', acc_no)
        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

        while self.is_next:
            self.__ocx.set_input_value('계좌번호', acc_no)
            self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        for i in range(self.__ocx.get_repeat_cnt(self.__tr_code, self.__rq_name)):
            date_ = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '일자')
            code = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '종목코드')
            name = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '종목명')
            price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '현재가')
            price_i = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매입가')
            price_im = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '매입금액')
            qty = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '보유수량')
            profit = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '당일매도손익')
            fee = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '당일매매수수료')
            tax = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '당일매매세금')
            credit_b = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '신용구분')
            date_2 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '대출일')
            qty_2 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '결제잔고')
            qty_0 = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '청산가능수량')
            credit_m = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '신용금액')
            credit_p = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '신용이자')
            expiry = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, i, '만기일')

            self.__records.append((date_, code, name, price, price_i, price_im, qty, profit, fee, tax,
                                   credit_b, date_2, qty_2, qty_0, credit_m, credit_p, expiry))

    def output(self):
        logger.debug(f"{self.__class__.__name__} > record size; {len(self.__records)}")
        for r in self.__records:
            logger.debug(f"{r}")


class Opt10001:
    """
    [ OPT10001 : 주식기본정보요청 ]

    [ 주의 ]
    PER, ROE 값들은 외부벤더사에서 제공되는 데이터이며 일주일에 한번 또는 실적발표 시즌에 업데이트 됨

    1. Open API 조회 함수 입력값을 설정합니다.
        종목코드 = 전문 조회할 종목코드
        SetInputValue("종목코드"	,  "입력값 1");

    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPT10001"	,  "0"	,  "화면번호");
    """

    def __init__(self, ocx):
        self.__rq_name = 'opt10001_req'
        self.__tr_code = 'opt10001'
        self.__next = '0'

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, code):
        self.__records = list()
        self.__next = '0'
        self.__ocx.set_input_value('종목코드', code)
        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        code = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '종목코드')
        name = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '종목명')
        # .... 생략
        price = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '현재가')

        self.__records.append((code, name, price))

    def output(self):
        for r in self.__records:
            logger.debug(r)


class Opt10081:
    """
    [ OPT10081 : 주식일봉차트조회요청 ]

    [ 주의 ]
    수정주가이벤트 항목은 데이터 제공되지 않음. 데이터 건수를 지정할 수 없고, 데이터 유무에따라 한번에 최대 600개가 조회됩니다.

    1. Open API 조회 함수 입력값을 설정합니다.
        종목코드 = 전문 조회할 종목코드
        SetInputValue("종목코드"	,  "입력값 1");

        기준일자 = YYYYMMDD (20160101 연도4자리, 월 2자리, 일 2자리 형식)
        SetInputValue("기준일자"	,  "입력값 2");

        수정주가구분 = 0 or 1, 수신데이터 1:유상증자, 2:무상증자, 4:배당락, 8:액면분할, 16:액면병합, 32:기업합병, 64:감자, 256:권리락
        SetInputValue("수정주가구분"	,  "입력값 3");


    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPT10081"	,  "0"	,  "화면번호");
    """
    def __init__(self, ocx):
        self.__rq_name = 'opt10081_req'
        self.__tr_code = 'opt10081'
        self.__next = '0'

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, s_date, code, modify_price=1):
        logger.debug(f"download; {s_date}, {code}")
        self.__records = list()
        self.__next = '0'
        self.__ocx.set_input_value('종목코드', code)
        self.__ocx.set_input_value('기준일자', s_date)
        self.__ocx.set_input_value('수정주가구분', modify_price)
        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

        # note; 계속 받아짐... e_date 등의 별도 종료조건이 필요할 듯
        while self.is_next:
            self.__ocx.set_input_value('종목코드', code)
            self.__ocx.set_input_value('기준일자', s_date)
            self.__ocx.set_input_value('수정주가구분', modify_price)
            self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)
            break

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        for i in range(self.__ocx.get_repeat_cnt(self.__tr_code, self.__rq_name)):
            date = self.__ocx.comm_get_data(self.__tr_code, "", self.__rq_name, i, "일자")
            open_ = self.__ocx.comm_get_data(self.__tr_code, "", self.__rq_name, i, "시가")
            high = self.__ocx.comm_get_data(self.__tr_code, "", self.__rq_name, i, "고가")
            low = self.__ocx.comm_get_data(self.__tr_code, "", self.__rq_name, i, "저가")
            close = self.__ocx.comm_get_data(self.__tr_code, "", self.__rq_name, i, "현재가")
            volume = self.__ocx.comm_get_data(self.__tr_code, "", self.__rq_name, i, "거래량")

            self.__records.append((date, open_, high, low, close, volume))

    def output(self, length=5):
        for r in self.__records[:length]:
            logger.debug(r)


class Opt20001Real:
    """
    [ OPT20001 : 업종현재가요청 ]

    1. Open API 조회 함수 입력값을 설정합니다.
        시장구분 = 0:코스피, 1:코스닥, 2:코스피200
        SetInputValue("시장구분"	,  "입력값 1");

        업종코드 = 001:종합(KOSPI), 002:대형주, 003:중형주, 004:소형주 101:종합(KOSDAQ), 201:KOSPI200, 302:KOSTAR, 701: KRX100 나머지 ※ 업종코드 참고
        SetInputValue("업종코드"	,  "입력값 2");

    2. Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        CommRqData( "RQName"	,  "OPT20001"	,  "0"	,  "화면번호");
    """
    def __init__(self, ocx):
        self.__rq_name = 'opt20001_req'
        self.__tr_code = 'opt20001'
        self.__next = '0'
        self.__code = ''

        self.__ocx = ocx
        self.__ocx.add_receive_handler(self.__rq_name, self.__receive_data)
        self.__ocx.add_message_handler(self.__rq_name, self.__receive_msg)

    def download(self, code):
        self.__next = '0'
        self.__code = code
        self.__ocx.set_input_value('시장구분', self.__market(code))
        self.__ocx.set_input_value('업종코드', code)

        self.__ocx.comm_rq_data(self.__rq_name, self.__tr_code, self.__next)

    @property
    def is_next(self) -> bool:
        return True if self.__next == '2' else False

    def __receive_msg(self, msg):
        logger.debug(f"{self.__class__.__name__}; {msg}")

    def __receive_data(self, next_):
        self.__next = next_
        logger.debug(f"__receive_data; {self.__class__.__name__}, next; {self.is_next}")

        cur = self.__ocx.comm_get_data(self.__tr_code, '', self.__rq_name, 0, '현재가')
        if self.__code in self.__ocx.real:
            self.__ocx.real[self.__code].cur_price = abs(float(cur))
        else:
            logger.warning(f"Error Real Key; {self.__code}, price; {cur}")

    @property
    def up_kospi(self) -> list:
        return self.__ocx.config['up_codes']['kospi']

    @property
    def up_kosdaq(self) -> list:
        return self.__ocx.config['up_codes']['kosdaq']

    @property
    def up_kp200(self) -> list:
        return self.__ocx.config['up_codes']['kp200']

    def __market(self, code):
        if code in self.up_kospi:
            return 0
        elif code in self.up_kosdaq:
            return 2
        elif code in self.up_kp200:
            return 1
        else:
            raise Exception(f"{self.__class__.__name__} >> 지원하지 않는 업종코드; {code}")

