from .base import PersistStateBase


class State(PersistStateBase):
    """Атрибуты класса сохраняются в файл при изменении"""

    read_timeout: int
    connect_timeout: int
    number_of_messages_per_day: int

    state_number_of_messages_to_send: int
    """Сколько осталось отправить"""

    state_status_message_id: int
    """Значения, определяющие состояние:
    - `0`: статус сообщения не должно быть
    - `-1`: статус сообщение нужно создать
    - `{id}`: id, ранее отправленного сообщения
    """

    state_last_status_message_text: str
    """Чтобы не обновлять такой же текст"""
