from config_dir import ConfigDir
from fo_ebest import Tr2105Real, TrCFOAT00300, TrCFOAT00200, TrCFOAT00100, Tr0441, TrCFOAQ00600, RealFo
from my_logger import logger
from utils import RealPrice, MatchItemStock, BalanceItemStock
from xing_basic import XAQuery3
from xing_real import RealStock


class _TrInterval:
    """
    각 TR별 대기 시간을 정의
    """
    def __init__(self, demo):
        self.__demo = demo
        self.__info = ConfigDir.load_yaml('../../xing_interval.yaml')

    def i(self, t_no: str) -> float:
        key = f"{t_no}{'.demo' if self.__demo else ''}"
        return self.__info[key]

    def p(self, t_no: str) -> list:
        key = f"{t_no}{'.demo' if self.__demo else ''}.period"
        return self.__info[key]


class EBestPack:
    def __init__(self, demo: bool, match):
        self.real = dict()
        self.t = _TrInterval(demo=demo)

        self.st_1101_real = Tr1101Real(interval=self.t.i('1101'), period=self.t.p('1101'))  # 주식현재가호가조회 - real 전용
        self.st_1101_real.real = self.real

        self.st_8436 = Tr8436(interval=self.t.i('8436'), period=self.t.p('8436'))  # 주식종목조회 API용
        self.st_0424 = Tr0424(interval=self.t.i('0424'), period=self.t.p('0424'))  # 주식잔고2

        self.st_00600 = TrCSPAT00600(interval=self.t.i('00600'), period=self.t.p('00600'), match=match)  # 현물주문
        self.st_00700 = TrCSPAT00700(interval=self.t.i('00700'), period=self.t.p('00700'), match=match)  # 현물정정주문
        self.st_00800 = TrCSPAT00800(interval=self.t.i('00800'), period=self.t.p('00800'), match=match)  # 현물취소주문

        self.st_13700 = TrCSPAQ13700(interval=self.t.i('13700'), period=self.t.p('13700'))  # 현물계좌주문체결내역조회

        # note; 로그인이 되어 있어야 실행 가능 =======================================================
        self.st_8436.download()
        self.real_st = RealStock(tr1101=self.st_1101_real, all_stock_codes=self.st_8436.results)

    def stop(self):
        self.real_st.stop()


# =========================================================================================
# =========================================================================================


class TrCSPAQ13700:
    """
    BEGIN_FUNCTION_MAP
        .Func,현물계좌주문체결내역조회,CSPAQ13700,SERVICE=CSPAQ13700,headtype=B,CREATOR=이상은,CREDATE=2015/04/13 08:39:53;
        BEGIN_DATA_MAP
        CSPAQ13700InBlock1,In(*EMPTY*),input;
        begin
            레코드갯수, RecCnt, RecCnt, long, 5
            계좌번호, AcntNo, AcntNo, char, 20;
            입력비밀번호, InptPwd, InptPwd, char, 8;
            주문시장코드, OrdMktCode, OrdMktCode, char, 2;
            매매구분, BnsTpCode, BnsTpCode, char, 1;
            종목번호, IsuNo, IsuNo, char, 12;
            체결여부, ExecYn, ExecYn, char, 1;
            주문일, OrdDt, OrdDt, char, 8;
            시작주문번호2, SrtOrdNo2, SrtOrdNo2, long, 10;
            역순구분, BkseqTpCode, BkseqTpCode, char, 1;
            주문유형코드, OrdPtnCode, OrdPtnCode, char, 2;
        end
        CSPAQ13700OutBlock1,In(*EMPTY*),output;
        begin
            레코드갯수, RecCnt, RecCnt, long, 5
            계좌번호, AcntNo, AcntNo, char, 20;
            입력비밀번호, InptPwd, InptPwd, char, 8;
            주문시장코드, OrdMktCode, OrdMktCode, char, 2;
            매매구분, BnsTpCode, BnsTpCode, char, 1;
            종목번호, IsuNo, IsuNo, char, 12;
            체결여부, ExecYn, ExecYn, char, 1;
            주문일, OrdDt, OrdDt, char, 8;
            시작주문번호2, SrtOrdNo2, SrtOrdNo2, long, 10;
            역순구분, BkseqTpCode, BkseqTpCode, char, 1;
            주문유형코드, OrdPtnCode, OrdPtnCode, char, 2;
        end
        CSPAQ13700OutBlock2,OUT1(*EMPTY*),output;
        begin
            레코드갯수, RecCnt, RecCnt, long, 5
            매도체결금액, SellExecAmt, SellExecAmt, long, 16;
            매수체결금액, BuyExecAmt, BuyExecAmt, long, 16;
            매도체결수량, SellExecQty, SellExecQty, long, 16;
            매수체결수량, BuyExecQty, BuyExecQty, long, 16;
            매도주문수량, SellOrdQty, SellOrdQty, long, 16;
            매수주문수량, BuyOrdQty, BuyOrdQty, long, 16;
        end
        CSPAQ13700OutBlock3,OUT(*EMPTY*),output,occurs;
        begin
            주문일, OrdDt, OrdDt, char, 8;
            관리지점번호, MgmtBrnNo, MgmtBrnNo, char, 3;
            주문시장코드, OrdMktCode, OrdMktCode, char, 2;
            주문번호, OrdNo, OrdNo, long, 10;
            원주문번호, OrgOrdNo, OrgOrdNo, long, 10;
            종목번호, IsuNo, IsuNo, char, 12;
            종목명, IsuNm, IsuNm, char, 40;
            매매구분, BnsTpCode, BnsTpCode, char, 1;
            매매구분, BnsTpNm, BnsTpNm, char, 10;
            주문유형코드, OrdPtnCode, OrdPtnCode, char, 2;
            주문유형명, OrdPtnNm, OrdPtnNm, char, 40;
            주문처리유형코드, OrdTrxPtnCode, OrdTrxPtnCode, long, 9;
            주문처리유형명, OrdTrxPtnNm, OrdTrxPtnNm, char, 50;
            정정취소구분, MrcTpCode, MrcTpCode, char, 1;
            정정취소구분명, MrcTpNm, MrcTpNm, char, 10;
            정정취소수량, MrcQty, MrcQty, long, 16;
            정정취소가능수량, MrcAbleQty, MrcAbleQty, long, 16;
            주문수량, OrdQty, OrdQty, long, 16;
            주문가격, OrdPrc, OrdPrc, double, 15.2;
            체결수량, ExecQty, ExecQty, long, 16;
            체결가, ExecPrc, ExecPrc, double, 15.2;
            체결처리시각, ExecTrxTime, ExecTrxTime, char, 9;
            최종체결시각, LastExecTime, LastExecTime, char, 9;
            호가유형코드, OrdprcPtnCode, OrdprcPtnCode, char, 2;
            호가유형명, OrdprcPtnNm, OrdprcPtnNm, char, 40;
            주문조건구분, OrdCndiTpCode, OrdCndiTpCode, char, 1;
            전체체결수량, AllExecQty, AllExecQty, long, 16;
            통신매체코드, RegCommdaCode, RegCommdaCode, char, 2;
            통신매체명, CommdaNm, CommdaNm, char, 40;
            회원번호, MbrNo, MbrNo, char, 3;
            예약주문여부, RsvOrdYn, RsvOrdYn, char, 1;
            대출일, LoanDt, LoanDt, char, 8;
            주문시각, OrdTime, OrdTime, char, 9;
            운용지시번호, OpDrtnNo, OpDrtnNo, char, 12;
            주문자ID, OdrrId, OdrrId, char, 16;
        end
        END_DATA_MAP
    END_FUNCTION_MAP
    """
    def __init__(self, interval=1.1, period=(660, 200)):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 현물계좌주문체결내역조회",
                              receive_data=self.__receive_data, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\CSPAQ13700.res')

        self.__com.SetFieldData('CSPAQ13700InBlock1', 'RecCnt', 0, '00001')
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'OrdMktCode', 0, '00')
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'BnsTpCode', 0, '0')
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'IsuNo', 0, '')
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'SrtOrdNo2', 0, '999999999')
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'BkseqTpCode', 0, '0')  # 0; 역수, 1; 정순 > 정순동작 안함..ㅠ
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'OrdPtnCode', 0, '00')

        self.__size = 0
        self.__prev_size = 0
        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, acc_no, pw, mode=0):
        from datetime import date
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'OrdDt', 0, date.today().strftime('%Y%m%d'))  # 주문일
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'AcntNo', 0, acc_no)  # 계좌번호
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'InptPwd', 0, pw)  # 계좌비번
        self.__com.SetFieldData('CSPAQ13700InBlock1', 'ExecYn', 0, mode)  # 0.전체, 1.체결, 3.미체결

        self.__records = list()
        self.__prev_size = 0
        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")

        while True:
            self.__com.wait_receive_message()
            if self.__size == 0:
                break
            if self.__size <= self.__prev_size:
                break
            self.__prev_size = self.__size
            ret = self.__com.tRequest(True)
            if ret < 0:
                raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")

    def __receive_msg(self, com, error, msg_code, msg):
        pass

    def __receive_data(self, com, tr_code):
        logger.debug(f"{self.__class__.__name__}; {tr_code}")

        self.__size = int(com.GetBlockCount('CSPAQ13700OutBlock3'))
        for i in range(self.__size):
            ord_no = com.GetFieldData('CSPAQ13700OutBlock3', 'OrdNo', i)  # 주문번호
            isu_no = com.GetFieldData('CSPAQ13700OutBlock3', 'IsuNo', i)  # 종목코드
            isu_nm = com.GetFieldData('CSPAQ13700OutBlock3', 'IsuNm', i)  # 종목명
            bns_tp_code = com.GetFieldData('CSPAQ13700OutBlock3', 'BnsTpCode', i)  # 매매구분
            # bns_tp_nm = com.GetFieldData('CSPAQ13700OutBlock3', 'BnsTpNm', i)  # 매매구분
            # OrdQty = int(com.GetFieldData('CSPAQ13700OutBlock3', 'OrdQty', i))  # 주문수량
            ord_prc = com.GetFieldData('CSPAQ13700OutBlock3', 'OrdPrc', i)  # 주문가격
            exec_qty = com.GetFieldData('CSPAQ13700OutBlock3', 'ExecQty', i)  # 체결수량
            # ExecPrc = com.GetFieldData('CSPAQ13700OutBlock3', 'ExecPrc', i)  # 체결가격
            mrc_able_qty = com.GetFieldData('CSPAQ13700OutBlock3', 'MrcAbleQty', i)  # 미체결량
            # OrgOrdNo = self.GetFieldData('CSPAQ13700OutBlock3', 'OrgOrdNo', i)  # 원주문번호 => 값이없음.

            # logger.debug(f"{ord_no, bns_tp_code, isu_no, ord_prc, exec_qty, mrc_able_qty}")
            # 주식 >> 주문번호, 매매구분, 종목코드, 주문가격, 체결수량, 미체결수량
            self.__records.append(MatchItemStock(ord_no=int(ord_no), mode='매도' if bns_tp_code == '1' else '매수',
                                                 code=isu_no[1:], price=int(float(ord_prc)),
                                                 qty_m=int(exec_qty), qty_um=int(mrc_able_qty)))

    def output(self):
        logger.debug(f"{self.__class__.__name__} > record size; {len(self.__records)}")
        for r in self.__records:
            logger.debug(f"{r}")


class TrCSPAT00800:
    """
    현물취소주문
    """
    def __init__(self, interval, period, match):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 현물취소주문",
                              receive_data=None, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\CSPAT00800.res')
        self.__match = match

    def cancel(self, acc_no, pw, code, qty, org_id):
        self.__com.SetFieldData('CSPAT00800InBlock1', 'AcntNo', 0, acc_no)  # 계좌번호
        self.__com.SetFieldData('CSPAT00800InBlock1', 'InptPwd', 0, pw)  # 계좌비번

        self.__com.SetFieldData('CSPAT00800InBlock1', 'OrgOrdNo', 0, org_id)  # 원주문번호
        self.__com.SetFieldData('CSPAT00800InBlock1', 'IsuNo', 0, 'A' + code)  # 종목번호
        self.__com.SetFieldData('CSPAT00800InBlock1', 'OrdQty', 0, qty)  # 주문수량

        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        self.__com.wait_receive_message()

    def __receive_msg(self, com, error, msg_code, msg):
        logger.info(f"receive msg; {self.__class__.__name__} > {com.tr_name} {error} [{msg_code}]; {msg.strip()}")
        self.__match.second(second=f"CANCEL RETURN({error}); {msg.strip()}")


class TrCSPAT00700:
    """
    현물정정주문
    """
    def __init__(self, interval, period, match):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 현물정정주문",
                              receive_data=None, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\CSPAT00700.res')
        self.__match = match

        self.__com.SetFieldData('CSPAT00700InBlock1', 'OrdprcPtnCode', 0, '00')  # 호가유형코드, 지정가
        self.__com.SetFieldData('CSPAT00700InBlock1', 'OrdCndiTpCode', 0, '0')  # 주문조건구분; 0:없음,1:IOC,2:FOK

    def modify(self, acc_no, pw, code, qty, price, org_id):
        self.__com.SetFieldData('CSPAT00700InBlock1', 'AcntNo', 0, acc_no)  # 계좌번호
        self.__com.SetFieldData('CSPAT00700InBlock1', 'InptPwd', 0, pw)  # 계좌비번

        self.__com.SetFieldData('CSPAT00700InBlock1', 'OrgOrdNo', 0, org_id)  # 원주문번호
        self.__com.SetFieldData('CSPAT00700InBlock1', 'IsuNo', 0, 'A' + code)  # 종목번호
        self.__com.SetFieldData('CSPAT00700InBlock1', 'OrdPrc', 0, price)  # 주문가 => 호가구분...
        self.__com.SetFieldData('CSPAT00700InBlock1', 'OrdQty', 0, qty)  # 주문수량

        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        self.__com.wait_receive_message()

    def __receive_msg(self, com, error, msg_code, msg):
        logger.info(f"receive msg; {self.__class__.__name__} > {com.tr_name} {error} [{msg_code}]; {msg.strip()}")
        self.__match.second(second=f"MODIFY RETURN({error}); {msg.strip()}")


class TrCSPAT00600:
    """
    현물주문
    """
    def __init__(self, interval, period, match):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 현물주문",
                              receive_data=None, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\CSPAT00600.res')
        self.__match = match

        self.__com.SetFieldData('CSPAT00600InBlock1', 'MgntrnCode', 0, '000')  # 신용거래코드
        self.__com.SetFieldData('CSPAT00600InBlock1', 'LoanDt', 0, '')  # 대출일
        self.__com.SetFieldData('CSPAT00600InBlock1', 'OrdprcPtnCode', 0, '00')  # 호가유형, 지정가
        self.__com.SetFieldData('CSPAT00600InBlock1', 'OrdCndiTpCode', 0, '0')  # 0:없음,1:IOC,2:FOK

    def order(self, acc_no, pw, mode, code, qty, price):
        self.__com.SetFieldData('CSPAT00600InBlock1', 'AcntNo', 0, acc_no)  # 계좌번호
        self.__com.SetFieldData('CSPAT00600InBlock1', 'InptPwd', 0, pw)  # 계좌비번

        self.__com.SetFieldData('CSPAT00600InBlock1', 'BnsTpCode', 0, mode)  # 매매구분 1;매도, 2; 매수
        self.__com.SetFieldData('CSPAT00600InBlock1', 'IsuNo', 0, 'A' + code)  # 종목번호
        self.__com.SetFieldData('CSPAT00600InBlock1', 'OrdPrc', 0, price)  # 주문가 => 호가구분...
        self.__com.SetFieldData('CSPAT00600InBlock1', 'OrdQty', 0, qty)  # 주문수량

        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        self.__com.wait_receive_message()

    def __receive_msg(self, com, error, msg_code, msg):
        logger.info(f"receive msg; {self.__class__.__name__} > {com.tr_name} {error} [{msg_code}]; {msg.strip()}")
        self.__match.second(second=f"ORDER RETURN({error}); {msg.strip()}")


class Tr0424:
    """
    주식잔고2
    """
    def __init__(self, interval, period):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 주식잔고2",
                              receive_data=self.__receive_data, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\t0424.res')

        self.__cts_expcode = ''
        self.__com.SetFieldData('t0424InBlock', 'prcgb', 0, '1')  # 단가구분
        self.__com.SetFieldData('t0424InBlock', 'chegb', 0, '0')  # 체결기준
        self.__com.SetFieldData('t0424InBlock', 'dangb', 0, '0')  # 단일가 구분
        self.__com.SetFieldData('t0424InBlock', 'charge', 0, '1')  # 제비용 포함
        self.__com.SetFieldData('t0424InBlock', 'cts_expcode', 0, self.__cts_expcode)  # 연속조회시 사용

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, acc_no, pw):
        self.__com.SetFieldData('t0424InBlock', 'accno', 0, acc_no)  # 계좌번호
        self.__com.SetFieldData('t0424InBlock', 'passwd', 0, pw)     # 계좌비번

        self.__records = list()
        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        while True:
            self.__com.wait_receive_message()
            if self.__cts_expcode == '':
                break

            self.__com.SetFieldData('t0424InBlock', 'cts_expcode', 0, self.__cts_expcode)  # 연속조회시 사용
            ret = self.__com.tRequest(True)  # False
            if ret < 0:
                raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        self.__records.sort()

    def __receive_msg(self, com, error, msg_code, msg):
        pass

    def __receive_data(self, com, tr_code):
        logger.debug(f"{self.__class__.__name__}; {tr_code}")
        self.__cts_expcode = com.GetFieldData('t0424OutBlock', 'cts_expcode', 0)  # 연속조회시 사용

        for i in range(com.GetBlockCount('t0424OutBlock1')):
            code = com.GetFieldData('t0424OutBlock1', 'expcode', i)  # 종목
            name = com.GetFieldData('t0424OutBlock1', 'hname', i)  # 종목명 => 삭제필요...
            # janqty = int(__com.GetFieldData('t0424OutBlock1', 'janqty', i))  # 수량
            mdposqt = com.GetFieldData('t0424OutBlock1', 'mdposqt', i)  # 매도가능수량
            price = com.GetFieldData('t0424OutBlock1', 'price', i)  # 현재가
            pamt = com.GetFieldData('t0424OutBlock1', 'pamt', i)  # 평균단가
            appamt = com.GetFieldData('t0424OutBlock1', 'appamt', i)  # 평가금액
            sunikrt = com.GetFieldData('t0424OutBlock1', 'sunikrt', i)  # 수익율
            # jonggb = __com.GetFieldData('t0424OutBlock1', 'jonggb', i)  # 종목구분; '2':코스닥, '3':거래소

            logger.debug(f"{code, name, mdposqt, price, pamt, appamt, sunikrt}")
            if int(mdposqt) == 0:
                continue
            self.__records.append(BalanceItemStock(code=code, name=name, qty=int(mdposqt),
                                                   price=int(price), mean=int(pamt),
                                                   eval=int(appamt), rate=float(sunikrt)))
            # ======================================== '''

    def output(self):
        logger.debug(f"{self.__class__.__name__} > record size; {len(self.__records)}")
        for r in self.__records:
            logger.debug(f"{r}")


class Tr8436:
    """
    주식종목조회 API용
    """
    def __init__(self, interval, period):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 주식종목조회 API용",
                              receive_data=self.__receive_data, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\t8436.res')

        self.kospi = set()
        self.kosdaq = set()
        self.etf_etn = set()

        self.__records = list()

    @property
    def results(self) -> list:
        return self.__records

    def download(self, mode_=0):
        if mode_ not in (0, 1, 2, ):
            raise Exception(f"{self.__class__.__name__} Error mode only 0, 1, 2; {mode_}")
        self.__com.SetFieldData('t8436InBlock', 'gubun', 0, mode_)  # 구분(0:전체, 1:코스피, 2:코스닥)
        self.__records = list()
        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        self.__com.wait_receive_message()

    def __receive_msg(self, com, error, msg_code, msg):
        pass

    def __receive_data(self, com, tr_code):
        """
            종목명,hname,hname,char,20;
            단축코드,shcode,shcode,char,6;
            확장코드,expcode,expcode,char,12;
            ETF구분(1:ETF, 2:ETN),etfgubun,etfgubun,char,1;
            상한가,uplmtprice,uplmtprice,long,8;
            하한가,dnlmtprice,dnlmtprice,long,8;
            전일가,jnilclose,jnilclose,long,8;
            주문수량단위,memedan,memedan,char,5;
            기준가,recprice,recprice,long,8;
            구분(1:코스피, 2:코스닥),gubun,gubun,char,1;
            증권그룹,bu12gubun,bu12gubun,char,2;
            기업인수목적회사여부(Y/N),spac_gubun,spac_gubun,char,1;
            filler(미사용),filler,filler,char,32;
        """
        logger.debug(f"{self.__class__.__name__}; {tr_code}")

        for i in range(com.GetBlockCount('t8436OutBlock')):
            hname = com.GetFieldData('t8436OutBlock', 'hname', i)  # 종목명
            shcode = com.GetFieldData('t8436OutBlock', 'shcode', i)  # 단축코드
            expcode = com.GetFieldData('t8436OutBlock', 'expcode', i)  # 확장코드
            etfgubun = com.GetFieldData('t8436OutBlock', 'etfgubun', i)  # ETF구분(1:ETF, 2:ETN)
            gubun = com.GetFieldData('t8436OutBlock', 'gubun', i)  # 구분(1:코스피, 2:코스닥)

            self.__records.append([shcode, hname, expcode, etfgubun, gubun, ])

        self.kospi = {r[0] for r in self.__records if r[3] == '0' and r[4] == '1'}
        self.kosdaq = {r[0] for r in self.__records if r[3] == '0' and r[4] == '2'}
        self.etf_etn = {r[0] for r in self.__records if r[3] != '0'}

    def output(self):
        logger.debug(f"{self.__class__.__name__} > record size; {len(self.__records)}")
        for r in self.__records:
            logger.debug(r)


class Tr1101Real:
    """
    주식현재가호가조회(t1101),t1101,attr,block,headtype=A;
    """
    def __init__(self, interval, period):
        self.__com = XAQuery3(f"{self.__class__.__name__}; 주식현재가호가조회",
                              receive_data=self.__receive_data, receive_msg=self.__receive_msg,
                              interval=interval, period_limit=period)
        self.__com.LoadFromResFile('Res\\t1101.res')
        self.real = dict()

    def download(self, code):
        if code not in self.real:
            self.real[code] = RealPrice(cur_price=0, sell_price=0, buy_price=0)
        self.__com.SetFieldData('t1101InBlock', 'shcode', 0, code)  # 종목코드

        ret = self.__com.tRequest(False)
        if ret < 0:
            raise Exception(f"{self.__class__.__name__} 전송에러 : {ret}")
        self.__com.wait_receive_message()

    def __receive_msg(self, com, error, msg_code, msg):
        pass

    def __receive_data(self, com, tr_code):
        logger.debug(f"{self.__class__.__name__}; {tr_code}")

        code = com.GetFieldData('t1101OutBlock', 'shcode', 0)
        self.real[code].sell_price = int(com.GetFieldData('t1101OutBlock', 'offerho1', 0))
        self.real[code].buy_price = int(com.GetFieldData('t1101OutBlock', 'bidho1', 0))
        self.real[code].cur_price = self.real[code].buy_price

