import sys
import pickle
from logging import DEBUG, INFO
from os import path
from datetime import date
from time import sleep

from PyQt5.QtWidgets import QApplication

from account import AccountStock, AccountFO
from config_dir import ConfigDir
from configuration import Configuration
from ebest import EBest
from my_logger import logger
from kiwoom import Kiwoom
from communication import EventQueue, Telegram
from tcp_server import TcpServer
from timer_process import TimerProcess
from utils import MatchMassage
from xing_basic import real_event_process


class ApiTrader:
    def __init__(self, config: Configuration):
        self.__config = config
        self.__queue = EventQueue()
        self.__match = MatchMassage()
        try:
            self.__store = pickle.load(open(ConfigDir.get_path('store_info.pickle'), 'rb'))
        except FileNotFoundError:
            self.__store = dict()

        self.__telegram = Telegram(queue=self.queue, config=self.config)
        self.__telegram.init_handler()
        self.__tcp_server = TcpServer(queue=self.queue, config=self.config)

        if ConfigDir.ROOT == 'ebest':
            self.__session = EBest(self)
        elif ConfigDir.ROOT == 'kiwoom':
            self.__session = Kiwoom(self)
        else:
            raise Exception(f"session error; {ConfigDir.ROOT}")
        self.__session.login()

        self.__accounts = dict()
        try:
            self.__load_account_files()
        except Exception as e:
            logger.debug(f"get_account_files...")
            self.__exit(f"{e}")

        self.__session.initial(self)
        self.__telegram.initial(self)
        self.__tcp_server.initial(self)

        for _, acc in self.__accounts.items():
            real_event_process()
            acc.initial()

        self.__timer = TimerProcess(self.__config)
        self.__timer.add_period(self.__config.timer_acc_reload,
                                lambda: self.queue.post(self.e_id, 'acc.reload', list()))
        self.__timer.add_period(self.__config.timer_store_save,
                                lambda: self.queue.post(self.e_id, 'store.save', list()))

    def __load_account_files(self):
        for f in ConfigDir.get_account_files(self.__config.demo):
            logger.debug(f"account file; {f}")
            f_data = ConfigDir.load_yaml(f"{f}", sub='account')
            if f_data['enable_trading'] != 1:
                continue

            if self.__session.account_validation(f_data['a_no']):
                match f_data['a_type']:
                    case 'stock':
                        self.__accounts[f_data['e_id']] = AccountStock(self, file=f)
                    case 'fo':
                        self.__accounts[f_data['e_id']] = AccountFO(self, file=f)
                    case _:
                        raise Exception(f"    Not support account type([{ConfigDir.ROOT}]"
                                        f" {f}); {f_data['a_type']}")
            else:
                raise Exception(f"    Not exist account number([{ConfigDir.ROOT}]"
                                f" {f}); {f_data['a_no']}")
        if not self.__accounts:
            raise Exception(f"    no account file & disabled")

    @property
    def store(self) -> dict:
        return self.__store

    @property
    def match(self) -> MatchMassage:
        return self.__match

    @property
    def config(self) -> Configuration:
        return self.__config

    @property
    def queue(self) -> EventQueue:
        return self.__queue

    @property
    def telegram(self) -> Telegram:
        return self.__telegram

    @property
    def tcp_server(self) -> TcpServer:
        return self.__tcp_server

    @property
    def session(self) -> Kiwoom | EBest:
        return self.__session

    @property
    def accounts(self) -> dict:
        return self.__accounts

    @property
    def e_id(self) -> str:
        return self.__config.e_id_main

    def _w_msg(self, f: str, p: str) -> str:
        return f"{self.__class__.__name__}.{f} > {p}"

    def __store_output(self):
        for key in self.__store:
            logger.debug(f"==== key; {key} ====")
            for k, v in self.__store[key].items():
                logger.debug(f"{k}, {v}")

    def __event_processing(self):
        for e in self.queue.get(self.e_id):
            logger.debug(f"__event_processing; {e}")
            match e.cmd:
                case 'test.store':
                    self.__store_output()
                case 'test.match':
                    self.__match.output()
                case 'store.save':
                    pickle.dump(self.__store, open(ConfigDir.get_path('store_info.pickle'), 'wb'))
                case 'acc.reload':
                    for _, acc in self.__accounts.items():
                        acc.reload()
                case 'shutdown':
                    logger.info('!!!!! 시스템 종료 명령 실행 !!!!!')
                    self.queue.post(e.s_id, 'msg', ['!!!!! 시스템 종료 명령 실행 !!!!!', ])
                    self.__timer.add_single(2, lambda: ConfigDir.make_file('exit'))
                case _:
                    logger.warning(self._w_msg('__event_processing',
                                               f"not match trade cmd; {e.cmd}"))

    def main_loop(self) -> None:
        logger.info(f"  !!! START MAIN LOOP [{ConfigDir.ROOT.upper()}] !!!")
        self.__telegram.send_msg(f"  !!! START MAIN LOOP [{ConfigDir.ROOT.upper()}] !!!")
        while not ConfigDir.exist(name='exit'):
            real_event_process()
            try:
                try:
                    self.__timer.processing()
                except Exception as e:
                    logger.warning(f"timer.processing; {e}")

                for _, acc in self.__accounts.items():
                    real_event_process()
                    acc.background()        # background....
                    acc.event_processing()

                self.__event_processing()
                for t, m in self.__match.pair():
                    self.queue.post(t, 'msg', [m, ])

            except Exception as e:
                logger.critical(f"main_loop [{ConfigDir.ROOT}] >> {e}")
                self.__telegram.send_msg(f"main_loop [{ConfigDir.ROOT}] >> {e}")
            sleep(self.__config.loop_sleep)
        logger.info(f"  !!! END MAIN LOOP [{ConfigDir.ROOT.upper()}] !!!")
        self.__telegram.send_msg(f"  !!! END MAIN LOOP [{ConfigDir.ROOT.upper()}] !!!")
        self.__stop()

    def __stop(self) -> None:
        for _, acc in self.__accounts.items():
            acc.stop()

        self.__tcp_server.stop()
        self.__telegram.stop()
        self.__session.stop()
        self.__session.logout()
        pickle.dump(self.__store, open(ConfigDir.get_path('store_info.pickle'), 'wb'))

    def __exit(self, msg):
        logger.critical(f"x" * 60)
        logger.critical(msg)
        logger.critical(f"x" * 60)
        self.__stop()
        exit(0)


if __name__ == '__main__':
    if len(sys.argv) > 1 and path.exists(sys.argv[1]):
        ConfigDir.validate(root=sys.argv[1])
        logger.info('=' * 50)
        logger.info(f"  CONFIGURATION DIRECTORY; {sys.argv[1]}")
    else:
        ConfigDir.validate(root='ebest')
        # ConfigDir.validate(root='kiwoom')
        logger.info('=' * 50)
        logger.warning(f"  !!! PARAMETER ERROR !!!")
        logger.warning(f"  DEFAULT CONFIGURATION DIRECTORY; {ConfigDir.ROOT}")
    ConfigDir.remove('exit')

    _config = Configuration()
    logger.info('=' * 50)
    if _config.debug:
        logger.setLevel(DEBUG)
    else:
        logger.setLevel(INFO)

    if _config.demo:
        logger.info(f"  !!!! DEMO SERVER !!!!")
    else:
        logger.info(f"  !!!! REAL SERVER !!!!")

    logger.info(f"  {ConfigDir.ROOT.upper()} Trading Start")
    logger.info(f"  TODAY; {date.today().strftime('%Y%m%d')}")
    logger.info('=' * 50)

    app = QApplication([])
    trader = ApiTrader(config=_config)
    trader.main_loop()

    logger.info('=' * 50)
    logger.info(f"  {ConfigDir.ROOT.upper()} Trading Exit")
    logger.info('=' * 50)
