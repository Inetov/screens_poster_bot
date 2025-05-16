import json
from logging import Logger
from pathlib import Path

ENCODING = "utf-8"


class PersistStateBase:
    """Класс для сохранения состояния на диск.

    Вызывает чтение/запись файла при обращении к аттрибутам!\
    (кроме тех, что начинаются с `_`)
    
    Однако: изменение файла извне не предполагается, по этому чтение кешируется,
    если `stat` файла не изменился"""

    _data_path: Path
    _logger: Logger | None = None

    _last_read_hash = 0

    def _debug(self, *args, **kwargs):
        """Пишет сообщение с уровнем 'DEBUG', если `_logger` существует.

        В остальном полностью аналогичен вызову `logging.debug`.

        Log 'msg % args' with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)"""
        if self._logger:
            self._logger.debug(*args, **kwargs)

    def _get_public_fields_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def __init__(
        self,
        data_path: str | Path = "data/state.json",
        default_json_path: str = "",
        logger: Logger | None = None,
    ) -> None:
        """Возвращает настроенный экземпляр и создаёт путь для `data_path` (но не сам файл)

        Args:
            data_path (str, optional): Путь к файлу. По умолчанию: "data/state.json".
            default_json_path (str, optional): Путь к файлу, из которого следует взять значения,
                если файл `data_path` пуст.
            logger (Logger | None, optional): Логгер для целей отладки.
        """

        if not isinstance(data_path, Path):
            data_path = Path(data_path)
        self._data_path = data_path
        self._data_path.parent.mkdir(exist_ok=True, parents=True)

        if default_json_path and (
            not self._data_path.exists() or self._data_path.stat().st_size == 0
        ):
            with open(default_json_path, mode="r", encoding=ENCODING) as f:
                self.__dict__.update(json.load(f))

        self._logger = logger

    def _update_self_from_file(self):
        with open(self._data_path, "r", encoding=ENCODING) as f:
            self.__dict__.update(json.load(f))
        self._debug("Состояние прочитано из файла '%s'", self._data_path)

    def __getattribute__(self, name: str):
        if (
            not name.startswith("_")
            and self._data_path.exists()
            and hash(self._data_path.stat()) != self._last_read_hash
        ):
            self._update_self_from_file()
            self._last_read_hash = hash(self._data_path.stat())

        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value) -> None:
        object.__setattr__(self, name, value)
        if not name.startswith("_"):
            with open(self._data_path, "w", encoding=ENCODING) as f:
                json.dump(self._get_public_fields_dict(), f, ensure_ascii=False, indent=4)
            self._debug(
                "Состояние сохранено в файл! Переменная '%s'='%s', файл: '%s'",
                name,
                value,
                self._data_path,
            )
