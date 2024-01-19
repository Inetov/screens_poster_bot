# Монитрование

`/app/data/` - каталог, в котором будут хранится данные

`/app/repo_key` - файл с ssh ключём для репозитория


# Переменные окружения

`BOT_TOKEN` - токен доступа к боту

`ADMIN_USER_ID` - id пользователя с правами админа

`CHANNEL_ID` - id каналы, в который отправляются посты

`CROP_DEBUG` - создавать файлы сравнения для отладки (папка `data/temp`)

`REPO_URL` - путь к репозиторию (SSH), например: `git@github.com:Inetov/screens_poster_bot.git`

`IMAGES_GLOB_PATTERN` - glob паттер для поиска изображений в локальных папках. По-умолчанию `*.jpg`
