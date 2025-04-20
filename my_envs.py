from dataclasses import dataclass
from os import environ
from pathlib import Path

from telebot import TeleBot

from persist_state import State


@dataclass
class MyEnvs:
    _REQUIREMENTS_ENVS = {
        "BOT_TOKEN": None,
        "ADMIN_USER_ID": lambda v: int(v),
        "CHANNEL_ID": lambda v: int(v),
        "CROP_DEBUG": lambda v: bool(v),
    }
    _DATA_DIR = "data"

    # -

    QUEUE_DIR = Path(_DATA_DIR, "queue")
    UPLOADED_DIR = Path(_DATA_DIR, "uploaded")
    TEMP_DIR = Path(_DATA_DIR, "temp")

    BOT: TeleBot
    STATE: State
    """Актуальные настройки и состояние.
    
    Внимание! Вызывает чтение/запись файла при обращении к аттрибутам!
    
    (кроме тех, что начинаются с `_`"""

    STATE_FILE = Path(_DATA_DIR, "state.json")

    BOT_TOKEN: str
    ADMIN_USER_ID: int
    CHANNEL_ID: int
    CROP_DEBUG: bool
    IMAGES_GLOB_PATTERN: str = environ.get("IMAGES_GLOB_PATTERN", "*.jpg")

    STATUS_MESSAGE = "Изображений в очереди (/queue) :"

    def __init__(self) -> None:
        """Проверяет наличие необходимых переменных окружения
        и сохраняет их в экземпляре"""

        for env_name, func in self._REQUIREMENTS_ENVS.items():
            if env_val := environ.get(env_name):
                if func:
                    try:
                        env_val = func(env_val)  # type: ignore
                    except Exception as ex:
                        raise ValueError(
                            "Значение переменной окружения: "
                            f"{env_name} = '{env_val}' "
                            "не прошло провверку"
                        ) from ex
                setattr(self, env_name, env_val)
            else:
                raise KeyError(f"Не найдена переменная окружения '{env_name}'")

        try:
            for x in [self.QUEUE_DIR, self.UPLOADED_DIR, self.TEMP_DIR]:
                x.mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            raise
