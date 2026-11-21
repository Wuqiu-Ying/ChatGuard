/* ChatGuard 数据视图（G 端）
 * ?view=telecom|police|edu 决定展示哪些字段（白名单在服务端也裁一次）。
 * 本页面是只读的：没有任何操作按钮，也没有个人身份与聊天原文。
 */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const el = (t, c, h) => { const n = document.createElement(t); if (c) n.className = c; if (h != null) n.innerHTML = h; return n; };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  const view = (new URLSearchParams(location.search).get('view') || 'telecom').toLowerCase();

  let useSample = true;   // 默认演示数据
  const srcParam = () => (useSample ? '' : '&source=live');

  const NOTES = {
    telecom: '这些是"作案工具"的线索，不是"人的身份"。同一号码被 15 个人报告，说明这个工具在扩散——加黑它能阻断后续受害者。被冒用的官方号（如 95588）会进白名单，永不加黑。',
    police: '我们只提供"哪类案在涨、话术怎么变、哪些载体在扩散"。要查"谁被骗了"，得走法定调证程序，我们出示数据但不主动推送。',
    edu: '各校只能看到自己的明细；这里看到的是汇总，看不到学生是谁、聊了什么。用于考核与资源投放，不用于处分任何学生。'
  };

  document.querySelectorAll('.switcher a[data-v]').forEach(a => {
    a.classList.toggle('on', a.dataset.v === view);
  });

  function chip(text, cls) { return el('span', 'chip ' + (cls || ''), esc(text)); }

  async function boot() {
    let d;
    try { d = await (await fetch('/api/g/report?view=' + encodeURIComponent(view) + srcParam())).json(); }
    catch (e) { $('#roleTitle').textContent = '无法连接后端'; return; }
    if (!d || !d.ok) { $('#roleTitle').textContent = (d && d.error) || '加载失败'; return; }

    $('#roleTitle').textContent = d.role.title;
    $('#roleSub').textContent = d.role.sub + '（更新于 ' + d.updated + '）';
    const vis = $('#vis'), hid = $('#hid');
    vis.innerHTML = ''; hid.innerHTML = '';
    d.role.visible.forEach(x => vis.appendChild(chip(x, 'yes')));
    d.role.hidden.forEach(x => hid.appendChild(chip(x, 'no')));
    $('#roleNote').textContent = NOTES[view] || '';

    const box = $('#content');
    box.innerHTML = '';
    const empty = !(d.carriers && d.carriers.length) && !(d.types && d.types.length)
               && !(d.schools && d.schools.length);
    if (empty) {
      box.appendChild(el('div', 'note', '还没有真实记录。到「学生端」分析几段对话，这里就会出现线索。'));
    }
    if (view === 'telecom') box.appendChild(carriersCard(d.carriers, true));
    if (view === 'police') {
      box.appendChild(typesCard(d.types));
      box.appendChild(variantsCard(d.variants));
      box.appendChild(carriersCard(d.carriers, false));
    }
    if (view === 'edu') {
      box.appendChild(schoolsCard(d.schools));
      box.appendChild(quarterCard(d.quarter));
    }
  }

  function carriersCard(list, full) {
    const c = el('section', 'card');
    c.appendChild(el('h2', '', '涉诈载体线索' + (full ? '' : '（前 4 条）')));
    const t = el('table');
    const head = el('tr');
    ['载体值', '类型', '被报告', '首次 / 最近', '可伪造度', '说明'].forEach(h => head.appendChild(el('th', '', esc(h))));
    t.appendChild(head);
    list.forEach(x => {
      const tr = el('tr');
      tr.appendChild(el('td', 'mono', esc(x.v)));
      tr.appendChild(el('td', '', '<span class="tag">' + esc(x.t) + '</span>'));
      tr.appendChild(el('td', '', esc(x.n) + ' 次'));
      tr.appendChild(el('td', '', esc(x.first) + ' → ' + esc(x.last)));
      const f = el('td', '', '<span class="tag ' + (x.forge === '低' ? 'ok' : (x.forge === '高' ? 'no' : '')) + '">' + esc(x.forge) + '</span>');
      tr.appendChild(f);
      tr.appendChild(el('td', '', '<span style="color:var(--ink3);font-size:12px">' + esc(x.note) + '</span>'));
      t.appendChild(tr);
    });
    c.appendChild(t);
    return c;
  }

  function typesCard(list) {
    const c = el('section', 'card');
    c.appendChild(el('h2', '', '类型分布（近 30 天）'));
    const bars = el('div', 'bars');
    const max = Math.max.apply(null, list.map(x => x.count));
    list.forEach(x => {
      const row = el('div', 'barrow');
      row.appendChild(el('div', '', esc(x.type)));
      const tr = el('div', 'track'); const i = el('i');
      i.style.width = Math.round(x.count / max * 100) + '%'; tr.appendChild(i);
      row.appendChild(tr);
      row.appendChild(el('div', 'num', esc(x.count) + '  ' + esc(x.delta)));
      bars.appendChild(row);
    });
    c.appendChild(bars);
    return c;
  }

  function variantsCard(list) {
    const c = el('section', 'card');
    c.appendChild(el('h2', '', '本周新增话术变种'));
    const t = el('table');
    const head = el('tr');
    ['话术特征', '归类', '出现次数'].forEach(h => head.appendChild(el('th', '', esc(h))));
    t.appendChild(head);
    list.forEach(x => {
      const tr = el('tr');
      tr.appendChild(el('td', '', esc(x.name)));
      tr.appendChild(el('td', '', '<span class="tag">' + esc(x.type) + '</span>'));
      tr.appendChild(el('td', '', esc(x.seen) + ' 次'));
      t.appendChild(tr);
    });
    c.appendChild(t);
    return c;
  }

  function schoolsCard(list) {
    const c = el('section', 'card');
    c.appendChild(el('h2', '', '各校研判与处置'));
    const t = el('table');
    const head = el('tr');
    ['学校', '研判量', '预警量', '已处置', '处置率'].forEach(h => head.appendChild(el('th', '', esc(h))));
    t.appendChild(head);
    list.forEach(x => {
      const tr = el('tr');
      tr.appendChild(el('td', '', esc(x.name)));
      tr.appendChild(el('td', '', esc(x.n)));
      tr.appendChild(el('td', '', esc(x.warn)));
      tr.appendChild(el('td', '', esc(x.done)));
      tr.appendChild(el('td', '', '<span class="tag ' + (parseFloat(x.rate) >= 70 ? 'ok' : '') + '">' + esc(x.rate) + '</span>'));
      t.appendChild(tr);
    });
    c.appendChild(t);
    return c;
  }

  function quarterCard(list) {
    const c = el('section', 'card');
    c.appendChild(el('h2', '', '季度趋势'));
    const bars = el('div', 'bars');
    const max = Math.max.apply(null, list.map(x => x.n));
    list.forEach(x => {
      const row = el('div', 'barrow');
      row.appendChild(el('div', '', esc(x.m)));
      const tr = el('div', 'track'); const i = el('i');
      i.style.width = Math.round(x.n / max * 100) + '%'; tr.appendChild(i);
      row.appendChild(tr);
      row.appendChild(el('div', 'num', esc(x.n)));
      bars.appendChild(row);
    });
    c.appendChild(bars);
    return c;
  }

  // ---- 数据源开关 / 刷新 ----

  (function bindBar() {
    const btn = document.getElementById('btnSample');
    const ref = document.getElementById('btnRefresh');
    const hint = document.getElementById('srcHint');
    if (!btn) return;
    btn.onclick = () => {
      useSample = !useSample;
      btn.classList.toggle('off', !useSample);
      btn.lastChild.textContent = useSample ? '演示数据' : '真实数据';
      if (hint) hint.textContent = useSample
        ? '当前使用演示数据；关闭开关后从后端拉取真实记录'
        : '当前从后端拉取真实记录（本机分析过的对话，不含原文）';
      boot();
    };
    if (ref) ref.onclick = () => boot();
  })();

  boot();
})();
