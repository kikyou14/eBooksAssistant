#!/usr/bin/env python
# -*- coding:utf-8 -*-
from bottle import *
import psycopg2
import pylibmc
import simplejson as json
import requests
import urllib.parse


app = Bottle()
mc = pylibmc.Client(['localhost:11211'])


def queryDB():
    conn = psycopg2.connect(dbname="turing", user="user",
                            host="localhost", password="password")
    cur = conn.cursor()
    cur.execute("SELECT isbn, price, url FROM Ebooks WHERE forsale = 1;")
    records = cur.fetchall()
    conn.commit()
    conn.close()
    return records


def loadData():
    records = queryDB()
    for item in records:
        isbn = item[0]
        price = item[1]
        url = item[2]
        book = {
            'isbn': isbn,
            'price': str(price),
            'url': url
        }
        mc.set(isbn, book)
    print('done.')
    return


@app.route('/turing')
def turing():
    isbn = str(request.query.isbn) or ''
    if not isbn:
        book = {}
        errmsg = 'isbn not given.'
    else:
        try:
            book = mc.get(isbn)
            errmsg = ''
        except:
            book = {}
            errmsg = 'record not found.'
    result = {
        'data': book,
        'errmsg': errmsg
    }
    resp = json.dumps(result)
    response.set_header('Content-Type', 'application/json; charset=UTF-8')
    response.add_header('Cache-Control', 'no-cache; must-revalidate')
    response.add_header('Expires', '-1')
    return resp


@app.route('/ximalaya')
def ximalaya():
    response.set_header('Content-Type', 'application/json; charset=UTF-8')
    response.add_header('Cache-Control', 'no-cache; must-revalidate')
    response.add_header('Expires', '-1')

    try:
        title = str(request.query.title) or ''
        author = str(request.query.author) or ''
        if not all([title, author]):
            result = {
                'data': {},
                'errmsg': 'title or author not given.'
            }
            resp = json.dumps(result)
            return resp

        title = urllib.parse.quote_plus(title)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.ximalaya.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }
        sess = requests.Session()
        sess.headers.update(headers)
        url = 'https://www.ximalaya.com/revision/search/main'
        params = {
            'core': 'album',
            'kw': '%s' % (title),
            'page': '1',
            'spellchecker': 'true',
            'rows': '20',
            'condition': 'play',
            'device': 'iPhone',
            'fq': 'category_id:3,is_paid:true',
            'paidFilter': 'true'
        }
        resp = sess.get(url, params=params, timeout=100)
        content = resp.json()
        total = int(content['data']['album']['total'])

        if total == 0:
            result = {
                'data': {},
                'errmsg': 'album not found.'
            }
            resp = json.dumps(result)
            return resp

        matchWords = re.sub(r'•|·|▪|\.|\-|\[|\]| |\/|\||\(|\)|（|）|<|>|【|】|\?|？', '\t', author).split('\t')
        matchWords.sort(key=len, reverse=True)
        for doc in content['data']['album']['docs']:
            album_url = doc['url']
            album_url = 'https://www.ximalaya.com' + album_url
            title = doc['title']
            nickname = doc['nickname']
            album = {
                'url': album_url,
                'title': title,
                'nickname': nickname
            }
            errmsg = ''
            intro = doc['intro']
            loopFlag = True
            for wd in matchWords:
                if len(wd) > 1 and (wd in intro):
                    loopFlag = False
            if not loopFlag:
                break
    except:
        album = {}
        errmsg = 'unknow error.'

    result = {
        'data': album,
        'errmsg': errmsg
    }
    resp = json.dumps(result)
    return resp


@app.route('/amazon')
def amazon():
    pass

if __name__ == '__main__':
    loadData()
    run(app, server='paste', host='localhost',
        port=8081, debug=True, reloader=True)
