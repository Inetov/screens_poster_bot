from my_envs import MyEnvs
from typing import Sequence
from telebot.types import (
    Message,
    InputMediaPhoto,
    PhotoSize,
)
from subprocess import getoutput
from pathlib import Path


_HELP_MESSAGE = """
Обрезает получаемые картинки и сохраняет в очередь.
Пересылает в канал "<a href="{c_link}">{c_name}</a>" по кнопке.

Команды:
/queue - показать очередь
/version - текущая версия
/restart - перезапуск с обновлённым кодом
/status - вывести и обновлять сообщение со статусом
/remove_status - убрать сообщение со статусом
"""


def get_help(envs: MyEnvs):
    """ справка по боту (команда /help) """

    c_name = envs.BOT.get_chat(envs.CHANNEL_ID).title
    c_link = envs.BOT.get_chat(envs.CHANNEL_ID).invite_link

    return _HELP_MESSAGE.format(c_name=c_name, c_link=c_link)


def get_version():
    git_cmd = r"git log -1 --pretty='format:%h%n%ai (%ar)'"
    git_log = getoutput(git_cmd)
    return git_log  # нужны доп. проверки?


def pull_repo():
    pull_cmd = "git pull --rebase"
    return getoutput(pull_cmd)


def get_queue_count(envs: MyEnvs):
    return len(list(envs.QUEUE_DIR.glob(envs.IMAGES_GLOB_PATTERN)))


def get_queue_images(envs: MyEnvs, with_caption=False, delete=False) -> Sequence[InputMediaPhoto]:
    max_display = 10

    result = []
    queue_files = list(envs.QUEUE_DIR.glob(envs.IMAGES_GLOB_PATTERN))
    queue_files.sort(key=lambda x: x.stat().st_ctime_ns)

    msg = [f"Всего изображений в очереди: {len(queue_files)}"]

    if len(queue_files) > max_display:
        queue_files = queue_files[:max_display]
        msg.append(f"Вот первые {max_display}")
    for file in queue_files:
        with open(file, 'rb') as photo:
            result.append(InputMediaPhoto(photo.read()))
            if delete:
                file.unlink()

    if result and with_caption:
        result[0].caption = '\n'.join(msg)

    return result


def get_id_from_file(file_path: str):
    with open(file_path, mode='r') as f:
        return int(f.read())


def save_id_to_file(file_path: str, message_id: int):
    with open(file_path, mode='w') as f:
        f.write(str(message_id))


def remove_status_message(envs: MyEnvs):
    message_id = get_id_from_file(envs.STATUS_MESSAGE_FILE.as_posix())
    try:
        msg_args = {
            'chat_id': envs.ADMIN_USER_ID,
            'message_id': message_id,
        }
        envs.BOT.unpin_chat_message(**msg_args)
        envs.BOT.delete_message(**msg_args)
    except Exception as ex:
        print(ex)
    # нет файла - нет уведомлений
    envs.STATUS_MESSAGE_FILE.unlink(missing_ok=True)


def delete_next_pin_message(message: Message, envs: MyEnvs):
    """ Предназначен для использования в функции
    `register_next_step_handler_by_chat_id`

    Удаляет полученное сообщение, если его тип = 'pinned_message' и
    вызывает метод `clear_step_handler_by_chat_id` """

    if message.content_type == 'pinned_message':
        envs.BOT.delete_message(envs.ADMIN_USER_ID, message.message_id)
    envs.BOT.clear_step_handler_by_chat_id(envs.ADMIN_USER_ID)


def save_biggest_image(envs: MyEnvs, sizes: list[PhotoSize] | None):
    """ Сохраняет самый большой файл и возвращает путь к созданному. """

    assert sizes
    # по идее не может быть сообщения с фотками и пустым массивом, но...

    biggest = max(sizes, key=lambda x: x.file_size)

    file_info = envs.BOT.get_file(biggest.file_id)
    suffix = Path(file_info.file_path).suffix
    new_path = Path(f"{envs.UPLOADED_DIR}/{file_info.file_unique_id}{suffix}")
    if not new_path.exists():  # предполагаем, что id таки уникальный
        downloaded_file = envs.BOT.download_file(file_info.file_path)
        with open(new_path, "wb") as new_file:
            new_file.write(downloaded_file)

    return new_path.as_posix()
