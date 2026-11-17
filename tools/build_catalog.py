#!/usr/bin/env python3
"""Build self-contained static Mini App from UTF-8 semicolon CSV; stdlib only."""
from __future__ import annotations
import csv, json, argparse, pathlib
ROOT = pathlib.Path(__file__).parent
FIELDS = {
    'SKU':'id', 'Год прайса':'year', 'Категория':'category', 'Тип':'subcategory',
    'Модель':'model', 'Группа':'age', 'Размер':'size', 'Посадка':'fit',
    'Цвет':'color', 'Флекс/высота':'flex', 'Загиб':'pattern', 'Хват':'hand',
    'Остаток':'qty', 'Цена RUB':'price',
}

def transform(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f,delimiter=';')
        absent=set(FIELDS)-set(reader.fieldnames or [])
        if absent: raise ValueError('Отсутствуют столбцы: '+', '.join(sorted(absent)))
        results=[]; seen=set()
        for n,row in enumerate(reader,2):
            x={key: (row.get(orig) or '').strip() for orig,key in FIELDS.items()}
            if not x['id'] or x['id'] in seen: raise ValueError('Дублируется или отсутствует SKU, строка '+str(n))
            seen.add(x['id'])
            x['year']=int(x['year']); x['qty']=int(x['qty']);
            if x['qty']<=0: continue
            x['price']=int(float(x['price'].replace(' ', '').replace(',','.'))) if x['price'] else None
            results.append(x)
    return results

def make(csv_path: pathlib.Path,date: str):
    if len(date)!=10 or date[4]!='-' or date[7]!='-': raise ValueError('Дата должна быть YYYY-MM-DD')
    values=transform(csv_path)
    tpl=(ROOT/'template.html').read_text(encoding='utf-8')
    payload=json.dumps({'updated':date,'rows':values},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    assert '__CATALOG_JSON__' in tpl
    html=tpl.replace('__CATALOG_JSON__',payload)
    (ROOT.parent/'docs'/'index.html').write_text(html,encoding='utf-8')
    print(f'Готово: {len(values)} вариантов, {len({(v["category"],v["subcategory"],v["model"],v["year"]) for v in values})} карточек, {(ROOT.parent/"docs"/"index.html").stat().st_size//1024} KiB')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('csv',type=pathlib.Path,help='CSV из подготовленной русской таблицы')
    p.add_argument('--date',required=True,help='Дата получения прайса YYYY-MM-DD')
    a=p.parse_args();make(a.csv,a.date)
