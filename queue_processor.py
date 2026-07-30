import logging
from datetime import datetime
from pathlib import Path

from telebot.apihelper import ApiTelegramException
from telebot.util import quick_markup

import bot_actions
import image_processing as imp
from my_envs import MyEnvs

logger = logging.getLogger(__name__)

def process_one_image(image_path: str | Path, envs: MyEnvs):
    if isinstance(image_path, str):
        image_path = Path(image_path)

    debug_path = None
    if envs.CROP_DEBUG:
        # Создаём файлы сравнений и сохраняем в TEMP_DIR
        # тут делаем имя удобным, в других местах в этом нет смысла,
        # так как работа с файлами напрямую не предполагается
        dt_file_name = datetime.now().strftime(r"%Y%m%d-%H%M%S_%f")
        debug_path = Path(envs.TEMP_DIR, dt_file_name).with_suffix(image_path.suffix).as_posix()
        imp.crop_logger.setLevel("DEBUG")

    queue_path = Path(envs.QUEUE_DIR, image_path.name)
    imp.create_cropped_image(image_path.as_posix(), queue_path.as_posix(), debug_path=debug_path)
    if queue_path.exists() and queue_path.stat().st_size > 0:  # изображение создалось
        image_path.unlink()
    return queue_path.as_posix()


def update_pinned_message(envs: MyEnvs):
    bot = envs.BOT

    message_id = envs.STATE.state_status_message_id
    if not message_id:
        return  # нет закрепа, нет сохранённого - нечего обновлять

    cnt = bot_actions.get_queue_count(envs)
    new_status_msg = envs.STATUS_MESSAGE.format(cnt=cnt)
    if getattr(envs.STATE, "state_last_status_message_text", None) == new_status_msg:
        return  # статус не изменился

    # если дошли сюда: нужно либо обновлять, либо создавать, готовимся:
    markup = quick_markup({
        '➡️🖼️ 1!': {'callback_data': 'queue_send 1'}
    }, row_width=1)
    message_args = {
        "message_id": message_id,
        "chat_id": envs.ADMIN_USER_ID,
        "text": new_status_msg,
        "reply_markup": markup,
    }

    if message_id == -1:  # значит статус сообщение нужно создать
        message_args.pop("message_id", None)
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

        envs.STATE.state_status_message_id = new_msg.message_id
        return

    # если дошли сюда - предполагаем наличие сообщения в закрепе и есть чем его обновлять

    # убрано взаимодействие с bot.get_chat(envs.ADMIN_USER_ID).pinned_message
    # так как периодически поле pinned_message приходит пустым, даже когда закреп есть
    try:
        bot.edit_message_text(**message_args)
        envs.STATE.state_last_status_message_text = new_status_msg

    except ApiTelegramException as ex:
        if "Bad Request: message is not modified" in ex.description:
            # если в закрепе уже такое же сообщение, то обновляем его в файле
            envs.STATE.state_last_status_message_text = new_status_msg
            return

        if "Too Many Requests" in ex.description:
            from datetime import timedelta

            # last_part = ex.description.split()[-1]
            # if last_part.isdecimal():
            secs = ex.result_json.get("parameters", {}).get("retry_after")
            if isinstance(secs, int):
                to_wait_str = str(timedelta(seconds=secs))
            else:
                to_wait_str = "НЕТ ЗНАЧЕНИЯ"

            logger.warning("Похоже, что нас забанил сервер! Ждать: %s\n%s", to_wait_str, repr(ex))
            # TODO: может добавить ожидание прям тут?
            return

        # но сюда же, видимо, попадаем и при других ошибках, надо бы отладить:
        logger.error(
            "Поймали ошибку из обёртки, при обновлении закрепа:",
            exc_info=ex,
        )

    # необработанную тут ошибку поймает вызывающий метод
    # except Exception as ex:
    #     logging.error(
    #         "Поймали ошибку типа %s, при обновлении закрепа:",
    #         type(ex),
    #         exc_info=ex,
    #     )


def file_name_append(file_name, append: str):
    p = Path(file_name)
    return f"{p.stem}{append}{p.suffix}"
