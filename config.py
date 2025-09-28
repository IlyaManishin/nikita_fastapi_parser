import os
from configparser import ConfigParser
import logging

CONFIG_PATH = "config.ini"
if not os.path.exists(CONFIG_PATH):
    file = open(CONFIG_PATH, "w")
    file.close()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("logger.log"),
    ]
)

class Parser(ConfigParser):
    def __init__(self, file_path: str | None):
        if not file_path:
            file_path = CONFIG_PATH
        self.file_path = file_path

        super().__init__()
        self.read(self.file_path)

    def save(self):
        with open(self.file_path, "w") as file:
            self.write(file)

    def set_default_field(self, key: str, value: str):
        self["DEFAULT"][key] = value
        self.save()

    def get_default_field(self, key: str) -> None:
        if key not in self["DEFAULT"]:
            return None
        return self["DEFAULT"][key]


if __name__ == "__main__":
    pass
