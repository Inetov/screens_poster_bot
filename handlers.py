import bot_actions
from telebot.types import Message
from my_envs import MyEnvs


def send_queue_to_channel(envs: MyEnvs):
    queue_images = bot_actions.get_queue_images(envs, delete=True)
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
        bot_actions.save_biggest_image(envs, message.photo)
        # l = bot_actions.get_queue_count(envs)
        # return f"Сохранил! Изображений в очереди: {l}"
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
                queue_images = bot_actions.get_queue_images(envs, True)
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
