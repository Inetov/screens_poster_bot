from my_envs import MyEnvs
import bot_actions
from telebot.apihelper import ApiTelegramException
from pathlib import Path
import image_processing as imp
from telebot.util import quick_markup


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
    sfile = envs.STATUS_MESSAGE_FILE.as_posix()
    cnt = bot_actions.get_queue_count(envs)
    markup = quick_markup({
        '➡️ Отправить 10!': {'callback_data': 'queue_send 10'}
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
        message_args['message_id'] = pm.message_id
    elif not envs.STATUS_MESSAGE_FILE.exists():
        return  # нет закрепа, нет сохранённого - нечего обновлять
    else:
        message_args['message_id'] = bot_actions.get_id_from_file(sfile)

    try:
        bot.edit_message_text(**message_args)
    except ApiTelegramException:    # не получилось изменить
        message_args.pop('message_id', None)  # будем создавать новое
        new_msg = bot.send_message(**message_args)
        bot.register_next_step_handler_by_chat_id(
            chat_id=envs.ADMIN_USER_ID,
            callback=bot_actions.delete_next_pin_message,
            envs=envs
        )
        bot.pin_chat_message(
            chat_id=envs.ADMIN_USER_ID,
            message_id=new_msg.message_id,
            disable_notification=True
        )

        bot_actions.save_id_to_file(sfile, new_msg.message_id)


def file_name_append(file_name, append: str):
    p = Path(file_name)
    return f"{p.stem}{append}{p.suffix}"
