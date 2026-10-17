#!/usr/bin/env python3
"""Build the real component against FixIt and a local, authenticated TMDB mock."""
import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

TOKEN = 'fixture-read-token-DO-NOT-PUBLISH'
KEY = 'fixture-v3-key-DO-NOT-PUBLISH'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1sAAAAASUVORK5CYII=')
requests = []
class Handler(BaseHTTPRequestHandler):
    mode = 'ok'
    def log_message(self, *args): pass
    def do_GET(self):
        parsed = urlparse(self.path)
        requests.append((parsed.path, parse_qs(parsed.query), self.headers.get('Authorization')))
        if self.mode not in ('ok', 'bad-genres'):
            self.send_response(429); self.end_headers(); return
        if parsed.path.startswith('/images/'):
            assert self.headers.get('Authorization') is None, 'Credentials leaked to image host'
            self.send_response(200); self.send_header('Content-Type','image/png'); self.end_headers(); self.wfile.write(PNG); return
        if self.headers.get('Authorization') != 'Bearer ' + TOKEN and parse_qs(parsed.query).get('api_key') != [KEY]:
            self.send_response(401); self.end_headers(); return
        if not re.fullmatch(r'/3/(movie|tv)/[1-9][0-9]*', parsed.path):
            self.send_response(404); self.end_headers(); return
        typ, id = parsed.path.strip('/').split('/')[-2:]
        data = dict(credits=dict(crew=[dict(id=1,name='测试导演',job='Director'),dict(id=2,name='测试编剧',job='Screenplay')],cast=[dict(id=3,name='测试主演')]),aggregate_credits=dict(crew=[dict(id=1,name='测试导演',jobs=[dict(job='Director')]),dict(id=2,name='测试编剧',jobs=[dict(job='Writer'),dict(job='Screenplay')])],cast=[dict(id=3,name='测试主演')]),id=int(id), overview='远程简介（测试数据）', genres=[dict(id=1, name='剧情')], vote_average=8.6, vote_count=123, poster_path='/poster.png')
        if typ == 'movie': data.update(title='远程电影', original_title='Remote Movie', release_date='1999-10-14', runtime=109, release_dates=dict(results=[dict(iso_3166_1='FR',release_dates=[dict(type=3,certification='12',release_date='1999-11-01T00:00:00Z')]),dict(iso_3166_1='US',release_dates=[dict(type=4,certification='PG',release_date='2000-01-01T00:00:00Z'),dict(type=3,certification='R',release_date='2009-10-15T00:00:00Z'),dict(type=3,certification='R',release_date='1999-10-15T00:00:00Z')])]))
        else: data.update(name='远程电视剧', original_name='Remote TV', first_air_date='2008-01-20',episode_run_time=[47],content_ratings=dict(results=[dict(iso_3166_1='US',rating='TV-MA')]))
        if self.mode == 'bad-genres': data.update(credits='invalid',aggregate_credits='invalid',genres='invalid-genre-shape',release_dates='invalid',content_ratings='invalid',episode_run_time='invalid')
        if id == '1561726': data['credits']['cast'][0]['id']=1355967
        if id == '11': data.update(poster_path=None, vote_count=0, vote_average=0)
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(json.dumps(data).encode())

class Cards(HTMLParser):
    def __init__(self): super().__init__(); self.cards=[]; self.depth=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='div' and 'tmdb-card' in attrs.get('class','').split():
            self.cards.append(dict(classes=[],links=[],images=[],text='')); self.depth=1
        elif self.depth:
            assert tag != 'script', 'Executable markup in card'
            if tag=='div': self.depth+=1
            self.cards[-1]['classes'].extend(attrs.get('class','').split())
            if tag=='a': self.cards[-1]['links'].append(attrs)
            if tag=='img': self.cards[-1]['images'].append(attrs)
    def handle_endtag(self, tag):
        if tag=='div' and self.depth: self.depth-=1
    def handle_data(self, value):
        if self.depth: self.cards[-1]['text']+=value

parser=argparse.ArgumentParser(); parser.add_argument('--fixit',type=Path,required=True); args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
assert (args.fixit/'layouts/baseof.html').is_file(), 'Supply a FixIt v1 checkout'
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with tempfile.TemporaryDirectory(prefix='tmdb-verify-') as temporary:
    tmp=Path(temporary); site=tmp/'site'; output=tmp/'public'; cache=tmp/'cache'
    shutil.copytree(root/'exampleSite',site,ignore=shutil.ignore_patterns('themes','public','resources','config','.hugo_build.lock','.tmdb-token','.tmdb-api-key','.tmdb','.env','.env.*','private.toml'))
    cfg=site/'hugo.toml'
    safe_config=re.sub(r'(?ms)^\[params\.tmdb\.api\]\n.*?(?=^\[|\Z)', '', cfg.read_text()).replace('source = "api"','source = "local"').replace('source = "hybrid"','source = "local"')
    cfg.write_text(safe_config)
    shutil.rmtree(site/'data/tmdb')
    shutil.copytree(root/'tests/fixtures/data/tmdb',site/'data/tmdb')
    shutil.copyfile(root/'tests/fixtures/cards.md',site/'content/cards.md')
    (site/'themes').mkdir()
    (site/'themes/FixIt').symlink_to(args.fixit.resolve(),target_is_directory=True)
    (site/'themes/hugo-cmpt-tmdb').symlink_to(root,target_is_directory=True)
    env=os.environ.copy()
    for name in ['HUGO_TMDB_TOKEN','HUGO_TMDB_API_KEY']: env.pop(name,None)
    def build(ok=True, extra=()):
        result=subprocess.run(['hugo','--source',str(site),'--environment','production','--destination',str(output),'--cacheDir',str(cache),'--cleanDestinationDir','--minify',*extra],env=env,text=True,capture_output=True)
        log=result.stdout+result.stderr
        assert TOKEN not in log and KEY not in log, 'Secret in build logs'
        if (result.returncode==0)!=ok: raise AssertionError(log)
        return log
    def read_cards():
        parsed=Cards(); parsed.feed((output/'cards/index.html').read_text()); return parsed.cards
    def check_output():
        for file in output.rglob('*'):
            if file.is_file():
                content=file.read_bytes(); assert TOKEN.encode() not in content and KEY.encode() not in content, 'Secret in output'
        for name in ['index.html', 'index.xml', 'sitemap.xml']:
            assert (output/name).is_file() and (output/name).stat().st_size, name
        html=(output/'cards/index.html').read_text()
        assert html.count('hugo-cmpt-tmdb.min.')==1
        assert 'hugo-cmpt-tmdb.min.' not in (output/'index.html').read_text()
    # Offline example and explicit false switches.
    log=build(); assert 'WARN' not in log,log
    cards=read_cards(); assert len(cards)==4
    assert cards[0]['links'][0]['href']=='https://www.themoviedb.org/movie/550'
    assert cards[1]['links'][0]['href']=='https://www.themoviedb.org/tv/1396'
    assert 'tmdb-card__summary' not in cards[2]['classes']
    assert 'tmdb-card__rating' not in cards[2]['classes']
    assert 'tmdb-card__personal-rating' not in cards[2]['classes']
    assert all('target' not in link for link in cards[2]['links'])
    assert '暂无评分' in cards[3]['text']; check_output()
    assert all('tmdb-card__attribution' in c['classes'] for c in cards)
    for c in cards:
        assert '↗' in c['text'] and '来源：' not in c['text']
        title=next(a for a in c['links'] if a.get('class')=='tmdb-card__title')
        source=next(a for a in c['links'] if a.get('class')=='tmdb-card__attribution')
        assert source['href']==title['href'] and source['aria-label']=='数据来源：TMDB'
        assert source.get('target')==title.get('target') and source.get('rel')==title.get('rel')
    assert (output/'images/hugo-cmpt-tmdb/logo.svg').read_bytes()==(root/'static/images/hugo-cmpt-tmdb/logo.svg').read_bytes()
    credits=(output/'credits/index.html').read_text()
    assert '/images/hugo-cmpt-tmdb/logo.svg' in credits
    assert 'This product uses the TMDB API but is not endorsed or certified by TMDB.' in credits
    # Attribution defaults on and resolves explicit false at all configuration levels.
    saved_config=(site/'hugo.toml').read_text()
    saved_content=(site/'content/cards.md').read_text()
    (site/'hugo.toml').write_text(saved_config.replace('source = "local"','source = "local"\nshow_attribution = false'))
    build();assert all('tmdb-card__attribution' not in c['classes'] for c in read_cards())
    (site/'content/cards.md').write_text(saved_content.replace('draft: false','draft: false\ntmdb:\n  show_attribution: true').replace('id="550" >','id="550" show_attribution=false >',1))
    build();cards=read_cards()
    assert 'tmdb-card__attribution' not in cards[0]['classes']
    assert all('tmdb-card__attribution' in c['classes'] for c in cards[1:])
    (site/'hugo.toml').write_text(saved_config)
    (site/'content/cards.md').write_text(saved_content)
    # Dedicated real-film page: two header rows, full metadata and personal rating.
    real=Cards();real.feed((output/'masterplan/index.html').read_text())
    assert len(real.cards)==1 and '1h 49m' not in real.cards[0]['text']
    assert '我的评分' in real.cards[0]['text'] and '演示评价' not in real.cards[0]['text']
    assert not any('/genre/' in x['href'] for x in real.cards[0]['links'])
    # Remaining API tests intentionally use the stable three-ID fixture.
    (site/'content/masterplan.md').unlink()
    # Local files may live outside Hugo's data directory, with the same field schema.
    cfg=site/'hugo.toml';local_config=cfg.read_text()
    shutil.move(str(site/'data/tmdb'),str(site/'custom-data'))
    cfg.write_text(local_config+'\n[params.tmdb.local]\ndata_dir = "custom-data"\n')
    build(); assert '搏击俱乐部' in read_cards()[0]['text']
    item=site/'custom-data/movie/550.json';item.unlink()
    (item.with_suffix('.yaml')).write_text('title: YAML 电影\ncover: /images/tmdb/fight-club.jpg\n')
    build();assert 'YAML 电影' in read_cards()[0]['text']
    item.with_suffix('.yaml').unlink()
    item.with_suffix('.toml').write_text('title = "TOML 电影"\ncover = "/images/tmdb/fight-club.jpg"\n')
    build();assert 'TOML 电影' in read_cards()[0]['text']
    shutil.rmtree(site/'custom-data');shutil.copytree(root/'tests/fixtures/data/tmdb',site/'data/tmdb')
    cfg.write_text(local_config)
    # Site false < page true < shortcode false.
    config=site/'hugo.toml'; initial=config.read_text()+f'\n[security.http]\nurls = ["^http://127[.]0[.]0[.]1:{server.server_port}/"]\n'
    config.write_text(initial.replace('source = "local"','source = "local"\nshow_summary = false'))
    content=site/'content/cards.md'; original=content.read_text()
    content.write_text(original.replace('draft: false','draft: false\ntmdb:\n  show_summary: true'))
    build(); assert 'tmdb-card__summary' in read_cards()[0]['classes']; assert 'tmdb-card__summary' not in read_cards()[2]['classes']
    content.write_text(original); build(); assert 'tmdb-card__summary' not in read_cards()[0]['classes']
    # Shortcode attributes override local fields, including empty strings and zero.
    content.write_text(original.replace('id="550" >', 'id="550" title="属性标题" rating=0 personal_rating=0 summary="" genres="动作,惊悚" runtime=109 >', 1))
    build(); direct=read_cards()[0]
    assert '属性标题' in direct['text'] and '1h 49m' not in direct['text']
    assert '我的评分 0.0' in direct['text'] and 'tmdb-card__summary' not in direct['classes']
    content.write_text(original)
    # An explicit personal score shows even if the site default hides it; explicit false wins.
    config.write_text(initial.replace('source = "local"','source = "local"\nshow_personal_rating = false'))
    content.write_text(original.replace('id="550" >','id="550" personal_rating=8.5 >',1))
    build();assert '我的评分 8.5' in read_cards()[0]['text']
    content.write_text(original.replace('id="550" >','id="550" personal_rating=8.5 show_personal_rating=false >',1))
    build();assert 'tmdb-card__personal-rating' not in read_cards()[0]['classes']
    config.write_text(initial);content.write_text(original)
    # Real build-time fetch with Bearer auth, duplicate-card deduplication, local overrides.
    shutil.rmtree(site/'data/tmdb'); (site/'data/tmdb/movie').mkdir(parents=True)
    overlay=site/'data/tmdb/movie/550.json'; overlay.write_text(json.dumps(dict(personal_rating=0,summary='<script>alert(1)</script>',review='REMOVED-REVIEW-TEXT')))
    api=f'http://127.0.0.1:{server.server_port}'
    remote_config=initial.replace('source = "local"','source = "api"')+f'\n[params.tmdb.api]\nbase_url = "{api}/3"\nimage_base_url = "{api}/images"\nposter_size = "w342"\ntimeout = "2s"\n'
    # Default hybrid mode prefers usable local records and never reads credentials for them.
    hybrid_config=remote_config.replace('source = "api"\n','')
    hybrid_args=('--cacheDir',str(tmp/'hybrid-cache'))
    hybrid_records=[site/'data/tmdb/movie/550.json',site/'data/tmdb/tv/1396.json',site/'data/tmdb/movie/11.json']
    saved_records={p:p.read_bytes() for p in hybrid_records if p.exists()}
    for p in hybrid_records:
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(dict(title='混合本地条目',cover='/images/tmdb/fight-club.jpg',personal_rating=0)))
    credentials=site/'.tmdb';credentials.write_text('token = "unterminated')
    config.write_text(hybrid_config);before=len(requests);build(extra=hybrid_args)
    assert len(requests)==before and all('混合本地条目' in c['text'] for c in read_cards())
    credentials.unlink()
    config.write_text(hybrid_config+f'token = "{TOKEN}"\n')
    before=len(requests);build(extra=hybrid_args);assert len(requests)==before
    # Missing records and rating-only files use configured API key; existing local records stay offline.
    hybrid_records[0].write_text(json.dumps(dict(personal_rating=0)))
    hybrid_records[2].unlink()
    config.write_text(hybrid_config+f'api_key = "{KEY}"\n')
    before=len(requests);build(extra=hybrid_args)
    api_calls=[(p,q,a) for p,q,a in requests[before:] if p.startswith('/3/')]
    assert sorted(p for p,q,a in api_calls)==['/3/movie/11','/3/movie/550']
    assert all(q.get('api_key')==[KEY] and a is None for p,q,a in api_calls)
    hybrid_cards=read_cards()
    assert '远程电影' in hybrid_cards[0]['text'] and '我的评分 0.0' in hybrid_cards[0]['text']
    assert '混合本地条目' in hybrid_cards[1]['text']
    # Blank local titles are treated as missing, while explicit zero ratings are retained.
    hybrid_records[0].write_text(json.dumps(dict(title='   ',personal_rating=0)))
    before=len(requests);build(extra=hybrid_args)
    assert len(requests)==before and '远程电影' in read_cards()[0]['text']
    assert '我的评分 0.0' in read_cards()[0]['text']
    # Without credentials, missing local data fails without anonymous API requests, even with warm cache.
    config.write_text(hybrid_config);before=len(requests)
    assert 'hybrid source needs a local title or API credentials' in build(False,hybrid_args)
    assert len(requests)==before
    # Hybrid can read the same private credentials file as explicit API mode.
    credentials.write_text(f'token = "{TOKEN}"\n')
    before=len(requests);build(extra=(*hybrid_args,'--ignoreCache'))
    assert all(a=='Bearer '+TOKEN for p,q,a in requests[before:] if p.startswith('/3/'))
    credentials.unlink()
    # Source overrides keep their priority, and explicit title data works without credentials.
    content.write_text('---\ntitle: Hybrid override\n---\n{{< tmdb id="11" source="hybrid" title="纯属性电影" >}}')
    config.write_text(remote_config);before=len(requests);build(extra=hybrid_args)
    assert len(requests)==before and '纯属性电影' in read_cards()[0]['text']
    content.write_text('---\ntitle: Local override\ntmdb:\n  source: local\n---\n{{< tmdb id="11" >}}')
    config.write_text(hybrid_config+f'token = "{TOKEN}"\n');before=len(requests)
    assert 'title is required' in build(False,hybrid_args) and len(requests)==before
    for p in hybrid_records:
        if p in saved_records:p.write_bytes(saved_records[p])
        elif p.exists():p.unlink()
    content.write_text(original)
    # Reject invalid API endpoints before making any authenticated request.
    for bad in [f'{api}/3?invalid=1', f'{api}/3?', f'{api}/3#fragment',
                f'http://user:{TOKEN}@127.0.0.1:{server.server_port}/3',
                f'https://{TOKEN}%zz.invalid/3']:
        before=len(requests)
        config.write_text((remote_config+f'token = "{TOKEN}"\n').replace(f'base_url = "{api}/3"', f'base_url = "{bad}"'))
        assert 'HTTPS base URL' in build(False,('--ignoreCache',))
        assert len(requests)==before, 'Invalid API endpoint received a request with credentials'
    config.write_text(remote_config+f'token = "{TOKEN}"\n')
    before=len(requests); log=build(); assert 'WARN' not in log,log
    cards=read_cards(); assert '远程电影' in cards[0]['text'] and '1999-10-15' in cards[0]['text'], cards[0]['text']
    assert '远程电视剧' in cards[1]['text'] and '2008-01-20' in cards[1]['text']
    assert '8.6' in cards[0]['text'] and '0.0' in cards[0]['text']
    for card in cards[:2]:
        assert '导演：测试导演' in card['text'] and '编剧：测试编剧' in card['text'] and '主演：测试主演' in card['text']
        assert card['text'].count('测试编剧')==1
        assert any(link['href']=='https://www.themoviedb.org/person/3' for link in card['links'])
    assert '1h 49m' not in cards[0]['text'] and '(US)' in cards[0]['text'] and 'tmdb-card__certification' in cards[0]['classes']
    assert 'TV-MA' in cards[1]['text'] and '47m / 集' not in cards[1]['text']
    assert not any('/genre/' in x['href'] for x in cards[0]['links'])
    assert all(q.get('append_to_response')==['release_dates,credits' if '/movie/' in p else 'content_ratings,aggregate_credits'] for p,q,a in requests[before:] if p.startswith('/3/'))
    assert '<script>alert(1)</script>' in cards[0]['text']
    assert 'REMOVED-REVIEW-TEXT' not in cards[0]['text']
    assert len([p for p,q,a in requests[before:] if p.startswith('/3/')])==3,requests
    assert all(q.get('language')==['zh-CN'] for p,q,a in requests[before:] if p.startswith('/3/'))
    for card in cards[:3]:
        for img in card['images']:
            assert img['src'].startswith('/images/tmdb/') and (output/img['src'].lstrip('/')).read_bytes()==PNG
    check_output()
    # Region is selected from cached raw records; language uses a distinct API cache entry.
    before=len(requests)
    config.write_text(remote_config+f'token = "{TOKEN}"\nregion = "FR"\n')
    build(); assert '1999-11-01' in read_cards()[0]['text'] and '(FR)' in read_cards()[0]['text']
    assert len(requests)==before, 'Changing region should reuse complete cached release records'
    config.write_text(remote_config+f'token = "{TOKEN}"\n')
    content.write_text(original.replace('id="550" >', 'id="550" language="en-US" >', 1))
    before=len(requests);build()
    assert len(requests[before:])==1 and requests[before][1].get('language')==['en-US'], 'Language-specific API cache key was not isolated'
    content.write_text(original)
    # Each shortcode can select a source independently of the site setting.
    saved_overlay=overlay.read_text()
    overlay.write_text(json.dumps(dict(title='单卡本地电影',personal_rating=7)))
    content.write_text('---\ntitle: Source override\n---\n{{< tmdb id="550" source="local" >}}')
    before=len(requests);build();assert '单卡本地电影' in read_cards()[0]['text'] and len(requests)==before
    overlay.write_text(json.dumps(dict(personal_rating=7)))
    config.write_text((remote_config+f'token = "{TOKEN}"\n').replace('source = "api"','source = "local"'))
    content.write_text('---\ntitle: Source override\n---\n{{< tmdb id="550" source="api" >}}')
    build();assert '远程电影' in read_cards()[0]['text']
    overlay.write_text(saved_overlay);content.write_text(original);config.write_text(remote_config+f'token = "{TOKEN}"\n')
    # Large numeric IDs must not become scientific notation in comparisons or links.
    large=site/'content/large-id.md';large.write_text('---\ntitle: Large IDs\n---\n{{< tmdb type="movie" id="1561726" >}}')
    build();large_cards=Cards();large_cards.feed((output/'large-id/index.html').read_text())
    assert any(link['href']=='https://www.themoviedb.org/person/1355967' for link in large_cards.cards[0]['links'])
    large.unlink()
    # With API source, attributes still win over local rating and remote metadata.
    content.write_text(original.replace('id="550" >', 'id="550" title="API 属性标题" personal_rating=9 review="IGNORED-REVIEW-ATTRIBUTE" summary="" >', 1))
    build(); direct=read_cards()[0]
    assert 'API 属性标题' in direct['text'] and 'IGNORED-REVIEW-ATTRIBUTE' not in direct['text'] and '我的评分 9.0' in direct['text']
    assert 'tmdb-card__summary' not in direct['classes'] and '1h 49m' not in direct['text']
    content.write_text(original)
    # Persistent cache works with failed service AND no credentials; --ignoreCache forces re-fetch.
    Handler.mode='fail'; before=len(requests); config.write_text(remote_config)
    build(); assert len(requests)==before, 'Cache hit made a network request'; check_output()
    assert 'data unavailable' in build(False,('--ignoreCache',))
    # Failed refresh falls back to explicit local data and a local cover.
    fallback=dict(title='本地回退电影',cover='/images/tmdb/fight-club.jpg',rating=0)
    for typ,id in [('movie','550'),('tv','1396'),('movie','11')]:
        target=site/f'data/tmdb/{typ}/{id}.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(fallback))
    assert 'using local fallback' in build(extra=('--ignoreCache',))
    assert '本地回退电影' in read_cards()[0]['text']
    # v3 API key is supported without exposing credentials to images, output or logs.
    Handler.mode='ok'; config.write_text(remote_config+f'api_key = "{KEY}"\n'); overlay.write_text('{}')
    build(extra=('--ignoreCache',)); assert any(q.get('api_key')==[KEY] for p,q,a in requests); check_output()
    # Token wins when both direct parameters are set; unused key is never sent.
    config.write_text(remote_config+f'token = "{TOKEN}"\napi_key = "{KEY}"\n')
    before=len(requests); build(extra=('--ignoreCache',)); check_output()
    assert all(a=='Bearer '+TOKEN and 'api_key' not in q for p,q,a in requests[before:] if p.startswith('/3/'))
    # One .tmdb TOML file is used only when both Hugo credential parameters are empty.
    credentials=site/'.tmdb';credentials.write_text(f'token = "{TOKEN}"\napi-key = "{KEY}"\n')
    config.write_text(remote_config);before=len(requests);build(extra=('--ignoreCache',));check_output()
    assert all(a=='Bearer '+TOKEN and 'api_key' not in q for p,q,a in requests[before:] if p.startswith('/3/'))
    credentials.write_text(f'token = "invalid-file-token"\napi-key = "{KEY}"\n')
    config.write_text(remote_config+f'api_key = "{KEY}"\n');before=len(requests);build(extra=('--ignoreCache',))
    assert all(q.get('api_key')==[KEY] and a is None for p,q,a in requests[before:] if p.startswith('/3/'))
    credentials.write_text(f'token = ""\napi-key = "{KEY}"\n');config.write_text(remote_config)
    build(extra=('--ignoreCache',));check_output()
    # A configured credentials file is used instead of the default .tmdb.
    custom=site/'private/tmdb.toml';custom.parent.mkdir();credentials.rename(custom)
    config.write_text(remote_config+'credentials_file = "private/tmdb.toml"\n')
    build(extra=('--ignoreCache',));check_output()
    custom.rename(credentials);config.write_text(remote_config)
    credentials.write_text('token = "unterminated')
    assert '.tmdb must be valid TOML' in build(False,('--ignoreCache',))
    config.write_text(remote_config+f'token = "{TOKEN}"\n')
    build(extra=('--ignoreCache',));credentials.unlink()
    # Malformed optional API fields must not crash the template.
    Handler.mode='bad-genres'
    build(extra=('--ignoreCache',)); assert '远程电影' in read_cards()[0]['text']
    Handler.mode='ok'
    # Invalid calls/configuration fail with a useful, sanitized error.
    config.write_text(initial)
    for call,expected in [('{{< tmdb source="invalid" id="550" >}}','source must be'),('{{< tmdb type="book" id="550" >}}','type must be'),('{{< tmdb id="../1" >}}','positive integer'),('{{< tmdb id="550" new_tab="maybe" >}}','must be true or false'),('{{< tmdb id="550" language="../en" >}}','invalid language')]:
        content.write_text('---\ntitle: Invalid\n---\n'+call); assert expected in build(False)
    content.write_text(original)
    overlay.write_text(json.dumps(dict(title='Bad rating',rating=11)))
    assert 'between 0 and 10' in build(False)
    overlay.write_text(json.dumps(dict(title='Non-finite rating',rating='NaN')))
    assert 'between 0 and 10' in build(False)
    overlay.write_text(json.dumps(dict(title='Non-finite personal rating',personal_rating='NaN')))
    assert 'between 0 and 10' in build(False)
    overlay.write_text(json.dumps(dict(title='Bad cover',cover='javascript:alert(1)')))
    assert 'HTTPS base URL' in build(False)
    print('PASS: FixIt production build, movie/TV API, Bearer/key parameters, API configuration, default hybrid/local/API source selection, local posters, persistent cache, fallback, overrides, validation, escaping and secret-free output')
finally:
 server.shutdown();server.server_close()
