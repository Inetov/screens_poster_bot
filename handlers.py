from os.path import exists

from telebot.types import Message

import bot_actions
from my_envs import MyEnvs
from queue_processor import process_one_image


def send_queue_to_channel(envs: MyEnvs, count: int):
    """ Отправляет в канал указанное количество изображений.
    Удаляет их из очереди! """

    queue_images = bot_actions.get_queue_images(envs, count=count, delete=True)
    imgs_cnt = len(queue_images)
    if imgs_cnt > 1:
        envs.BOT.send_media_group(
            media=queue_images,  # type: ignore
            chat_id=envs.CHANNEL_ID)
        return f"Отправлено! {imgs_cnt}"
    elif imgs_cnt == 1:
        envs.BOT.send_photo(
            photo=queue_images[0].media,
            chat_id=envs.CHANNEL_ID)
        return f"Отправлено! {imgs_cnt}"
    else:
        return "В очереди ничего нет"


def process_message(message: Message, envs: MyEnvs):
    chat_id = message.from_user.id

    if message.content_type == 'photo':
        src_path = bot_actions.save_biggest_image(envs, message.photo)
        processed_path = process_one_image(src_path, envs)
        if exists(processed_path):
            envs.BOT.delete_message(chat_id, message.message_id)
    else:
        match isinstance(message.text, str) and message.text.lower():
            case "/help":
                return bot_actions.get_help(envs)

            case "/status":
                # тут просто создаётся файл, далее его прочитает
                # метод update_pinned_message из фонового потока
                # и не найдя такое сообщение - создаст новое
                envs.STATUS_MESSAGE_FILE.write_text(str(-1))
            case "/remove_status":
                if not envs.STATUS_MESSAGE_FILE.exists():
                    return "Нечего убирать."
                bot_actions.remove_status_message(envs)

            case "/queue":
                queue_images = bot_actions.get_queue_images(envs,
                                                            with_caption=True,
                                                            delete=False)
                if len(queue_images) > 1:
                    envs.BOT.send_media_group(
                        media=queue_images,  # type: ignore
                        chat_id=chat_id,
                        reply_to_message_id=message.message_id)
                elif len(queue_images) == 1:
                    envs.BOT.send_photo(
                        photo=queue_images[0].media,
                        caption=queue_images[0].caption,
                        chat_id=chat_id,
                        reply_to_message_id=message.message_id)
                else:
                    return "В очереди ничего нет"

            case "/restart":
                return "Лог <code>git pull</code>:\n" + bot_actions.pull_repo()

            case "/version":
                return f"Моя версия: <code>{bot_actions.get_version()}</code>"

            case _:
                return "Я тебя не понимаю. Напиши /help."
