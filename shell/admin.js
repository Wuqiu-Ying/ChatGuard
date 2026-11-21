/* ChatGuard 校园端（B 端）
 * 数据来自 /api/b/events 与 /api/b/weekly。
 * 按设计：这里**没有聊天原文**，只有结构化事件。
 */
(() => {
  'use strict';

  const LV = {
    critical: { c: '#D93025', t: '极高' },
    high:     { c: '#E8710A', t: '高'   },
    medium:   { c: '#B8860B', t: '中'   },
    low:      { c: '#1E8E3E', t: '低'   },
    none:     { c: '#5F6368', t: '无'   }
  };
  const ST = { pending: '待处理', contacted: '已联系', closed: '已关闭' };
  const VS = {
    none: '尚未损失', money_lost: '已损失资金', info_leaked: '已泄露信息',
    media_held: '影像被持有', acted: '已按指示行动', in_danger: '有人身危险'
  };

  const $ = s => document.querySelector(s);
  const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  let cur = null;
  let useSample = true;          // 默认演示数据
  let lastEvents = [];
  const SRC = () => (useSample ? "" : "?source=live");

  async function boot() {
    const [ev, wk] = await Promise.all([
      fetch('/api/b/events' + SRC()).then(r => r.json()).catch(() => null),
      fetch('/api/b/weekly' + SRC()).then(r => r.json()).catch(() => null)
    ]);

    if (!ev || !ev.ok) { $('#school').textContent = '无法连接后端'; return; }
    if (!ev.events || !ev.events.length) {
      $('#school').textContent = ev.school || '某大学 · 学生工作处';
      const box0 = $('#list');
      if (box0) box0.innerHTML = '<div style="padding:18px;color:#8A90A0;font-size:13px">还没有真实记录。到「学生端」分析几段对话，这里就会出现告警。</div>';
      const st = $('#stats'); if (st) st.innerHTML = '';
      // 详情与周报一并清空，避免残留上一次（演示数据）的内容
      const dt = $('#detail');
      if (dt) dt.innerHTML = '<div style="padding:24px;color:#8A90A0;font-size:13px">暂无告警详情。</div>';
      const wkBox = document.getElementById('weekly');
      if (wkBox) wkBox.innerHTML = '<div style="padding:18px;color:#8A90A0;font-size:13px">还没有真实记录，暂无周报。</div>';
      return;
    }
    $('#school').textContent = ev.school;
    renderStats(ev.stats);
    renderList(ev.events);
    if (ev.events.length) select(ev.events[0]);
    if (wk && wk.ok) renderWeekly(wk.weekly);
  }

  function renderStats(s) {
    const box = $('#stats'); box.innerHTML = '';
    const put = (k, v, d) => {
      const c = el('div', 'stat');
      c.appendChild(el('div', 'k', k));
      c.appendChild(el('div', 'v', String(v)));
      if (d) c.appendChild(el('div', 'd', d));
      box.appendChild(c);
    };
    put('本周研判', s.week_total, s.delta + ' 环比');
    put('待处理', s.pending, '需要人处理的');
    put('高危', s.high, 'P0 / P1');
    put('涉及学生', s.students, '去重后');
  }

  function renderList(events) {
    const box = $('#list'); box.innerHTML = '';
    events.forEach(e => {
      const row = el('div', 'ev');
      row.dataset.id = e.id;
      const bar = el('div', 'bar');
      bar.style.background = (LV[e.level] || LV.none).c;
      row.appendChild(bar);

      const body = el('div', 'body');
      const l1 = el('div', 'l1');
      l1.appendChild(el('div', 'tp', esc(e.type)));
      l1.appendChild(el('div', 'an', esc(e.anon)));
      const pill = el('span', 'pill ' + e.status, ST[e.status] || e.status);
      l1.appendChild(pill);
      body.appendChild(l1);
      body.appendChild(el('div', 'l2', esc(e.action)));
      body.appendChild(el('div', 'tm', esc(e.at) + ' · ' + esc(VS[e.victim_state] || e.victim_state)));
      row.appendChild(body);

      row.onclick = () => select(e);
      box.appendChild(row);
    });
  }

  function select(e) {
    cur = e;
    document.querySelectorAll('.ev').forEach(n => n.classList.toggle('on', n.dataset.id === e.id));

    const d = $('#detail');
    d.innerHTML = '';
    d.appendChild(el('h2', '', '告警详情'));

    const lv = LV[e.level] || LV.none;
    const tag = el('span', 'lv', esc(lv.t + '风险'));
    tag.style.background = lv.c;
    d.appendChild(tag);
    d.appendChild(el('div', 'h', esc(e.type)));
    d.appendChild(el('div', 'sub', esc(e.anon) + ' · ' + esc(e.at) + ' · ' + esc(VS[e.victim_state] || e.victim_state)));

    if (e.timeline && e.timeline.length) {
      const ul = el('ul', 'tl');
      e.timeline.forEach(t => {
        const li = el('li', '', esc(t.what));
        li.insertBefore(el('span', 't', esc(t.t)), li.firstChild);
        ul.appendChild(li);
      });
      d.appendChild(ul);
    }

    d.appendChild(el('div', 'action', '<b>建议动作：</b>' + esc(e.action)));

    const acts = el('div', 'actions');
    const b1 = el('button', 'primary', e.status === 'pending' ? '标记为已联系' : '标记为已处理');
    b1.onclick = () => {
      e.status = e.status === 'pending' ? 'contacted' : 'closed';
      renderList(window.__events);
      select(e);
    };
    const b2 = el('button', '', '申请查看原文');
    b2.onclick = () => alert('需要学生本人在 ChatGuard 内单独授权。\n\n授权后：单次可看、7 天有效、全程留痕，学生可随时撤回。\n（演示环境不实际发起请求）');
    acts.appendChild(b1); acts.appendChild(b2);
    d.appendChild(acts);

    d.appendChild(el('div', 'action', '<b>为什么看不到原文：</b>系统只上报"S-4F2A 疑似刷单、已转账"这样的事件，不上报聊天内容。'));
  }

  function renderWeekly(w) {
    const s = $('#scripts'); s.innerHTML = '';
    w.top_scripts.forEach(x => {
      const li = el('li', '', esc(x.name));
      li.appendChild(el('span', 'c', x.count + ' 次'));
      s.appendChild(li);
    });

    const box = $('#byType'); box.innerHTML = '';
    const max = Math.max.apply(null, w.by_type.map(x => x.count));
    w.by_type.forEach(x => {
      const row = el('div', 'barrow');
      row.appendChild(el('div', '', esc(x.type)));
      const tr = el('div', 'track');
      const i = el('i'); i.style.width = Math.round(x.count / max * 100) + '%';
      tr.appendChild(i); row.appendChild(tr);
      row.appendChild(el('div', 'num', String(x.count)));
      box.appendChild(row);
    });
  }

  // ---- 数据源开关 / 刷新 ----
  function bindSourceBar() {
    const btn = document.getElementById('btnSample');
    const ref = document.getElementById('btnRefresh');
    const hint = document.getElementById('srcHint');
    if (!btn) return;
    btn.onclick = () => {
      useSample = !useSample;
      btn.classList.toggle('off', !useSample);
      btn.querySelector('.sdot'); // no-op
      btn.lastChild.textContent = useSample ? '演示数据' : '真实数据';
      if (hint) hint.textContent = useSample
        ? '当前使用演示数据；关闭开关后从后端拉取真实记录'
        : '当前从后端拉取真实记录（本机分析过的对话，不含原文）';
      const c = document.getElementById('btnClear');
      if (c) c.style.display = useSample ? 'none' : '';
      boot();
    };
    if (ref) ref.onclick = () => boot();

    const clr = document.getElementById('btnClear');
    if (clr) {
      clr.onclick = async () => {
        if (!confirm('确定清空全部“真实数据”吗？\n\n只会删除本机分析记录（不含聊天原文），清空后无法恢复。')) return;
        clr.disabled = true;
        try {
          const r = await (await fetch('/api/b/reset?confirm=1')).json();
          if (r && r.ok) {
            if (hint) hint.textContent = '已清空 ' + (r.cleared || 0) + ' 条真实记录';
            await boot();
          } else {
            if (hint) hint.textContent = '清空失败：' + ((r && r.error) || '未知错误');
          }
        } catch (e) {
          if (hint) hint.textContent = '清空失败：连不上后端';
        } finally { clr.disabled = false; }
      };
    }
  }

  // 供"标记已联系"后重渲染用
  const _renderList = renderList;
  renderList = function (evs) { window.__events = evs; _renderList(evs); };

  bindSourceBar();
  boot();
})();
