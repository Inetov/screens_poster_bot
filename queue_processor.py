from my_envs import MyEnvs
import bot_actions
from telebot.apihelper import ApiTelegramException
from pathlib import Path
from os import listdir
import image_processing as imp
from telebot.util import quick_markup


def process_uploaded_images(envs: MyEnvs):
    uploaded_files = listdir(envs.UPLOADED_DIR)
    if not uploaded_files:
        return

    files_count = len(uploaded_files)
    for file_name in uploaded_files:
        img_path = Path(envs.UPLOADED_DIR, file_name)

        # TODO: по неизвестной причине срабатывает через раз (потоки?)
        if envs.CROP_DEBUG:
            # Создаём файлы сравнений и сохраняем в TEMP_DIR
            debug_path = Path(envs.TEMP_DIR, file_name)
            imp.create_debug_image(
                img_path.as_posix(), debug_path.as_posix())

        queue_path = Path(envs.QUEUE_DIR, file_name)
        imp.create_cropped_image(
            img_path.as_posix(), queue_path.as_posix())
        img_path.unlink()  # удаляем обработанный файл из UPLOADED_DIR

    # TODO: по неизвестной причине срабатывает через раз (потоки?)
    # envs.BOT.send_message(
    #     chat_id=envs.ADMIN_USER_ID,
    #     text=(f"Обработка загруженных изображений завершена: {files_count}"
    #           "\nОни ожидают в очереди: /queue"))


def update_pinned_message(envs: MyEnvs):
    bot = envs.BOT
    sfile = envs.STATUS_MESSAGE_FILE.as_posix()
    cnt = bot_actions.get_queue_count(envs)
    markup = quick_markup({
        '➡️ Отправить!': {'callback_data': 'queue_send'}
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
