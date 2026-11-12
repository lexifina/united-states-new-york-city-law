"""Append checked corpus.d batches without rewriting the scratch history."""
import os
import sys
import json
import hashlib
import subprocess
import datetime as dt
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1]
COMMON = FOLDER.parent/'gitlaw_common'
sys.path.insert(0, str(COMMON))
import build as B

def git(repo, *args):
    p=subprocess.run(['git','-c','gc.auto=0','-C',str(repo),*args],capture_output=True,encoding='utf-8')
    if p.returncode: raise RuntimeError(p.stderr)
    return p.stdout.strip()

def append(repo, part_path, branch='main'):
    corpus,raw=B.load(FOLDER)
    errors=B.validate(corpus)
    if errors: raise RuntimeError('\n'.join(errors))
    part=json.loads(part_path.read_text(encoding='utf-8'))
    if branch not in ('main','future'):raise RuntimeError('unsupported branch')
    present=subprocess.run(['git','-C',str(repo),'rev-parse','--verify',branch],capture_output=True).returncode==0
    base=branch if present else ('main' if branch=='future' else None)
    if base and subprocess.run(['git','-C',str(repo),'rev-parse','--verify',base],capture_output=True).returncode:
        base=None
    existing=set(git(repo,'ls-tree','--name-only',base).splitlines()) if base else set()
    acts=[a for a in part['acts'] if a['slug'] not in existing]
    if not acts: return git(repo,'rev-parse',branch)
    head=git(repo,'rev-parse',base) if base else None
    count=int(git(repo,'rev-list','--count',base)) if base else 0
    clock=B.Clock(corpus['country']['tz'])
    payload=bytearray()
    def write(s):payload.extend(s.encode('utf-8'))
    def data(s):
        b=s.encode('utf-8');write(f'data {len(b)}\n');payload.extend(b);write('\n')
    for mark,a in enumerate(sorted(acts,key=lambda a:(a['versions'][0]['from'],a['slug'])),1):
        v=a['versions'][0];day=v['from']
        if day>'2026-11-12' and branch!='future':raise RuntimeError('future act must be held separately')
        if day<='2026-11-12' and branch=='future':raise RuntimeError('current act belongs on main')
        key=a.get('first_law');law=corpus['laws'].get(key,{})
        author=law.get('label') or (a.get('publisher') or corpus['country']['publisher'])['name']
        email=(key+'@nyc-law.invalid') if key else 'publisher@nyc-law.invalid'
        kind='law' if key else 'baseline'
        trailers=[f'Kind: {kind}']
        if key:trailers.extend([f'Law-kind: {a.get("law_kind","regulation")}',f'Law: {law["label"]}'])
        trailers.extend([f'In-force: {day}',f'In-force-basis: {v["in_force_basis"]}',
            f'Source: {a["url"]}',f'Text-source: {v["source_url"]}',f'Act: {a["short"]}',
            f'Provisions: {len(v["units"])}'])
        if law.get('enacted'):trailers.append(f'Enacted: {law["enacted"]}')
        if v.get('text_as_of'):trailers.append(f'Text-as-of: {v["text_as_of"]}')
        message=f'{a["short"]}: '+('as adopted' if key else 'labelled historical snapshot')+'\n\n'+v.get('note','')+'\n\n'+'\n'.join(trailers)+'\n'
        B.check_trailers(trailers)
        write(f'commit refs/heads/{branch}\nmark :{mark}\n')
        write(f'author {author} <{email}> {clock.stamp(day)}\n')
        commit_time=int(dt.datetime(2026,11,12,tzinfo=dt.timezone.utc).timestamp())+count+mark
        write(f'committer Lexifina <united-states-new-york-city-law@lexifina.com> {commit_time} +0000\n')
        data(message)
        if mark==1 and head:write(f'from {head}\n')
        elif mark>1:write(f'from :{mark-1}\n')
        for k,u in sorted(v['units'].items()):
            write(f'M 100644 inline {a["slug"]}/{k}.md\n');data(u['text'])
        write('\n')
        write(f'reset refs/tags/{a["slug"]}/{day}\nfrom :{mark}\n\n')
    write('done\n')
    p=subprocess.run(['git','-c','gc.auto=0','fast-import','--quiet','--done','--date-format=raw'],
        cwd=repo,input=bytes(payload),capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8','replace'))
    # Verify the stored blobs against the checked source-derived input before marking a batch pending review.
    requests=[];expected=[]
    for a in acts:
        for key,u in sorted(a['versions'][0]['units'].items()):
            requests.append(f'{branch}:{a["slug"]}/{key}.md')
            expected.append(u['text'].encode('utf-8'))
    p=subprocess.run(['git','-C',str(repo),'cat-file','--batch'],input=('\n'.join(requests)+'\n').encode(),capture_output=True)
    if p.returncode:raise RuntimeError('stored-blob check failed')
    offset=0
    for name,want in zip(requests,expected):
        newline=p.stdout.index(b'\n',offset);header=p.stdout[offset:newline].split()
        if len(header)!=3 or header[1]!=b'blob':raise RuntimeError('missing stored file '+name)
        size=int(header[2]);offset=newline+1;got=p.stdout[offset:offset+size];offset+=size+1
        if got!=want:raise RuntimeError('stored text differs from checked source input '+name)
    return git(repo,'rev-parse',branch)
