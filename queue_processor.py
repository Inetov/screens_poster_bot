import logging
from pathlib import Path

from telebot.apihelper import ApiTelegramException
from telebot.util import quick_markup

import bot_actions
import image_processing as imp
from my_envs import MyEnvs
from settings import Names


def process_one_image(image_path: str | Path, envs: MyEnvs):
    if isinstance(image_path, str):
        image_path = Path(image_path)

    if envs.CROP_DEBUG:
        # Создаём файлы сравнений и сохраняем в TEMP_DIR
        debug_path = Path(envs.TEMP_DIR, image_path.name)
        imp.create_debug_image(image_path.as_posix(), debug_path.as_posix())

    queue_path = Path(envs.QUEUE_DIR, image_path.name)
    imp.create_cropped_image(image_path.as_posix(), queue_path.as_posix())
    image_path.unlink()
    return queue_path.as_posix()


def update_pinned_message(envs: MyEnvs):
    bot = envs.BOT
    message_id = envs.SETTINGS.get(Names.STATE_STATUS_MESSAGE_ID)
    if not message_id:
        return  # нет закрепа, нет сохранённого - нечего обновлять
    cnt = bot_actions.get_queue_count(envs)
    markup = quick_markup({
        '➡️🖼️ 1!': {'callback_data': 'queue_send 1'}
    }, row_width=1)
    message_args = {
        'chat_id': envs.ADMIN_USER_ID,
        'text': f"{envs.STATUS_MESSAGE} {cnt}",
        'reply_markup': markup
    }

    pm = bot.get_chat(envs.ADMIN_USER_ID).pinned_message
    if pm:
        if pm.text == message_args['text']:
            return  # есть закреп уже с нужной инфой
        message_args["message_id"] = pm.message_id
    else:
        message_args["message_id"] = message_id

    try:
        bot.edit_message_text(**message_args)
    except ApiTelegramException as ex:  # не получилось изменить
        # но сюда же, видимо, попадаем и при других ошибках, надо бы отладить:
        logging.warning(
            "Поймали ошибку типа %s, считаем, что не удалось обновить закреп",
            type(ex),
            exc_info=ex,
        )
        return
        # TODO: пока тут специально убрано создание нового, чтобы отловить нужную ошибку
        message_args.pop("message_id", None)  # будем создавать новое
        new_msg = bot.send_message(**message_args)
        bot.register_next_step_handler_by_chat_id(
            chat_id=envs.ADMIN_USER_ID,
            callback=bot_actions.delete_next_pin_message,
            envs=envs,
        )
        bot.pin_chat_message(
            chat_id=envs.ADMIN_USER_ID,
            message_id=new_msg.message_id,
            disable_notification=True,
        )

        envs.SETTINGS.set(Names.STATE_STATUS_MESSAGE_ID, new_msg.message_id)


def file_name_append(file_name, append: str):
    p = Path(file_name)
    return f"{p.stem}{append}{p.suffix}"
