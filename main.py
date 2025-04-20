import logging
import threading
import time
from random import randrange

import schedule
import telebot

import handlers
import queue_processor
from my_envs import MyEnvs
from persist_state import State

# region инициализации

# логирование
log_format = "[%(asctime)s] %(levelname)s [%(filename)s.%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)


# переменные окружения
envs = MyEnvs()

# Настройки и состояние
envs.STATE = State(data_path=envs.STATE_FILE, default_json_path="_default_settings.json")

# бот
telebot.apihelper.CONNECT_TIMEOUT = envs.STATE.connect_timeout
telebot.apihelper.READ_TIMEOUT = envs.STATE.read_timeout
bot = telebot.TeleBot(
    envs.BOT_TOKEN,
    parse_mode="HTML",
)
envs.BOT = bot

# endregion

# region служебные функции


def ready_check():
    assert envs
    logging.info("Инициализация окружения успешно завершена")

    assert envs.BOT
    bot_info = envs.BOT.get_me()
    logging.info("Инициализация бота, ответ: %s", bot_info)


# endregion

# region фоновые потоки


def background_ticks():
    """Обновление статуса, обработка расписаний (schedule)
    и прочие мелкие действия"""

    while True:
        try:
            queue_processor.update_pinned_message(envs)  # статус
            schedule.run_pending()  # расписания
            time.sleep(3)
        except Exception as ex:
            if "timeout" in str(ex):
                logging.error(
                    "Поймали очередной таймаут, типа %s, но тут не страшно",
                    type(ex),
                    exc_info=True,
                )
            pass


def endless_sending():
    """Отправка сообщений из очереди"""

    while True:
        messages_to_send = envs.STATE.state_number_of_messages_to_send

        if not messages_to_send:
            time.sleep(60)  # не нужно проверять слишком часто
            continue

        resp = handlers.send_queue_to_channel(envs, count=1)
        if "Отправлено" in resp:
            envs.STATE.state_number_of_messages_to_send = messages_to_send - 1
            wait_seconds = randrange(20 * 60, 30 * 60)
            logging.info(
                "Отправили картинку, ответ: '%s', ждём: %s мин, %s сек.",
                resp,
                wait_seconds // 60,
                wait_seconds % 60,
            )
            time.sleep(wait_seconds)
        else:
            logging.debug("Пришло время отправлять пост, но: %s", resp)

            time.sleep(60)


def add_messages():
    """Обновляет переменную в настройках `state_number_of_messages_to_send`"""

    add_amount = envs.STATE.number_of_messages_per_day or 0
    # по идее тут всегда должна быть цифра, определённая в _default_settings.json
    logging.info("Запущен метод добавления постов, планируется добавить: %s", add_amount)

    if p := envs.STATE.state_number_of_messages_to_send:
        add_amount += p

    envs.STATE.state_number_of_messages_to_send = add_amount
    logging.info("Теперь Переменная 'state_number_of_messages_to_send' = %s", add_amount)


def no_luck_today():
    """Очищает переменную в настройках `state_number_of_messages_to_send`

    (что бы не копились)"""

    envs.STATE.state_number_of_messages_to_send = 0
    logging.info("Переменная 'state_number_of_messages_to_send' установлена на '0'")


# endregion


@bot.callback_query_handler(func=lambda *_: True)
def callback_handler(cbq: telebot.types.CallbackQuery):
    method, *args = cbq.data.split()
    if method == "queue_send" and args[0].isnumeric():
        result = handlers.send_queue_to_channel(envs, count=int(args[0]))
        bot.answer_callback_query(cbq.id, text=result)


@bot.message_handler(content_types=["text", "photo"])
def get_text_messages(message: telebot.types.Message):
    if message.from_user.id != envs.ADMIN_USER_ID:
        return  # не реагируем на сообщения других людей

    response = None
    try:
        response = handlers.process_message(message, envs)

    except Exception as ex:
        response = f"Не смог обработать сообщение 😔\n{ex}"
    finally:
        if response:
            bot.reply_to(message=message, text=response)


ready_check()

schedule.every().day.at("12:00", "Europe/Moscow").do(add_messages)
schedule.every().day.at("23:50", "Europe/Moscow").do(no_luck_today)
threading.Thread(target=background_ticks, daemon=True).start()
threading.Thread(target=endless_sending, daemon=True).start()

bot.infinity_polling(
    timeout=10,
    long_polling_timeout=envs.STATE.read_timeout * 2,
    interval=3,  # из базового polling
    logger_level=logging.WARNING,
    restart_on_change=True,
    path_to_watch=__file__,
)
