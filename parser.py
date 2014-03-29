# -*- coding: utf-8 -*-

import datetime
import locale
import logging
import lxml.html
import mechanize
import time
import traceback
import sqlite3
import sys
import urllib2
try:
    import pynotify

    pynotify_app = pynotify.init('bgchat')

    def do_pynotify(title, text):
        try:
            pynotify.Notification(title, text).show()
        except Exception as e:
            print u'Какая-то хуйня с pynotify'
except ImportError:
    pynotify = None

    def do_pynotify(title, text):
        pass


class BGChatParser(object):
    DATELINE_FORMAT = u'(%d %B %Y - %H:%M )'
    USER_AGENT = (u'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  u'Chrome/29.0.1547.62 Safari/537.36')
    USERNAME = 'simpleBot'
    PASSWORD = '5nnT99K8DFILjvhXRugi4fVZ'
    BEST_HOST = 'http://bestgothic.com/'
    STATE = 'anonymous'

    def __init__(self, db_options=None, log_options=None, **options):
        self._init_logging(**(log_options or {}))
        self._init_db(**(db_options or {}))
        self._init_data(**options)

    def __del__(self):
        self._close_db()

    def _init_logging(self, **options):
        log = logging.getLogger(options.pop('logger', 'bg_chat_parser'))
        log.setLevel(options.pop('loglevel', logging.DEBUG))
        formatter = logging.Formatter(**options.pop('log_format', {'fmt': '[%(asctime)s] %(levelname)s: %(message)s',
                                                                   'datefmt': '%Y-%m-%d %H:%M:%S'}))
        fh = logging.FileHandler(options.pop('logfile', 'bgchat.log'))
        fh.setFormatter(formatter)
        log.addHandler(fh)
        self.log = log

    def _init_db(self, **options):
        db_name = options.pop('name', 'bgchat.db')
        try:
            self.db = sqlite3.connect(db_name)
        except sqlite3.OperationalError:
            self.db = sqlite3.connect('bgchat.db')
            sys.stderr.write(u'Не удалось создать базу данных %s.\n'
                             u'Будет использована стандартная база данных bgchat.db\n' % (db_name,))
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()

    def _close_db(self):
        self.cursor.close()
        self.db.close()

    def _init_data(self, interval=30, **options):
        locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
        self.last = None
        self.REQUEST_INTERVAL = interval
        if interval < 15:
            self.REQUEST_INTERVAL = 15
            sys.stderr.write(u'Выбран слишком частый переиод обновления. Период обновления сброшен на 15 секунд.\n')
        self.options = options
        try:
            self.last = self._fetch_one('SELECT * FROM messages ORDER BY id DESC LIMIT 1')
        except sqlite3.OperationalError:
            self._create_chat_table()
        self._reset_new()

    def _reset_new(self):
        self.new = 0

    def _create_chat_table(self):
        self.cursor.execute('CREATE TABLE `messages` '
                            '(`id` INTEGER PRIMARY KEY AUTOINCREMENT, '
                            '`message` TEXT, `author` TEXT, `dateline` INTEGER)')

    def _fetch_one(self, sql, params=None):
        self.cursor.execute(sql, params or [])
        return self.cursor.fetchone()

    def _get_response(self):
        request = urllib2.Request(url=self.BEST_HOST, headers={'User-Agent': self.USER_AGENT})
        return urllib2.urlopen(request)

    def create_entry(self, data):
        self.new += 1
        self.last = data
        do_pynotify(u'[%s] %s' % (datetime.datetime.fromtimestamp(data['dateline']), data['author']), data['message'])
        return self.cursor.execute('INSERT INTO `messages`(`message`, `author`, `dateline`) VALUES(?, ?, ?)',
                                   [data['message'], data['author'], data['dateline']])

    def parse_dateline(self, dateline):
        try:
            return int(time.mktime(datetime.datetime.strptime(dateline.encode('utf-8'), self.DATELINE_FORMAT).timetuple()))
        except ValueError:
            return int(time.mktime(datetime.datetime.strptime(dateline.encode('utf-8'), '(%d %B %Y - %I:%M %p)').timetuple()))

    def parse_message(self, elem):
        if self.options.get('html', False):
            return u'%s%s' % (elem.text or '', u''.join([lxml.html.tostring(x) for x in elem.iterchildren()]),)
        return u''.join([x for x in elem.itertext()])

    def parse_data(self, data):
        doc = lxml.html.document_fromstring(data, parser=lxml.html.HTMLParser(encoding='utf-8'))
        data = []
        for elem in doc.cssselect('#shoutbox-shouts-table tr'):
            children = elem.getchildren()
            d = children[3].getchildren()
            try:
                author = u''.join([x for x in children[1].getchildren()[1].itertext()])
            except IndexError:
                author = children[1].text
            message = self.parse_message(d[1])
            dateline = self.parse_dateline(d[0].text)
            data.append({'author': author, 'dateline': dateline, 'message': message})

        last_date = data[0]['dateline']
        last_inc = 1
        for d in reversed(data):
            if d['dateline'] == last_date:
                d['dateline'] = last_date + last_inc
                last_inc += 1
            else:
                last_date = d['dateline']
                last_inc = 1
        return data

    def log_to_db(self, data):
        self._reset_new()
        for d in reversed(data):
            if self.last is None:
                self.create_entry(d)
                continue
            diff = self.last['dateline'] - d['dateline']
            if diff < 30:
                check = self._fetch_one('SELECT * FROM messages WHERE dateline > ? AND author=? AND message=?',
                                        [d['dateline'] - 60, d['author'], d['message']])
                if check is None:
                    self.create_entry(d)
            elif diff < -60:
                self.create_entry(d)

        if self.new > 0:
            self.db.commit()
            self.do_user_log(u'Добавлено %s новых сообщений' % (self.new,))

    def do_user_log(self, message=None, level='info'):
        getattr(self.log, level, lambda x: None)(message)
        if level != 'info':
            do_pynotify(u'Уютненький чатик', message)

    def get_data(self, response):
        data = []
        success = False
        while True:
            new_data = response.read(1000)
            data.append(new_data)
            if len(new_data) < 1:
                break
            if 'ipb.shoutbox.myMemberID' in new_data or 'ipb.shoutbox.can_use' in new_data:
                success = True
                break
        response.close()
        return ''.join(data) if success else None

    def _response_action(self, response):
        interval = self.REQUEST_INTERVAL
        if response.code != 200:
            interval = self.REQUEST_INTERVAL * 5
            self.do_user_log(u'Сайт недоступен, получен статус, отличный от 200 (%s)' % (response.code,), 'error')
        else:
            data = self.get_data(response)
            if data is None:
                interval = self.REQUEST_INTERVAL * 5
                self.do_user_log(u'Не удалось получить валидный HTML', 'error')
            else:
                self.log_to_db(self.parse_data(data))

        return interval

    def anonymous_parse(self):
        try:
            response = self._get_response()
            interval = self._response_action(response)

        except (urllib2.HTTPError, urllib2.URLError,) as e:
            self.do_user_log(u'Ошибка соединения', 'error')
            self.log.exception(e)
            interval = self.REQUEST_INTERVAL * 5

        return interval

    def parse(self):
        if self.STATE == 'anonymous':
            return self.anonymous_parse()
        return self.auth_parse()

    def auth_parse(self):
        try:
            br = mechanize.Browser()
            br.addheaders = [('User-agent', self.USER_AGENT)]
            br.open(self.BEST_HOST)
            form = reduce(lambda x, y: y if y[1].attrs['id'] == 'login' else x, enumerate(br.forms()), (0, None,))[0]
            br.select_form(nr=form)
            br['ips_username'] = self.USERNAME
            br['ips_password'] = self.PASSWORD
            br['anonymous'] = ['1']
            response = br.submit()

            interval = self._response_action(response)

            br.close()
        except Exception as e:
            self.do_user_log(u'Произошла какая-то хуйня', 'error')
            self.log.exception(e)
            interval = self.REQUEST_INTERVAL * 5

        return interval

    def run(self):
        while True:
            try:
                time.sleep(self.parse())
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.do_user_log(u'Неожиданная ошибка', 'error')
                self.log.exception(e)
                self.log.error(traceback.format_exc(e))
                time.sleep(self.REQUEST_INTERVAL * 5)
