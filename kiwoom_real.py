from utils import RealPrice


class KiwoomRealPrice:
    """
    [화면번호]
    서버에 데이터를 요청하거나, 주문을 발생시킬때 사용합니다.
    화면번호는 서버의 결과를 수신할때 어떤 요청에 의한 수신인지를 구별하기 위한 키값의 개념입니다.
    0000을 제외한 임의의 숫자(4자리)를 자유롭게 사용하시면 됩니다.

    ※ 화면번호 사용시 주의할 점 :
    같은 화면번호로 데이터 요청을 빠르게 반복하는 경우 데이터의 유효성을 보장할 수 없습니다.
    최소한 2개이상의 화면번호를 번갈아가며 또는 매번 새로운 화면번호를 사용하시기 바랍니다.
    사용자 프로그램에서 사용할 수 있는 화면번호 갯수가 200개로 한정되어 있습니다.
    이 갯수를 넘는 경우 데이터의 유효성을 보장할 수 없습니다.
    (구현하시는 프로그램 성격상  화면번호 갯수가 200개가 넘어야 하는 경우, 이전에 사용되었던 화면번호를 재사용 하는 방식으로 구현해야 합니다.)

    고정된 값을 real 로 사용
        종목 - 현재가, 매도호가, 매수호가
        업종 - 현재가
    """
    def __init__(self, ocx):
        self.__ocx = ocx

        self.__real = dict()

        self.__s_pos = 0
        self.__screen = [i + self.__ocx.screen_start + self.__ocx.screen_query
                         for i in range(self.__ocx.screen_price)]

    @property
    def real(self) -> dict:
        return self.__real

    @property
    def __screen_no(self) -> int:
        self.__s_pos = self.__s_pos + 1 if self.__s_pos + 1 < len(self.__screen) else 0
        return self.__screen[self.__s_pos]

    def register(self, code, fids='41'):
        if code in self.__real:
            return
        self.__real[code] = RealPrice(cur_price=0, sell_price=0, buy_price=0)
        if len(code) == len('000660'):     # 주식
            self.__ocx.tr.opt10004_real.download(code)
        elif len(code) == len('101V3000'):  # 선옵
            self.__ocx.tr.opt50001_real.download(code)
        else:
            raise Exception(f"Not Support Type; {code}")
        real_type = 0 if len(self.__real) <= len(self.__screen) else 1
        self.__ocx.set_real_reg(self.__screen_no, code, fids, real_type)

    def receive_real_data(self, code, real_type):
        match real_type:
            case '주식호가잔량':
                self.__real[code].sell_price = abs(int(self.__ocx.get_comm_real_data(code, 41)))
                self.__real[code].buy_price = abs(int(self.__ocx.get_comm_real_data(code, 51)))
                self.__real[code].cur_price = self.__ocx.real[code].buy_price
            case '선물호가잔량':
                self.__real[code].sell_price = abs(float(self.__ocx.get_comm_real_data(code, 41)))
                self.__real[code].buy_price = abs(float(self.__ocx.get_comm_real_data(code, 51)))
                self.__real[code].cur_price = self.__ocx.real[code].buy_price
            case '옵션호가잔량':
                self.__real[code].sell_price = abs(float(self.__ocx.get_comm_real_data(code, 41)))
                self.__real[code].buy_price = abs(float(self.__ocx.get_comm_real_data(code, 51)))
                self.__real[code].cur_price = self.__ocx.real[code].buy_price
            case _:
                pass
