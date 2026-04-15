#!/usr/bin/env python3
"""
cocare.kr NAS 자동 처리 스크립트
- uploads/pending/ 파일 확인 → HTML 업데이트 → git push → ntfy 알림
- admin/delete-requests.txt 확인 → 카드 삭제 → git push → ntfy 알림
- /etc/crontab 에서 */5분마다 실행: python3 /volume1/web/cocare/process.py
"""

import re, subprocess, urllib.request
from pathlib import Path
from datetime import datetime

REPO = Path('/volume1/web/cocare')
PENDING = REPO / 'uploads' / 'pending'
DONE = REPO / 'uploads' / 'done'
DELETE_FILE = REPO / 'admin' / 'delete-requests.txt'
NTFY = 'https://ntfy.sh/gola-claude-alerts'
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
CAT_PAGE = {
    '소식': 'news.html',
    '활동': 'activities.html',
    '자료실': 'resources.html',
    '소개': 'index.html',
}


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)


def notify(title, msg, tags='bell'):
    try:
        req = urllib.request.Request(NTFY, data=msg.encode(), method='POST')
        req.add_header('Title', title)
        req.add_header('Priority', 'high')
        req.add_header('Tags', tags)
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f'ntfy 실패: {e}')


def git_sync(commit_msg):
    sh('git config user.email "bot@cocare.kr"')
    sh('git config user.name "cocare-bot"')
    sh('git add -A')
    r = sh(f'git commit -m "{commit_msg}"')
    if 'nothing to commit' in r.stdout:
        return False
    sh('git pull --rebase')
    push = sh('git push')
    if push.returncode != 0:
        print(f'git push 실패: {push.stderr}')
    return True


def read_memo(f: Path) -> str:
    memo = f.parent / (f.stem + '_메모.txt')
    if not memo.exists():
        return ''
    lines = [
        l.strip() for l in memo.read_text('utf-8').split('\n')
        if l.strip() and not l.startswith(('카테고리:', '파일:'))
    ]
    return '\n'.join(lines)


def make_card(cat, fname, memo, rel_path) -> str:
    ext = Path(fname).suffix.lower()
    name = Path(fname).stem
    today = datetime.now().strftime('%Y.%m.%d')
    display = memo or name

    if ext in IMAGE_EXTS:
        return f'''
      <div class="photo-card">
        <img src="{rel_path}" alt="{display}">
        <div class="photo-info">
          <h4>{display}</h4>
          <p>활동 기록</p>
        </div>
      </div>'''
    elif cat == '소식':
        return f'''
    <div class="news-item">
      <div class="news-meta">
        <span class="news-date">{today}</span>
        <span class="news-tag">{cat}</span>
      </div>
      <div class="news-title">{display}</div>
      <div class="news-body">{cat} 자료가 업로드되었습니다.</div>
    </div>'''
    else:
        return f'''        <div class="resource-card">
          <div class="file-icon">📎</div>
          <div class="file-tag">{cat}</div>
          <div class="file-name">{name}</div>
          <div class="file-meta">{display}</div>
          <a href="{rel_path}" download class="file-download">다운로드</a>
        </div>'''


def insert_card(page: str, card: str):
    p = REPO / page
    html = p.read_text('utf-8')

    anchors = {
        'news.html': '<div class="container">\n\n',
        'activities.html': '<h3>사진 갤러리</h3>\n',
        'resources.html': '<div class="resource-grid">',
    }
    anchor = anchors.get(page, '<div class="container">\n\n')
    idx = html.find(anchor)
    if idx == -1:
        # fallback: insert before </section>
        idx = html.rfind('</section>')
        if idx == -1:
            return
        p.write_text(html[:idx] + card + '\n' + html[idx:], 'utf-8')
        return

    pos = idx + len(anchor)
    p.write_text(html[:pos] + card + '\n' + html[pos:], 'utf-8')


def remove_card(html: str, title: str) -> str:
    """제목을 포함하는 div 카드 전체 제거"""
    classes = ['news-item', 'activity-card', 'resource-card', 'photo-card']
    for cls in classes:
        open_tag = f'<div class="{cls}"'
        start = 0
        while True:
            idx = html.find(open_tag, start)
            if idx == -1:
                break
            depth, pos = 0, idx
            while pos < len(html):
                if html[pos:pos+4] == '<div':
                    depth += 1
                elif html[pos:pos+6] == '</div>':
                    depth -= 1
                    if depth == 0:
                        block = html[idx:pos+6]
                        if title in block:
                            return html[:idx].rstrip() + '\n' + html[pos+7:].lstrip('\n')
                        break
                pos += 1
            start = idx + 1
    return html


def process_pending() -> list:
    if not PENDING.exists():
        return []

    pending_files = []
    for cat_dir in sorted(PENDING.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat = cat_dir.name
        for f in sorted(cat_dir.iterdir()):
            if f.suffix == '.txt' and '_메모' in f.stem:
                continue
            pending_files.append((cat, f))

    if not pending_files:
        return []

    processed = []
    for cat, f in pending_files:
        page = CAT_PAGE.get(cat, 'news.html')
        memo = read_memo(f)
        rel = f'uploads/done/{cat}/{f.name}'

        done_dir = DONE / cat
        done_dir.mkdir(parents=True, exist_ok=True)
        dest = done_dir / f.name
        f.rename(dest)

        memo_f = f.parent / (f.stem + '_메모.txt')
        if memo_f.exists():
            memo_f.rename(done_dir / memo_f.name)

        card = make_card(cat, f.name, memo, rel)
        insert_card(page, card)
        processed.append(f.name)
        print(f'포스팅: {f.name} → {page}')

    if processed:
        names = ', '.join(processed)
        if git_sync(f'자동 포스팅: {names}'):
            notify('cocare 포스팅 완료 ✅', f'포스팅: {names}', 'white_check_mark')

    return processed


def process_deletes() -> list:
    if not DELETE_FILE.exists():
        return []
    content = DELETE_FILE.read_text('utf-8').strip()
    if not content:
        return []

    deleted = []
    for line in content.split('\n'):
        if 'DELETE' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 3:
            continue
        page, title = parts[1], parts[2]
        p = REPO / page
        if not p.exists():
            continue
        html = p.read_text('utf-8')
        new_html = remove_card(html, title)
        if new_html != html:
            p.write_text(new_html, 'utf-8')
            deleted.append(title)
            print(f'삭제: {title} from {page}')

    DELETE_FILE.write_text('', 'utf-8')

    if deleted:
        names = ', '.join(deleted)
        if git_sync(f'자동 삭제: {names}'):
            notify('cocare 삭제 완료 🗑', f'삭제: {names}', 'wastebasket')

    return deleted


if __name__ == '__main__':
    sh('git checkout main')
    sh('git pull --rebase')

    p = process_pending()
    d = process_deletes()

    if not p and not d:
        print(f'[{datetime.now():%Y-%m-%d %H:%M}] 처리할 내용 없음')
