#!/usr/bin/env python3
"""Own Telegram stories -> private archive -> explicit review -> Hugo drafts."""
import argparse
import asyncio
from getpass import getpass
import json
import os
from pathlib import Path
import sys
from stories.content import ROOT
from stories.exporter import export_archive,atomic_json,read_json
from stories.importer import import_selection
from stories.review import create_review

PRIVATE=ROOT.parent/'.brodov-private'/'telegram'

def external(path):
    path=Path(path).expanduser().resolve()
    if path.is_relative_to(ROOT.resolve()):raise ValueError('Сырой архив и сессия должны быть вне репозитория')
    return path

async def export(args):
    from telethon import TelegramClient
    from stories.telegram import TelegramGateway
    private=external(args.private);out=external(args.out)
    private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700)
    config=read_json(private/'app.json')
    if not config:
        print('Создайте собственное приложение на https://my.telegram.org → API development tools.')
        config={'api_id':int(input('API ID: ')), 'api_hash':getpass('API hash (скрытый ввод): ')}
        if not config['api_hash']:raise ValueError('Пустой API hash')
        atomic_json(private/'app.json',config)
    client=TelegramClient(str(private/'account'),config['api_id'],config['api_hash'],flood_sleep_threshold=0)
    try:
        await client.start(phone=lambda:input('Ваш номер телефона (локально): '),code_callback=lambda:getpass('Код Telegram (скрытый ввод): '),password=lambda:getpass('Пароль 2FA (скрытый ввод): '))
        me=await client.get_me()
        print('Аккаунт:',me.first_name or '', '@'+me.username if me.username else '')
        owner=read_json(private/'owner.json')
        if owner and owner['id']!=me.id:raise ValueError('Сессия другого владельца')
        if not owner:
            if input('Это ваш аккаунт для экспорта собственных Stories? [да/нет]: ').strip().lower() not in ('да','yes'):return
            atomic_json(private/'owner.json',{'id':me.id})
        manifest=await export_archive(TelegramGateway(client),out,me.id,None if args.all else args.limit)
        print('Источники:',json.dumps(manifest['sources'],ensure_ascii=False))
        print('Полных файлов:',sum(e['status']=='complete' for e in manifest['stories'].values()))
        print('Локальная сетка:',create_review(out))
    finally:
        await client.disconnect()
        for path in private.glob('account.session*'):os.chmod(path,0o600)

def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('export');p.add_argument('--out',type=Path,default=PRIVATE/'archive');p.add_argument('--private',type=Path,default=PRIVATE);g=p.add_mutually_exclusive_group();g.add_argument('--limit',type=int,default=3);g.add_argument('--all',action='store_true')
    p=sub.add_parser('desktop');p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,default=PRIVATE/'desktop-archive')
    p=sub.add_parser('review');p.add_argument('--input',type=Path,default=PRIVATE/'archive')
    p=sub.add_parser('import');p.add_argument('--input',type=Path,default=PRIVATE/'archive');p.add_argument('--selection',type=Path,required=True);p.add_argument('--drafts',action='store_true',required=True)
    args=parser.parse_args()
    if args.command=='export':
        if args.limit<1:parser.error('--limit должен быть положительным')
        asyncio.run(export(args))
    elif args.command=='desktop':
        from stories.desktop import ingest_desktop
        out=external(args.out)
        manifest=ingest_desktop(external(args.input),out)
        print(json.dumps(manifest['sources']['desktop'],ensure_ascii=False,indent=2))
        print('Локальная сетка:',create_review(out))
    elif args.command=='review':print(create_review(external(args.input)))
    else:print(json.dumps(import_selection(external(args.input),args.selection),ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nОстановлено. Прогресс сохранён; повторите команду для продолжения.');sys.exit(130)
    except Exception as e:
        # Do not leak credentials, phone or API payloads through a traceback.
        print(f'Операция не завершена: {type(e).__name__}. Проверьте входные файлы и доступность сети.',file=sys.stderr);sys.exit(1)
