#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Переставляет аналитические блоки report по утверждённому маршруту."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
FILES=[ROOT/'Веб'/'report.html',ROOT/'Веб'/'Части'/'каркас.html']
ORDER=['topbar','hdr','hwrap','savebar top','wnote','logi','card01','card02','card04','card05','card06','card07','thxbar','card09','card10','logi logiw','cta thx','спрдет','trial','foot']
NUMBERS={'card04':'03','card05':'04','card06':'05','card07':'06'}

def key(chunk):
 for ident in ['topbar','card01','card02','card04','card05','card06','card07','card09','card10','спрдет','trial']:
  if re.search(r'id="'+re.escape(ident)+r'"',chunk):return ident
 m=re.match(r'<div\s+class="([^"]+)"',chunk)
 if m:return m.group(1)
 raise ValueError('Не распознан прямой блок: '+chunk[:100])

def split_wp(text):
 start=text.index('<div class="wp">');open_end=text.index('>',start)+1
 token=re.compile(r'<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>|</?div\b[^>]*>',re.S|re.I)
 depth=0;child_start=None;chunks=[];wp_end=None
 for m in token.finditer(text,open_end):
  t=m.group(0).lower()
  if t.startswith('<!--') or t.startswith('<script') or t.startswith('<style'):continue
  if t.startswith('<div'):
   if depth==0:child_start=m.start()
   depth+=1
  else:
   if depth==0:
    wp_end=m.start();break
   depth-=1
   if depth==0:
    chunks.append(text[child_start:m.end()]);child_start=None
 if wp_end is None or len(chunks)!=20:raise ValueError(f'Не разобран .wp: {len(chunks)} блоков')
 return start,open_end,wp_end,chunks

outputs=[]
for path in FILES:
 text=path.read_text(encoding='utf-8');start,open_end,wp_end,chunks=split_wp(text)
 by={key(x):x for x in chunks}
 if set(by)!=set(ORDER):raise SystemExit(f'{path}: состав блоков отличается: {set(by)^set(ORDER)}')
 for ident,no in NUMBERS.items():
  by[ident],n=re.subn(r'(<div class="bn">)\d{2}(</div>)',rf'\g<1>{no}\2',by[ident],count=1)
  if n!=1:raise SystemExit(f'{path}: не найден номер {ident}')
 body='\n'.join(by[x] for x in ORDER)
 result=text[:open_end]+'\n'+body+'\n'+text[wp_end:]
 path.write_text(result,encoding='utf-8');outputs.append(result)
 print(path,'— порядок обновлён')
if outputs[0]!=outputs[1]:raise SystemExit('report и каркас разошлись')
print('Порядок: 01 бюджет → 02 время → 03 сценарии → 04 загрузка → 05 скидка → 06 налоги → благодарность')
