import json
import os


class Settings:
    _file_path: str

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

        if not os.path.exists(self._file_path) or os.stat(self._file_path).st_size == 0:
            self._load_default()

    def _set_all(self, object: dict):
        """ЗАМЕНЯЕТ все текущие настройки указанным объектом"""

        with open(self._file_path, mode="w", encoding="utf-8") as f:
            json.dump(object, f)

    def _load_default(self):
        with open("_default_settings.json", mode="r", encoding="utf-8") as f:
            self._set_all(json.load(f))

    def get_all(self) -> dict:
        with open(self._file_path, mode="r", encoding="utf-8") as f:
            return json.load(f)

    def get(self, name: str):
        return self.get_all().get(name)

    def set(self, name: str, value):
        all_setts = self.get_all()
        all_setts[name] = value

        self._set_all(all_setts)
