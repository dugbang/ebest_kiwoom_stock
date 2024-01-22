from time import sleep
from timeit import default_timer
from pythoncom import PumpWaitingMessages

from PyQt5.QAxContainer import QAxWidget

from kiwoom_query import KiwoomPack
from kiwoom_real import KiwoomRealPrice
from my_logger import logger


class KiwoomOcx(QAxWidget):
    """
    [기본동작]
    OpenAPI 데이터 요청과 데이터 수신 이벤트는 모두 비동기 방식입니다.
    (반드시 조회요청한 순서대로 수신되지는 않습니다.)
    시세조회나 주문 등 함수호출을 통해 서버로 요청하면 서버의 처리 결과를 그에 맞는 이벤트 발생으로 전달합니다.
    이벤트는 일반함수와 구별하기 위해 "On~" 으로 시작되는 이름을 갖습니다.
    OnEventConnect (로그인처리완료), OnReceiveTRData (조회요청응답), OnReceiveRealData (실시간시세수신)

    [데이터요청과 수신]
    예) 조회요청.
    요청(조회함수 CommRqData 사용자가 호출)  --> 이벤트 발생(OnReceiveTRData) --> 데이터 획득(GetCommData 사용자가 호출)
    예) 조건검색요청.
    요청(조회함수 SendCondition 사용자가 호출)  --> 이벤트 발생(OnReceiveTrCondition)
    예) 주문요청.
    요청(주문함수 SendOrder 사용자가 호출)  --> 이벤트 발생(OnReceiveTRData) --> 이벤트 발생 (OnReceiveChejanData) --> 데이터 획득(GetChejanData 사용자가 호출)

    ※ 이벤트를 임의로 호출해서 사용하는 것은 불가 합니다.


    [계좌번호]
    OpenAPI에서는 10자리의 계좌번호가 사용됩니다.
    영웅문4 등에서는 끝 2자리를 고객님께 노출하지 않고 8자릿수로 제공됩니다.
    OpenAPI에서는 계좌의 끝 2자리를 따로 관리하지 않고
    사용자가 입력한 그대로의 계좌번호를 사용하도록 설계되어 있습니다.
    따라서 데이터 조회 또는 주문시 계좌번호 10자리를 모두 입력해주셔야 합니다.


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
    """
    def __init__(self, config, match):
        super().__init__()

        self.config = config
        self.__account_numbers = list()

        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        self.OnReceiveMsg.connect(self.__receive_msg)
        self.OnEventConnect.connect(self.__handler_login)
        self.OnReceiveTrData.connect(self.__handler_tr_data)
        self.OnReceiveChejanData.connect(self.__handler_chejan_data)
        self.OnReceiveRealData.connect(self.__handler_real_data)

        self.__receive_event = False
        self.__receive_handler = dict()
        self.__message_handler = dict()

        self.__s_pos = 0
        self.__screen = [i + self.screen_start for i in range(self.screen_query)]
        self.__prev_request_time = default_timer()

        self.__real_price: KiwoomRealPrice = KiwoomRealPrice(self)
        self.tr: KiwoomPack = KiwoomPack(self, match)

    @property
    def real(self) -> dict:
        return self.__real_price.real

    def cur_price(self, code) -> int | float:
        if code not in self.__real_price.real:
            self.__real_price.register(code, fids='41')
        return self.__real_price.real[code].cur_price

    def buy_price(self, code) -> int | float:
        if code not in self.__real_price.real:
            self.__real_price.register(code, fids='41')
        return self.__real_price.real[code].buy_price

    def sell_price(self, code) -> int | float:
        if code not in self.__real_price.real:
            self.__real_price.register(code, fids='41')
        return self.__real_price.real[code].sell_price

    def account_validation(self, acc_no: str) -> bool:
        return acc_no in self.__account_numbers

    @property
    def screen_start(self) -> int:
        return self.config.row['screen']['start']

    @property
    def screen_max(self) -> int:
        return self.config.row['screen']['max']

    @property
    def screen_query(self) -> int:
        return self.config.row['screen']['query']

    @property
    def screen_price(self) -> int:
        return self.config.row['screen']['price']

    @property
    def __screen_no(self) -> int:
        self.__s_pos = self.__s_pos + 1 if self.__s_pos + 1 < len(self.__screen) else 0
        return self.__screen[self.__s_pos]

    @property
    def __tr_request_delay(self) -> float:
        return 0.21

    def __waiting_system_delay(self):
        while default_timer() - self.__prev_request_time < self.__tr_request_delay:
            PumpWaitingMessages()
            sleep(0.01)
        self.__prev_request_time = default_timer()

    def __waiting_event(self):
        self.__receive_event = False
        while self.__receive_event is False:
            PumpWaitingMessages()
            sleep(0.01)

    def add_receive_handler(self, rq_name, handler):
        self.__receive_handler[rq_name] = handler

    def add_message_handler(self, rq_name, handler):
        self.__message_handler[rq_name] = handler

    def login(self):
        self.dynamicCall("CommConnect()")
        self.__waiting_event()

    def set_real_reg(self, screen_no, code_list, fid_list, real_type):
        """
        [SetRealReg() 함수]

        SetRealReg(
            BSTR strScreenNo,   // 화면번호
            BSTR strCodeList,   // 종목코드 리스트
            BSTR strFidList,  // 실시간 FID리스트
            BSTR strOptType   // 실시간 등록 타입, 0또는 1
        )

        종목코드와 FID 리스트를 이용해서 실시간 시세를 등록하는 함수입니다.
        한번에 등록가능한 종목과 FID갯수는 100종목, 100개 입니다.
        실시간 등록타입을 0으로 설정하면 등록한 종목들은 실시간 해지되고 등록한 종목만 실시간 시세가 등록됩니다.
        실시간 등록타입을 1로 설정하면 먼저 등록한 종목들과 함께 실시간 시세가 등록됩니다

        -----------------------------------------------------------------------------------------------------------

        [실시간 시세등록 예시]
        OpenAPI.SetRealReg(_T("0150"), _T("039490"), _T("9001;302;10;11;25;12;13"), "0");  // 039490 종목만 실시간 등록
        OpenAPI.SetRealReg(_T("0150"), _T("000660"), _T("9001;302;10;11;25;12;13"), "1");  // 000660 종목을 실시간 추가등록

        -----------------------------------------------------------------------------------------------------------
        """
        # logger.debug(f"set_real_reg; {screen_no, code_list, fid_list, real_type}")
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                         [screen_no, code_list, fid_list, real_type])

    def dis_connect_realdata(self, screen_no):
        """
        [DisconnectRealData() 함수]

        DisconnectRealData(
            BSTR sScnNo // 화면번호
        )

        시세데이터를 요청할때 사용된 화면번호를 이용하여
        해당 화면번호로 등록되어져 있는 종목의 실시간시세를 서버에 등록해지 요청합니다.
        이후 해당 종목의 실시간시세는 수신되지 않습니다.
        단, 해당 종목이 또다른 화면번호로 실시간 등록되어 있는 경우 해당종목에대한 실시간시세 데이터는 계속 수신됩니다.
        """
        logger.debug(f"dis_connect_realdata; {screen_no}")
        self.dynamicCall("DisConnectRealData(QString)", screen_no)

    def get_comm_real_data(self, code, fid):
        """
        [GetCommRealData() 함수]

        GetCommRealData(
            BSTR strCode,   // 종목코드
            long nFid   // 실시간 타입에 포함된FID (Feild ID)
        )

        실시간시세 데이터 수신 이벤트인 OnReceiveRealData() 가 발생될때 실시간데이터를 얻어오는 함수입니다.
        이 함수는 OnReceiveRealData()이벤트가 발생될때 그 안에서 사용해야 합니다.
        FID 값은 "실시간목록"에서 확인할 수 있습니다.

        ----------------------------------------------------------------------------------------------------------

        예)
        [주식체결 실시간 데이터 예시]

        if(strRealType == _T("주식체결"))	// OnReceiveRealData 이벤트로 수신된 실시간타입이 "주식체결" 이면
        {
            strRealData = OpenAPI.GetCommRealData(strCode, 10);   // 현재가
            strRealData = OpenAPI.GetCommRealData(strCode, 13);   // 누적거래량
            strRealData = OpenAPI.GetCommRealData(strCode, 228);    // 체결강도
            strRealData = OpenAPI.GetCommRealData(strCode, 20);  // 체결시간
        }

        ----------------------------------------------------------------------------------------------------------
        """
        return self.dynamicCall("GetCommRealData(QString, int)", [code, fid])

    def set_input_value(self, name, value):
        self.dynamicCall("SetInputValue(QString, QString)", [name, value])

    def comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)",
                               [code, real_type, field_name, index, item_name])
        return ret.strip()

    def get_repeat_cnt(self, tr_code, rq_name) -> int:
        return self.dynamicCall("GetRepeatCnt(QString, QString)", [tr_code, rq_name])

    def send_order(self, rq_name, acc_no, code, qty, price, order_type, hoga_gb='00', org_order_no=''):
        """
        [SendOrder() 함수]

        SendOrder(
        BSTR sRQName, // 사용자 구분명
        BSTR sScreenNo, // 화면번호
        BSTR sAccNo,  // 계좌번호 10자리
        LONG nOrderType,  // 주문유형 1:신규매수, 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정, 7:프로그램매매 매수, 8:프로그램매매 매도
        BSTR sCode, // 종목코드 (6자리)
        LONG nQty,  // 주문수량
        LONG nPrice, // 주문가격
        BSTR sHogaGb,   // 거래구분(혹은 호가구분)은 아래 참고
        BSTR sOrgOrderNo  // 원주문번호. 신규주문에는 공백 입력, 정정/취소시 입력합니다.
        )

        서버에 주문을 전송하는 함수 입니다.
        9개 인자값을 가진 주식주문 함수이며 리턴값이 0이면 성공이며 나머지는 에러입니다.
        1초에 5회만 주문가능하며 그 이상 주문요청하면 에러 -308을 리턴합니다.
        ※ 시장가주문시 주문가격은 0으로 입력합니다. 주문가능수량은 해당 종목의 상한가 기준으로 계산됩니다.
        ※ 취소주문일때 주문가격은 0으로 입력합니다.
        ※ 프로그램매매 주문은 실거래 서버에서만 주문하실수 있으며 모의투자 서버에서는 지원하지 않습니다.

        [거래구분]
        00 : 지정가
        03 : 시장가
        05 : 조건부지정가
        06 : 최유리지정가
        07 : 최우선지정가
        10 : 지정가IOC
        13 : 시장가IOC
        16 : 최유리IOC
        20 : 지정가FOK
        23 : 시장가FOK
        26 : 최유리FOK
        61 : 장전시간외종가
        62 : 시간외단일가매매
        81 : 장후시간외종가
        ※ 모의투자에서는 지정가 주문과 시장가 주문만 가능합니다.
        """
        logger.debug(f"send_order; {acc_no, code, qty, price, order_type}")
        self.__waiting_system_delay()
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                         [rq_name, self.__screen_no, acc_no, order_type, code, qty, price, hoga_gb, org_order_no])

    def send_order_fo(self, rq_name, acc_no, mode, code, qty, price, ord_kind, hoga_gb='1', org_order_no=''):
        """
        [SendOrderFO() 함수]

        SendOrderFO(
        BSTR sRQName,     // 사용자 구분명
        BSTR sScreenNo,   // 화면번호
        BSTR sAccNo,      // 계좌번호 10자리
        BSTR sCode,       // 종목코드
        LONG lOrdKind,    // 주문종류 1:신규매매, 2:정정, 3:취소
        BSTR sSlbyTp,     // 매매구분	1: 매도, 2:매수
        BSTR sOrdTp,      // 거래구분(혹은 호가구분)은 아래 참고
        LONG lQty,        // 주문수량
        BSTR sPrice,      // 주문가격
        BSTR sOrgOrdNo    // 원주문번호
        )

        서버에 주문을 전송하는 함수 입니다.
        코스피지수200 선물옵션 전용 주문함수입니다.

        [거래구분]
        1 : 지정가
        2 : 조건부지정가
        3 : 시장가
        4 : 최유리지정가
        5 : 지정가(IOC)
        6 : 지정가(FOK)
        7 : 시장가(IOC)
        8 : 시장가(FOK)
        9 : 최유리지정가(IOC)
        A : 최유리지정가(FOK)
        장종료 후 시간외 주문은 지정가 선택
        """
        logger.debug(f"send_order_of; {acc_no, mode, code, qty, price, ord_kind}")
        self.__waiting_system_delay()
        self.dynamicCall("SendOrderFO(QString, QString, QString, QString, int, QString, QString, int, QString, QString)",
                         [rq_name, self.__screen_no, acc_no, code, ord_kind, mode, hoga_gb, qty, price, org_order_no])

    def comm_rq_data(self, rq_name, tr_code, next_):
        self.__waiting_system_delay()
        self.dynamicCall("CommRqData(QString, QString, int, QString)", [rq_name, tr_code, next_, self.__screen_no])
        self.__waiting_event()

    def __handler_login(self, err_code):
        """
        [OnEventConnect()이벤트]

        OnEventConnect(
            long nErrCode   // 로그인 상태를 전달하는데 자세한 내용은 아래 상세내용 참고
        )

        로그인 처리 이벤트입니다. 성공이면 인자값 nErrCode가 0이며 에러는 다음과 같은 값이 전달됩니다.

        nErrCode별 상세내용
        -100 사용자 정보교환 실패
        -101 서버접속 실패
        -102 버전처리 실패
        """
        logger.info(f"login error code; {err_code}")
        if self.config.login_dialog is True:
            self.dynamicCall("KOA_Functions(QString, QString)", "ShowAccountWindow", "")
        self.__receive_event = True

        logger.debug(f"계좌수: {self.GetLoginInfo('ACCOUNT_CNT')}")
        self.__account_numbers = [r for r in self.GetLoginInfo('ACCNO').split(';') if len(r)]
        logger.debug(f"전체 계좌 리스트: {self.__account_numbers}")
        # logger.debug(f"사용자 ID: {self.GetLoginInfo('USER_ID')}")
        # logger.debug(f"사용자명: {self.GetLoginInfo('USER_NAME')}")

    def __handler_tr_data(self, screen_no, rq_name, tr_code, record_name, next_,
                          unused1, unused2, unused3, unused4):
        """
        [OnReceiveTrData() 이벤트]

        void OnReceiveTrData(
            BSTR sScrNo,       // 화면번호
            BSTR sRQName,      // 사용자 구분명
            BSTR sTrCode,      // TR이름
            BSTR sRecordName,  // 레코드 이름
            BSTR sPrevNext,    // 연속조회 유무를 판단하는 값 0: 연속(추가조회)데이터 없음, 2:연속(추가조회) 데이터 있음
            LONG nDataLength,  // 사용안함.
            BSTR sErrorCode,   // 사용안함.
            BSTR sMessage,     // 사용안함.
            BSTR sSplmMsg     // 사용안함.
        )

        요청했던 조회데이터를 수신했을때 발생됩니다.
        수신된 데이터는 이 이벤트내부에서 GetCommData()함수를 이용해서 얻어올 수 있습니다.
        """
        try:
            self.__receive_handler[rq_name](next_)
        except KeyError:
            logger.critical(f"__receive_tr_data key error; {rq_name}")
        self.__receive_event = True

    def __handler_real_data(self, code, real_type, _):
        """
        [OnReceiveRealData()이벤트]

        OnReceiveRealData(
            BSTR sCode,        // 종목코드
            BSTR sRealType,    // 실시간타입
            BSTR sRealData    // 실시간 데이터 전문 (사용불가)
        )

        실시간시세 데이터가 수신될때마다 종목단위로 발생됩니다.
        SetRealReg()함수로 등록한 실시간 데이터도 이 이벤트로 전달됩니다.
        GetCommRealData()함수를 이용해서 수신된 데이터를 얻을수 있습니다.

        [주식체결 실시간 데이터 예시]

        if(strRealType == _T("주식체결"))	// OnReceiveRealData 이벤트로 수신된 실시간타입이 "주식체결" 이면
        {
            strRealData = OpenAPI.GetCommRealData(strCode, 10);   // 현재가
            strRealData = OpenAPI.GetCommRealData(strCode, 13);   // 누적거래량
            strRealData = OpenAPI.GetCommRealData(strCode, 228);    // 체결강도
            strRealData = OpenAPI.GetCommRealData(strCode, 20);  // 체결시간
        }
        """
        # logger.debug(f"receive_real_data; {code, real_type}")
        if code in self.__real_price.real:
            self.__real_price.receive_real_data(code, real_type)

    def __handler_chejan_data(self, gubun, item_cnt, fid_list):
        """
        [OnReceiveChejanData() 이벤트]

        OnReceiveChejanData(
            BSTR sGubun, // 체결구분. 접수와 체결시 '0'값, 국내주식 잔고변경은 '1'값, 파생잔고변경은 '4'
            LONG nItemCnt,
            BSTR sFIdList
        )
        주문전송 후 주문접수, 체결통보, 잔고통보를 수신할 때 마다 발생됩니다.
        GetChejanData()함수를 이용해서 FID항목별 값을 얻을수 있습니다.
        """
        pass
        # logger.debug(f"OnReceiveChejanData; {gubun, item_cnt, fid_list}")

    def __receive_msg(self, screen_no, rq_name, tr_code, msg) -> None:
        """
        [OnReceiveMsg() 이벤트]

        OnReceiveMsg(
            BSTR sScrNo,   // 화면번호
            BSTR sRQName,  // 사용자 구분명
            BSTR sTrCode,  // TR이름
            BSTR sMsg     // 서버에서 전달하는 메시지
        )

        서버통신 후 수신한 서버메시지를 알려줍니다.
        데이터 조회시 입력값(Input)오류, 주문 전송시 주문거부 사유 등을 확인할 수 있습니다.
        메시지에 포함된 6자리 코드번호는 변경될 수 있으니, 여기에 수신된 코드번호를 특정 용도로 사용하지 마시기 바랍니다.
        예) "조회가 완료되었습니다"
        예) "계좌번호 입력을 확인해주세요"
        예) "조회할 자료가 없습니다."
        예) "증거금 부족으로 주문이 거부되었습니다."

           1        // 정상처리
           0        // 정상처리
         -10        // 실패
         -11        // 조건번호 없슴
         -12        // 조건번호와 조건식 불일치
         -13        // 조건검색 조회요청 초과
        -100        // 사용자정보교환 실패
        -101        // 서버 접속 실패
        -102        // 버전처리 실패
        -103        // 개인방화벽 실패
        -104        // 메모리 보호실패
        -105        // 함수입력값 오류
        -106        // 통신연결 종료
        -107        // 보안모듈 오류
        -108        // 공인인증 로그인 필요

        -200        // 시세조회 과부하
        -201        // 전문작성 초기화 실패.
        -202        // 전문작성 입력값 오류.
        -203        // 데이터 없음.
        -204        // 조회가능한 종목수 초과. 한번에 조회 가능한 종목개수는 최대 100종목.
        -205        // 데이터 수신 실패
        -206        // 조회가능한 FID수 초과. 한번에 조회 가능한 FID개수는 최대 100개.
        -207        // 실시간 해제오류
        -209        // 시세조회제한

        -300        // 입력값 오류
        -301        // 계좌비밀번호 없음.
        -302        // 타인계좌 사용오류.
        -303        // 주문가격이 주문착오 금액기준 초과.
        -304        // 주문가격이 주문착오 금액기준 초과.
        -305        // 주문수량이 총발행주수의 1% 초과오류.
        -306        // 주문수량은 총발행주수의 3% 초과오류.
        -307        // 주문전송 실패
        -308        // 주문전송 과부하
        -309        // 주문수량 300계약 초과.
        -310        // 주문수량 500계약 초과.
        -311        // 주문전송제한 과부하
        -340        // 계좌정보 없음.
        -500        // 종목코드 없음.
        """
        # logger.debug(f"OnReceiveMsg; {screen_no, rq_name, tr_code, msg}")
        if not len(screen_no):
            return
        try:
            self.__message_handler[rq_name](msg)
        except KeyError:
            logger.critical(f"__message_handler key error; {rq_name}")
        finally:
            # note; msg event 의 경우는 대기할 필요가 없는가?
            pass
