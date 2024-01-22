import pickle

from config_dir import ConfigDir


class Configuration:
    def __init__(self):
        self.__config = ConfigDir.load_yaml('configuration.yaml')
        try:
            self.__secret = ConfigDir.load_yaml('secret.yaml')
        except FileNotFoundError:
            raise Exception(f"!!! secret.yaml file not find !!!")

        try:
            self.__login = pickle.load(open(ConfigDir.get_path('login_info.pickle'), 'rb'))
        except FileNotFoundError:
            self.__login = None

    def telegram_info(self) -> dict:
        self.__config['telegram']['t_id'] = self.__secret['telegram']
        return self.__config['telegram']['t_id']

    @property
    def e_id_main(self) -> str:
        return self.__config['event_id']['main']

    @property
    def e_id_telegram(self) -> str:
        return self.__config['event_id']['telegram']

    @property
    def e_id_tcp_server(self) -> str:
        return self.__config['event_id']['tcp_server']

    @property
    def timer_acc_reload(self) -> int:
        return self.__config['timer']['account_reload']

    @property
    def timer_store_save(self) -> int:
        return self.__config['timer']['store_save']

    @property
    def row(self) -> dict:
        return self.__config

    @property
    def loop_sleep(self) -> float:
        return self.__config['loop_sleep']

    @property
    def login_dialog(self) -> bool:
        return self.__config['login_dialog'] == 1

    @property
    def debug(self) -> bool:
        return self.__config['debug'] == 1

    @property
    def demo(self) -> bool:
        return self.__config['demo'] == 1

    @property
    def server_address(self) -> str:
        if self.__login:
            return self.__login['server_address'][1 if self.demo else 0]
        return self.__secret['login_info']['server_address'][1 if self.demo else 0]

    @property
    def id(self) -> str:
        if self.__login:
            return self.__login['id'][1 if self.demo else 0]
        return self.__secret['id']

    @property
    def pw(self) -> str:
        if self.__login:
            return self.__login['pw'][1 if self.demo else 0]
        return self.__secret['login_info']['pw'][1 if self.demo else 0]

    @property
    def ppw(self) -> str:
        if self.__login:
            return self.__login['ppw'][1 if self.demo else 0]
        return self.__secret['login_info']['ppw'][1 if self.demo else 0]

    @property
    def apw(self) -> str:
        if self.__login:
            return self.__login['apw'][1 if self.demo else 0]
        return self.__secret['login_info']['apw'][1 if self.demo else 0]


# def make_pickle():
#     """
#     login_info.pickle 파일을 만들 때 사용.
#     """
#     try:
#         secret = ConfigDir.load_yaml('secret.yaml')
#     except FileNotFoundError:
#         raise Exception(f"!!! secret.yaml file not find !!!")
#     pickle.dump(secret['login_info'], open(ConfigDir.get_path('login_info.pickle'), 'wb'))
#
#
# if __name__ == "__main__":
#     ConfigDir.validate(root='ebest')
#     make_pickle()
