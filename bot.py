#!/usr/bin/env python3
"""Minimal BAUER Telegram bot: long polling, web_app keyboard, owner notifications.
Python standard library only. Environment: BOT_TOKEN, ADMIN_CHAT_ID, MINIAPP_URL.
"""
from __future__ import annotations
import html, json, os, sys, time, urllib.request, urllib.parse, urllib.error

TOKEN = os.environ.get('BOT_TOKEN','').strip()
ADMIN_CHAT_ID=os.environ.get('ADMIN_CHAT_ID','').strip()
MINIAPP_URL=os.environ.get('MINIAPP_URL','').strip()
if not TOKEN or not MINIAPP_URL.startswith('https://'):
    sys.exit('Укажите BOT_TOKEN и MINIAPP_URL (https://...)')
API=f'https://api.telegram.org/bot{TOKEN}/'

def api(method, values):
    raw=urllib.parse.urlencode({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else str(v) for k,v in values.items()}).encode()
    with urllib.request.urlopen(urllib.request.Request(API+method,data=raw),timeout=60) as f:
        response=json.load(f)
    if not response.get('ok'):
        raise RuntimeError('Telegram API '+method+' '+str(response.get('description')))
    return response['result']

def send(chat,text,**kwargs):
    return api('sendMessage',{'chat_id':chat,'text':text,**kwargs})

def safe(s):return html.escape(str(s or ''))

def start(msg):
    keyboard={'keyboard':[[{'text':'🏒 Открыть каталог BAUER','web_app':{'url':MINIAPP_URL}}]],'resize_keyboard':True,'is_persistent':True,'input_field_placeholder':'Откройте каталог и выберите экипировку'}
    text='Привет! Здесь можно выбрать хоккейную экипировку BAUER по последнему складскому списку. Цены и остатки ориентировочные — каждую позицию подтвердим у менеджера после вашего запроса.\n\nНажмите кнопку «🏒 Открыть каталог BAUER» под полем ввода.\n\nКоманда /myid покажет ваш Telegram ID для настройки уведомлений.'
    send(msg['chat']['id'],text,reply_markup=keyboard)

def fmt_variant(x):
    names={'age':'Группа','size':'Размер','fit':'Посадка','color':'Цвет','flex':'FLEX/высота','pattern':'Загиб','hand':'Хват'}
    return ', '.join(f'{kname}: {safe(x.get(k))}' for k,kname in names.items() if x.get(k)) or 'вариант не указан'

def on_request(msg):
    user=msg.get('from') or {};chat=msg.get('chat') or {}
    if not ADMIN_CHAT_ID or ADMIN_CHAT_ID == '0':
        send(chat['id'], 'Приём заявок пока настраивается. Попробуйте позже или отправьте текст запроса владельцу каталога.')
        return
    try:
        raw=msg['web_app_data']['data']
        if len(raw.encode('utf-8'))>4096:raise ValueError('слишком большой запрос')
        payload=json.loads(raw)
        if payload.get('kind')!='bauer_request':raise ValueError('неверный тип запроса')
        items=payload.get('items')
        if not isinstance(items,list) or not (1<=len(items)<=40):raise ValueError('пустой или слишком большой запрос')
        lines=[]
        for i,x in enumerate(items,1):
            if not isinstance(x,dict) or not x.get('id') or not x.get('model'):raise ValueError('некорректная позиция')
            if len(str(x['id']))>100 or len(str(x['model']))>200:raise ValueError('некорректная позиция')
            price=x.get('price');price=safe(f'{int(price):,}'.replace(',',' ')+' ₽') if isinstance(price,(int,float)) and not isinstance(price,bool) and price>=0 else 'цену уточнить'
            lines.append(f'{i}. <b>{safe(x["model"])}</b>\n{safe(x.get("category"))}\n{fmt_variant(x)}\n{price}\nSKU: <code>{safe(x["id"])}</code>')
        label=' '.join(str(user.get(k) or '') for k in ('first_name','last_name')).strip() or 'Покупатель'
        ulink=f'<a href="tg://user?id={int(user["id"])}">{safe(label)}</a>' if user.get('id') else safe(label)
        username=' @'+safe(user['username']) if user.get('username') else ''
        header=f'🆕 <b>Запрос на проверку наличия BAUER</b>\nОт: {ulink}{username}\nID: <code>{safe(chat.get("id"))}</code>\nОстатки из прайса: {safe(payload.get("updated"))}\n\n'
        text=header+'\n\n'.join(lines)+'\n\n⚠️ Это запрос, наличие и цены у поставщика ещё не подтверждены.'
        if len(text)>3900:
            raise ValueError('слишком длинный запрос — выберите меньше товаров')
        # Do not tell customer success unless message reached owner.
        send(ADMIN_CHAT_ID,text,parse_mode='HTML',disable_web_page_preview=True)
        send(chat['id'],'✅ Запрос получен! Проверю позиции у менеджера склада и напишу вам с подтверждением наличия и цены.')
    except Exception as exc:
        print('Request failed:',repr(exc),file=sys.stderr)
        send(chat['id'],'Не удалось передать запрос. Попробуйте выбрать меньше позиций или напишите мне сообщением.')

def main():
    print('Бот BAUER запущен. Ctrl+C для остановки.',flush=True)
    offset=None
    while True:
        try:
            updates=api('getUpdates',{'timeout':40,'offset':offset or 0,'allowed_updates':['message']})
            for up in updates:
                offset=up['update_id']+1
                msg=up.get('message') or {}
                if msg.get('web_app_data'):on_request(msg)
                else:
                    command=str(msg.get('text','')).split()[0].split('@')[0].lower() if msg.get('text') else ''
                    if command in ('/start','/catalog','/каталог'):start(msg)
                    elif command in ('/myid','/id'):
                        send(msg['chat']['id'],f'Ваш Telegram chat ID: {msg["chat"]["id"]}\nСкопируйте только цифры в ADMIN_CHAT_ID на Railway.')
                    elif command=='/help':
                        send(msg['chat']['id'],'Напишите /start, чтобы открыть каталог BAUER. /myid — узнать свой Telegram ID. Наличие и цену подтверждаем после проверки у поставщика.')
        except KeyboardInterrupt:
            print('Остановлен');return
        except Exception as exc:
            print('Telegram error',repr(exc),file=sys.stderr);time.sleep(5)
if __name__=='__main__':main()
