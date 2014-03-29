# -*- coding: utf-8 -*-

from parser import BGChatParser

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(
        description=unicode(u'Парсер чатика BestGothic.com в свою уютненькую БДшечку SQLite. '
                            u'Просматривать содержимое базы SQLite можно любым удобным вам способом, '
                            u'например через Sqliteman (http://sourceforge.net/projects/sqliteman/)'),
        epilog=unicode(u'Нет смысла ставить интервал менее 30 секунд при периодическом парсинге. '
                       u'Практически никогда не бывает более 20 сообщений за 30 секунд, '
                       u'да и хостеры бестготика побанить могут за постоянные запросы.')
    )
    parser.add_argument('-t', action='store_true', default=False,
                        help=unicode(u'Включать только текст. '
                                     u'Любая HTML-сущность (Например смайл) будет проигнорирована. '
                                     u'По умолчанию отключено.'))
    parser.add_argument('-p', action='store_true',
                        help=unicode(u'Включает режим периодического парсинга.'))
    parser.add_argument('-i', type=int, default=30,
                        help=unicode(u'Интервал для парсинга чата в секундах. По умолчанию 30.'))
    parser.add_argument('db', type=unicode, nargs='?', default=u'bgchat.db',
                        help=unicode(u'Путь до файла с базой данных SQLite, в которую вы хотите парсить чат.'))
    args = parser.parse_args()

    parser = BGChatParser(html=not args.t, interval=args.i, db_options={'name': args.db})
    if args.p:
        parser.run()
    else:
        parser.parse()