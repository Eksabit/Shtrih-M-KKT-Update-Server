import os
import sys
import datetime
import socket
import ctypes
import tornado.escape
import tornado.ioloop
import tornado.web
import logging
from logging.handlers import RotatingFileHandler
from colorama import init, Fore
config_directory = os.path.abspath('static')
sys.path.append(config_directory)
from config import *

init(autoreset=True)

# Настройка консоли и логирования
local_ip = socket.gethostbyname(socket.gethostname())
ctypes.windll.kernel32.SetConsoleTitleA(b"Shtrih-M KKT Update Server V1.4")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[RotatingFileHandler('static/history.log', maxBytes=128 * 1024, backupCount=10), logging.StreamHandler(sys.stdout)]
)

print(Fore.MAGENTA + f'''
  Сервер для обновления ККТ Штрих-М
  README.md - информация о сервере                      
  config.py - конфигурация сервера                      
  history.log - история всех подключений и запусков
  Server address: {local_ip}:{PORT}
''')

def build_to_int(build):
    return int(datetime.datetime.strptime(build, "%d.%m.%Y").strftime("%Y%m%d"))

def make_download_url(request, firmware, old=False):
    suffix = "upd_app_for_old_frs.bin" if old else "upd_app.bin"
    return f"http://{request.host}/firmware/{firmware['version']}/{suffix}"

class BaseHandler(tornado.web.RequestHandler):
    def prepare(self):
        ip_address = self.request.remote_ip
        logging.info(Fore.YELLOW + f"Received {self.request.method} request to {self.request.uri} from {ip_address}")

class MainHandler(BaseHandler):
    def get(self):
        logging.info(Fore.YELLOW + f"The client connected with IP: {self.request.remote_ip}")
        self.render("index.html")

class VersionHandler(BaseHandler):
    def get(self):
        response = {
            'susv': '0.1',
            'python': sys.version.split(" ")[0],
            'tornado': tornado.version,
            'server': '1.0'
        }
        self.write(response)

class CheckStableFirmware(BaseHandler):
    def post(self):
        if not self.request.body:
            logging.warning(Fore.YELLOW + f"Empty request body from {self.request.remote_ip}.")
            return self.send_error(400, message='Empty request body.')

        try:
            data = tornado.escape.json_decode(self.request.body)
            build = build_to_int(data['build_date'])
            response = {
                'update_available': build < CURRENT_FIRMWARE["version"],
                'critical': build < CRITICAL_VERSION,
                'version': CURRENT_FIRMWARE["version"],
                'description': CURRENT_FIRMWARE["description"],
                "url": make_download_url(self.request, CURRENT_FIRMWARE),
                "url_old_frs": make_download_url(self.request, CURRENT_FIRMWARE, old=True),
                "device_info": self.request.headers.get("User-Agent", "Unknown")
            }
            self.write(response)
            logging.info(Fore.YELLOW + f"Response sent to {self.request.remote_ip}: {response}")
        except ValueError:
            logging.error(Fore.YELLOW + f"Unable to parse JSON from {self.request.remote_ip}.")
            self.send_error(400, message='Unable to parse JSON.')

application = tornado.web.Application([
    (r"/check_firmware", CheckStableFirmware),
    (r"/version", VersionHandler),
    (r"/", MainHandler),
    (r'/firmware/(.*)', tornado.web.StaticFileHandler, {'path': FIRMWARE_PATH}),
    (r"/(.*)", tornado.web.StaticFileHandler, {"path": "static"})
])

def main():
    application.listen(PORT)
    logging.info(Fore.GREEN + "Starting server...")
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()
# Logging - ветка с доработкой логирования