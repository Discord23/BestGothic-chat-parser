BestGothic-chat-parser
======================

usage: bgchat.py [-h] [-t] [-p] [-i I] [db]

Парсер чатика BestGothic.com в свою уютненькую БДшечку SQLite. Просматривать
содержимое базы SQLite можно любым удобным вам способом, например через
Sqliteman (http://sourceforge.net/projects/sqliteman/)

positional arguments:
  db          Путь до файла с базой данных SQLite, в которую вы хотите парсить
              чат.

optional arguments:

  -h, --help  show this help message and exit

  -t          Включать только текст. Любая HTML-сущность (Например смайл)
              будет проигнорирована. По умолчанию отключено.

  -p          Включает режим периодического парсинга.

  -i I        Интервал для парсинга чата в секундах. По умолчанию 30.

Нет смысла ставить интервал менее 30 секунд при периодическом парсинге.
Практически никогда не бывает более 20 сообщений за 30 секунд, да и хостеры
бестготика побанить могут за постоянные запросы.
