import logging
import telebot
from my_envs import MyEnvs
import handlers
import queue_processor
import time
import threading
import schedule
from random import randrange


# region инициализация логгирования

log_format = ("[%(asctime)s] %(levelname)s "
              "[%(filename)s.%(funcName)s] %(message)s")
logging.basicConfig(format=log_format, level=logging.INFO)

# endregion

# инициализация переменных окружения
envs = MyEnvs()

_number_of_messages = 0
""" Сколько сообщений осталось отправить """

# инициализация бота
bot = telebot.TeleBot(envs.BOT_TOKEN, parse_mode='HTML')
envs.BOT = bot

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
        queue_processor.update_pinned_message(envs)  # статус
        schedule.run_pending()  # расписания
        time.sleep(3)


def endless_sending():
    """ Отправка сообщений из очереди """

    while True:
        global _number_of_messages

        if _number_of_messages == 0:
            time.sleep(60)  # не нужно проверять слишком часто
            continue

        resp = handlers.send_queue_to_channel(envs, count=1)
        _number_of_messages -= 1
        wait_seconds = randrange(20*60, 30*60)
        logging.info(f"Ответ: '{resp}', ждём: {wait_seconds // 60} мин, "
                     f"{wait_seconds % 60} сек.")
        time.sleep(wait_seconds)


def add_messages():
    """ Обновляет глобальную переменную `_number_of_messages` """

    global _number_of_messages
    _number_of_messages = 5

# endregion


@bot.callback_query_handler(func=lambda call: True)
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
threading.Thread(target=background_ticks, daemon=True).start()
threading.Thread(target=endless_sending, daemon=True).start()

bot.infinity_polling(
    timeout=10,
    long_polling_timeout=5,
    logger_level=logging.WARNING,
    restart_on_change=True,
    path_to_watch=__file__
)
