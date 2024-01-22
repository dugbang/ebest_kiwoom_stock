from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QHBoxLayout, \
    QVBoxLayout, QInputDialog, QRadioButton, QGroupBox, QComboBox
from PyQt5.QtCore import Qt

from config_dir import ConfigDir
from my_logger import logger
from tcp_client import TcpClient
from utils import EventMessage, BalanceItemFO, BalanceItemStock


class TestTcp:
    def __init__(self, config, parent):
        self.__c = config
        self.__a = dict()
        self.__parent = parent

        self.__tcp = TcpClient(config, receive_event=self.__receive_event)
        if not self.__tcp.start():
            raise Exception(self._w_msg('__init__', '서버 연결 실패'))

    def _w_msg(self, f: str, p: str) -> str:
        return f"{self.__class__.__name__}.{f} > {p}"

    def __receive_event(self, e: EventMessage):
        logger.debug(f"__receive_event; {e}")
        match e.cmd:
            case 'exit':
                self.__parent.tcp_disconnected()
                self.__parent.te.insertPlainText(f"서버가 종료 되었습니다.\n")
            case 'a_ls':
                self.__parent.te.insertPlainText(f"receive account info\n")
                for a_id, a_type, a_no in e.data:
                    self.__a[a_id] = [a_type, a_no]
                    self.__parent.te.insertPlainText(f"{a_id, a_type, a_no}\n")
                for k in self.__a:
                    if self.__parent.cb_02.findText(f"{k}, {self.__a[k][0]}") == -1:
                        self.__parent.cb_02.addItem(f"{k}, {self.__a[k][0]}")
                self.__parent.cb_02.setCurrentIndex(0)
            case 'msg':
                logger.debug(e.data[0])
                self.__parent.te.insertPlainText(f"{e.data[0]}\n")
            case 'ts_msg':
                logger.debug('not support yet')
                pass
            case 'r_lm':
                logger.debug(f"return lm cmd")
                self.__parent.te.insertPlainText(f"return lm cmd\n")
                msg_ = f"{e.data[0]}, a_id; {e.data[1]}, a_type; {e.data[2]}, len; {e.data[3]}"
                logger.debug(f"{msg_}")
                self.__parent.te.insertPlainText(f"{msg_}\n")
                for r in e.data[4:]:
                    d = BalanceItemFO(**r) if e.data[2] == 'fo' else BalanceItemStock(**r)
                    logger.debug(f"{d}")
            case 'r_ls':
                logger.debug(f"return ls cmd")
                self.__parent.te.insertPlainText(f"return ls cmd\n")

                msg_ = f"{e.data[0]}, a_id; {e.data[1]}, a_type; {e.data[2]}, len; {e.data[3]}"
                logger.debug(f"{msg_}")
                self.__parent.te.insertPlainText(f"{msg_}\n")
                for r in e.data[4:]:
                    d = BalanceItemFO(**r) if e.data[2] == 'fo' else BalanceItemStock(**r)
                    logger.debug(f"{d}")
                    self.__parent.te.insertPlainText(f"{d}\n")
            case _:
                logger.warning(self._w_msg('event_processing', f"cmd not define; {e.cmd}"))
        pass

    def initial(self):
        self.__parent.te.insertPlainText(f"cmd; /ls\n")
        self.__tcp.send_cmd('/ls')

    def stop(self):
        self.__tcp.stop()

    def send_cmd(self, cmd):
        self.__tcp.send_cmd(cmd)


class SampleEBestKiwoom(QWidget):

    def __init__(self):
        super().__init__()
        self.__server = None

        self.__init_ui_2()

    def tcp_disconnected(self):
        self.__btn_30_order.setEnabled(False)
        self.__btn_31_ls.setEnabled(False)
        self.__btn_32_lm.setEnabled(False)
        self.__btn_33_connect.setEnabled(True)
        self.__btn_34_disconnect.setEnabled(False)

    def tcp_connected(self):
        self.__btn_30_order.setEnabled(True)
        self.__btn_31_ls.setEnabled(True)
        self.__btn_32_lm.setEnabled(True)
        self.__btn_33_connect.setEnabled(False)
        self.__btn_34_disconnect.setEnabled(True)

    def __tcp_start(self):
        msg_ = 'exec 디렉토리에 있는 \n' \
               'ebest_trade.bat 또는 kiwoom_trade.bat 를 \n' \
               '실행한 후 [OK]을 클릭하세요.'

        item, ok = QInputDialog.getItem(
            None,
            "서버 선택",
            msg_,
            ('ebest', 'kiwoom'),
            0,
            False
        )

        if ok and item:
            ConfigDir.validate(root=item)
            from configuration import Configuration
            try:
                self.__server = TestTcp(config=Configuration(), parent=self)
            except Exception as e:
                logger.warning(f"{e}")
                return
            self.__server.initial()
            self.tcp_connected()

    def __tcp_stop(self):
        if self.__server:
            self.__server.stop()
            self.__server = None
        self.tcp_disconnected()

    def __tcp_cmd_ls(self):
        logger.debug(f"send_cmd; /ls")
        self.__server.send_cmd('/ls ds')

    def __tcp_cmd_lm(self):
        logger.debug(f"send_cmd; /lm")
        self.__server.send_cmd('/lm ds')

    def __tcp_order(self):
        cmd = ''
        if self.__rbtn_01_order.isChecked():
            cmd = '/o'
        elif self.__rbtn_02_modify.isChecked():
            cmd = '/m'
        elif self.__rbtn_03_cancel.isChecked():
            cmd = '/c'

        opt = ''
        match self.__cb_20.currentText():
            case '수동':
                opt = 'm'
            case '자동':
                opt = 'a'
            case '체결':
                opt = 'i'

        cmd = f"{cmd} {self.cb_02.currentText().split(',')[0]} {opt} {self.__cb_21.currentText()} " \
              f"{self.__qle_22_code.text()} {self.__qle_23_qty.text()} {self.__qle_24_price.text()}"

        logger.debug(f"{cmd}")
        self.__server.send_cmd(f"{cmd}")

    def closeEvent(self, event):
        if self.__server:
            self.__server.stop()
        event.accept()

    def __init_ui_2(self):
        label1 = QLabel('계좌 e_id :', self)
        label1.setAlignment(Qt.AlignVCenter | Qt.AlignCenter)

        self.cb_02 = QComboBox(self)

        hbox_00 = QHBoxLayout()
        hbox_00.addWidget(label1)
        hbox_00.addWidget(self.cb_02)

        groupbox_01 = QGroupBox('주문명령')
        self.__rbtn_01_order = QRadioButton('신규주문', self)
        self.__rbtn_01_order.setChecked(True)
        self.__rbtn_02_modify = QRadioButton('수정주문', self)
        self.__rbtn_03_cancel = QRadioButton('취소주문', self)

        hbox_01 = QHBoxLayout()
        hbox_01.addWidget(self.__rbtn_01_order)
        hbox_01.addWidget(self.__rbtn_02_modify)
        hbox_01.addWidget(self.__rbtn_03_cancel)
        groupbox_01.setLayout(hbox_01)

        hbox_10 = QHBoxLayout()
        hbox_10.addLayout(hbox_00)
        hbox_10.addWidget(groupbox_01)

        grid_10 = QGridLayout()

        label_10 = QLabel('order type', self)
        label_10.setAlignment(Qt.AlignCenter)
        label_11 = QLabel('sell / buy', self)
        label_11.setAlignment(Qt.AlignCenter)
        label_12 = QLabel('code', self)
        label_12.setAlignment(Qt.AlignCenter)
        label_13 = QLabel('qty', self)
        label_13.setAlignment(Qt.AlignCenter)
        label_14 = QLabel('price/money', self)
        label_14.setAlignment(Qt.AlignCenter)

        grid_10.addWidget(label_10, 0, 0)
        grid_10.addWidget(label_11, 0, 1)
        grid_10.addWidget(label_12, 0, 2)
        grid_10.addWidget(label_13, 0, 3)
        grid_10.addWidget(label_14, 0, 4)

        self.__cb_20 = QComboBox(self)
        self.__cb_20.addItem('수동')
        self.__cb_20.addItem('자동')
        self.__cb_20.addItem('체결')
        self.__cb_21 = QComboBox(self)
        self.__cb_21.addItem('sell')
        self.__cb_21.addItem('buy')

        self.__qle_22_code = QLineEdit(self)
        self.__qle_22_code.setAlignment(Qt.AlignVCenter | Qt.AlignCenter)
        self.__qle_23_qty = QLineEdit(self)
        self.__qle_23_qty.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.__qle_24_price = QLineEdit(self)
        self.__qle_24_price.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        grid_10.addWidget(self.__cb_20, 1, 0)
        grid_10.addWidget(self.__cb_21, 1, 1)
        grid_10.addWidget(self.__qle_22_code, 1, 2)
        grid_10.addWidget(self.__qle_23_qty, 1, 3)
        grid_10.addWidget(self.__qle_24_price, 1, 4)

        groupbox_20 = QGroupBox('전송정보')
        groupbox_20.setLayout(grid_10)

        hbox_20 = QHBoxLayout()
        hbox_20.addWidget(groupbox_20)

        self.__btn_30_order = QPushButton('주문실행', self)
        self.__btn_30_order.setEnabled(False)
        self.__btn_31_ls = QPushButton('ls 명령', self)
        self.__btn_31_ls.setEnabled(False)
        self.__btn_32_lm = QPushButton('lm 명령', self)
        self.__btn_32_lm.setEnabled(False)
        self.__btn_33_connect = QPushButton('서버연결', self)
        self.__btn_33_connect.setEnabled(True)
        self.__btn_34_disconnect = QPushButton('연결끊기', self)
        self.__btn_34_disconnect.setEnabled(False)

        hbox_30 = QHBoxLayout()
        hbox_30.addWidget(self.__btn_30_order)
        hbox_30.addWidget(self.__btn_31_ls)
        hbox_30.addWidget(self.__btn_32_lm)
        hbox_30.addWidget(self.__btn_33_connect)
        hbox_30.addWidget(self.__btn_34_disconnect)

        self.te = QTextEdit()
        self.te.setAcceptRichText(False)
        hbox_40 = QHBoxLayout()
        hbox_40.addWidget(self.te)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox_10)
        vbox.addLayout(hbox_20)
        vbox.addLayout(hbox_30)
        vbox.addLayout(hbox_40)

        self.setLayout(vbox)

        self.__btn_30_order.clicked.connect(self.__tcp_order)
        self.__btn_31_ls.clicked.connect(self.__tcp_cmd_ls)
        self.__btn_32_lm.clicked.connect(self.__tcp_cmd_lm)
        self.__btn_33_connect.clicked.connect(self.__tcp_start)
        self.__btn_34_disconnect.clicked.connect(self.__tcp_stop)

        self.setWindowTitle('ebest & kiwoom TCP sample')

        self.resize(620, 430)
        self.show()


if __name__ == '__main__':
    app = QApplication([])
    ex = SampleEBestKiwoom()
    app.exec_()
