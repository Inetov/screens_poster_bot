import logging
import telebot
from my_envs import MyEnvs
import handlers
import queue_processor
import time
import threading


# region инициализация логгирования

log_format = ("[%(asctime)s] %(levelname)s "
              "[%(filename)s.%(funcName)s] %(message)s")
logging.basicConfig(format=log_format, level=logging.INFO)

# endregion

# инициализация переменных окружения
envs = MyEnvs()

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

# def get_buttons():
#     btns = [telebot.types.KeyboardButton(f"{x + 1}") for x in range(3)]
#     return (
#         telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
#         .row(*btns)
#     )

# endregion


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(cbq: telebot.types.CallbackQuery):
    if cbq.data == 'queue_send':
        result = handlers.send_queue_to_channel(envs)
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


def background_processor():
    while True:
        queue_processor.process_uploaded_images(envs)
        queue_processor.update_pinned_message(envs)
        time.sleep(3)


threading.Thread(target=background_processor).start()

bot.infinity_polling(
    timeout=10,
    long_polling_timeout=5,
    logger_level=logging.WARNING,
    restart_on_change=True,
    path_to_watch=__file__
)