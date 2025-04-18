import logging
import threading
import time
from random import randrange

import schedule
import telebot

import handlers
import queue_processor
from my_envs import MyEnvs
from settings import Names, Settings

# region инициализации

# логирование
log_format = ("[%(asctime)s] %(levelname)s "
              "[%(filename)s.%(funcName)s] %(message)s")
logging.basicConfig(format=log_format, level=logging.INFO)


# переменные окружения
envs = MyEnvs()

# Настройки и состояние
envs.SETTINGS = Settings(envs.SETTINGS_FILE)
envs.READ_TIMEOUT = envs.SETTINGS.get(Names.SETTING_READ_TIMEOUT) or 30

# бот
telebot.apihelper.CONNECT_TIMEOUT = envs.READ_TIMEOUT
telebot.apihelper.READ_TIMEOUT = envs.READ_TIMEOUT
bot = telebot.TeleBot(
    envs.BOT_TOKEN,
    parse_mode='HTML',
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
    """ Обновление статуса, обработка расписаний (schedule)
    и прочие мелкие действия """

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
    """ Отправка сообщений из очереди """

    while True:
        messages_to_send = envs.SETTINGS.get(Names.STATE_MESSAGES_TO_SEND)

        if not messages_to_send:
            time.sleep(60)  # не нужно проверять слишком часто
            continue

        resp = handlers.send_queue_to_channel(envs, count=1)
        if "Отправлено" in resp:
            envs.SETTINGS.set(Names.STATE_MESSAGES_TO_SEND, messages_to_send - 1)
            wait_seconds = randrange(20 * 60, 30 * 60)
            logging.info(
                f"Отправили картинку, ответ: '{resp}', "
                f"ждём: {wait_seconds // 60} мин, "
                f"{wait_seconds % 60} сек."
            )
            time.sleep(wait_seconds)
        else:
            logging.info("Пришло время отправлять пост, но: %s", resp)
            time.sleep(60)


def add_messages():
    """Обновляет переменную в настройках `Settings.STATE_MESSAGES_TO_SEND`"""

    add_amount = envs.SETTINGS.get(Names.SETTIGS_MESSAGES_PER_DAY) or 0
    # по идее тут всегда должна быть цифра, определённая в _default_settings.json
    logging.info(
        "Запущен метод добавления постов, планируется добавить: %s", add_amount
    )

    if (p := envs.SETTINGS.get(Names.STATE_MESSAGES_TO_SEND)) and isinstance(p, int):
        add_amount += p

    envs.SETTINGS.set(Names.STATE_MESSAGES_TO_SEND, add_amount)
    logging.info("Теперь сегодня на отправку: %s", add_amount)


def no_luck_today():
    """Очищает переменную в настройках `Settings.STATE_MESSAGES_TO_SEND`

    (что бы не копились)"""

    logging.info(
        "Переменная конфига '%s' установлена на '0'.", Names.STATE_MESSAGES_TO_SEND
    )
    envs.SETTINGS.set(Names.STATE_MESSAGES_TO_SEND, 0)


# endregion


@bot.callback_query_handler(func=lambda *_: True)
def callback_handler(cbq: telebot.types.CallbackQuery):
    method, *args = cbq.data.split()
    if method == 'queue_send' and args[0].isnumeric():
        result = handlers.send_queue_to_channel(envs, count=int(args[0]))
        bot.answer_callback_query(cbq.id, text=result)


@bot.message_handler(content_types=['text', 'photo'])
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
    long_polling_timeout=120,
    interval=3,  # из базового polling
    logger_level=logging.WARNING,
    restart_on_change=True,
    path_to_watch=__file__,
)
