(function () {
  const params = new URLSearchParams(window.location.search);
  if (!params.has('admin')) return;

  const token = localStorage.getItem('gh_pat');
  if (!token) {
    alert('GitHub 토큰이 없습니다.\n포스팅 페이지(cocare.kr/posting.html)에서 먼저 로그인해주세요.');
    return;
  }

  const REPO = 'daekeun-lab/cocare-site';
  const REQUEST_FILE = 'admin/delete-requests.txt';

  // 관리자 모드 표시
  const badge = document.createElement('div');
  badge.style.cssText = 'position:fixed;top:16px;right:16px;background:#e74c3c;color:white;padding:6px 16px;border-radius:20px;font-size:0.8rem;font-weight:700;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.2);';
  badge.textContent = '🔐 관리자 모드';
  document.body.appendChild(badge);

  async function writeDeleteRequest(page, title, description) {
    const timestamp = new Date().toISOString().slice(0, 16).replace('T', ' ');
    const line = `[${timestamp}] DELETE | ${page} | ${title} | ${description}\n`;

    try {
      // 기존 파일 내용 가져오기
      const getResp = await fetch(`https://api.github.com/repos/${REPO}/contents/${REQUEST_FILE}`, {
        headers: { Authorization: `token ${token}` }
      });

      let sha = null;
      let currentContent = '';
      if (getResp.ok) {
        const data = await getResp.json();
        sha = data.sha;
        currentContent = decodeURIComponent(escape(atob(data.content.replace(/\n/g, ''))));
      }

      const newContent = currentContent + line;
      const body = {
        message: `삭제 요청: ${title}`,
        content: btoa(unescape(encodeURIComponent(newContent)))
      };
      if (sha) body.sha = sha;

      const putResp = await fetch(`https://api.github.com/repos/${REPO}/contents/${REQUEST_FILE}`, {
        method: 'PUT',
        headers: { Authorization: `token ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      return putResp.ok;
    } catch {
      return false;
    }
  }

  function addDeleteButton(card, titleEl, metaEl) {
    const btn = document.createElement('button');
    btn.textContent = '🗑 삭제 요청';
    btn.style.cssText = 'display:block;margin-top:12px;padding:6px 16px;background:#e74c3c;color:white;border:none;border-radius:8px;cursor:pointer;font-size:0.82rem;font-weight:700;';

    btn.onclick = async () => {
      const title = titleEl?.textContent?.trim() || '(제목 없음)';
      const meta = metaEl?.textContent?.trim() || '';
      const page = window.location.pathname.split('/').pop() || 'index.html';

      if (!confirm(`"${title}" 를 삭제 요청하시겠어요?\n(최대 1시간 내 반영됩니다)`)) return;

      btn.disabled = true;
      btn.textContent = '요청 중...';

      const ok = await writeDeleteRequest(page, title, meta);
      if (ok) {
        btn.textContent = '✅ 요청 완료';
        btn.style.background = '#27ae60';
        card.style.opacity = '0.4';
        card.style.pointerEvents = 'none';
      } else {
        btn.disabled = false;
        btn.textContent = '🗑 삭제 요청';
        alert('요청 실패. 다시 시도해주세요.');
      }
    };

    card.appendChild(btn);
  }

  // 페이지별 카드 감지
  document.querySelectorAll('.news-item').forEach(card => {
    addDeleteButton(card, card.querySelector('.news-title'), card.querySelector('.news-date'));
  });

  document.querySelectorAll('.activity-card').forEach(card => {
    addDeleteButton(card, card.querySelector('.activity-content h4'), card.querySelector('.activity-date'));
  });

  document.querySelectorAll('.resource-card').forEach(card => {
    addDeleteButton(card, card.querySelector('.file-name'), card.querySelector('.file-meta'));
  });
})();
