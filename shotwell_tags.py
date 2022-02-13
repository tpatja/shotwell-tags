#!/usr/bin/env python

import sqlite3
import os
import sys
import argparse
from datetime import datetime

HOME = os.getenv('HOME')

DB_FILE = f'{HOME}/.local/share/shotwell/data/photo.db'


def photo_id_str_from_photo_id(photo_id: int):
    return f"thumb{photo_id:0{16}x}"


def photo_id_from_photo_id_str(photo_id_str: str):
    return int(photo_id_str[5:], base=16)


def get_photo_tags(filename):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    row = cur.execute(
        f'''select id
        from PhotoTable
        where filename like '%{filename}' '''
    ).fetchone()
    if not row:
        print(f'photo {filename} not found in DB')
        return
    photo_id_str = photo_id_str_from_photo_id(row[0])
    rows = cur.execute(
        f'''select name 
        from TagTable
        where photo_id_list like '%{photo_id_str}%' '''
    ).fetchall()
    return [row[0] for row in rows]


def get_all_tags():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    rows = cur.execute(
        f'''select name, photo_id_list
        from TagTable'''
    ).fetchall()
    return [f'{row[0]} {len(row[1].split(",")) - 1 if row[1] else 0}' for row in rows]


def get_photos_by_tagname(tag_name):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    row = cur.execute(
        f'''select photo_id_list 
        from TagTable
        where name='{tag_name}' '''
    ).fetchone()
    if not row:
        print(f'tag {tag_name} not found')
        return
    photo_id_strs = [x for x in row[0].split(',') if len(x.strip()) > 0]
    ret = []
    for photo_id_str in photo_id_strs:
        row = cur.execute(
            f'''select filename 
            from PhotoTable
            where id='{photo_id_from_photo_id_str(photo_id_str)}' '''
        ).fetchone()
        ret.append(row[0])
    return ret


def _tag_photo(row, photo_id_str, tag_name, cur):
    if not row:
        print('inserting tag')
        ts = int(datetime.utcnow().timestamp())

        cur.execute(
            f'''insert into TagTable (name, photo_id_list, time_created)
            values 
            ('{tag_name}', '{photo_id_str}' || ',', {ts})
            '''
        )
        return
    tag_id = row[0]
    existing_photo_id_strs = row[1]
    if not photo_id_str in existing_photo_id_strs.split(','):
        photo_id_strs = f'{existing_photo_id_strs},{photo_id_str},'
        cur.execute(
            f'''update TagTable 
            set photo_id_list='{photo_id_strs}'
            where id={tag_id}'''
        )
    else:
        print(f'Tag already exists')


def _untag_photo(row, photo_id_str, tag_name, cur):
    if not row:
        print(f'tag {tag_name} does not exist')
        return

    tag_id = row[0]
    existing_photo_id_strs = [x for x in row[1].split(',') if len(x.strip()) > 0]
    if photo_id_str in existing_photo_id_strs:
        photo_id_strs = ','.join(
            [x for x in existing_photo_id_strs if x != photo_id_str]
        )
        cur.execute(
            f'''update TagTable 
            set photo_id_list='{photo_id_strs},'
            where id={tag_id}'''
        )
    else:
        print(f'photo not tagged with {tag_name}')


def tag_photo(filename, tag_name, untag=False):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    # assert photo filename exists in PhotoTable, get photo_id
    row = cur.execute(
        f'''select id
        from PhotoTable
        where filename like '%{filename}' '''
    ).fetchone()
    if not row:
        print(f'photo {filename} not found in DB')
        return
    photo_id = row[0]
    photo_id_str = photo_id_str_from_photo_id(photo_id)
    row = cur.execute(
        f'''select id, photo_id_list 
        from TagTable
        where name='{tag_name}'
        '''
    ).fetchone()

    if untag:
        _untag_photo(row, photo_id_str, tag_name, cur)
    else:
        _tag_photo(row, photo_id_str, tag_name, cur)
    con.commit()


def untag_photo(filename, tag_name):
    return tag_photo(filename, tag_name, untag=True)


def rm_tag(tag_name):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(
        f'''delete from TagTable 
            where name='{tag_name}'
            '''
    )
    con.commit()


if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        print(f'shotwell database not found at {DB_FILE}')
        sys.exit(1)
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['tags', 'tag', 'untag', 'rmtag', 'photos'])
    ap.add_argument('-f', '--file-name', type=str)
    ap.add_argument('-t', '--tag-name', type=str)
    args = vars(ap.parse_args())

    action = args['action']
    file_name = args['file_name']
    tag_name = args['tag_name']
    if action in ('tag', 'untag') and (not tag_name or not file_name):
        ap.print_usage()
        sys.exit(1)
    elif action == 'photos' and (not tag_name or file_name):
        ap.print_usage()
        sys.exit(1)
    elif action == 'rmtag' and (not tag_name or file_name):
        ap.print_usage()
        sys.exit(1)

    if action == 'tags':
        if file_name:
            print(' '.join(get_photo_tags(filename=file_name)))
        else:
            print('\n'.join(get_all_tags()))
    elif action == 'tag':
        tag_photo(filename=file_name, tag_name=tag_name)
    elif action == 'untag':
        untag_photo(filename=file_name, tag_name=tag_name)
    elif action == 'photos':
        print('\n'.join(get_photos_by_tagname(tag_name)))
    elif action == 'rmtag':
        rm_tag(tag_name)
