/* ChatGuard 壳子 · 单页逻辑
 * 只调本域名的 /api/analyze（BFF），API Key 不落在前端。
 * 判定样本全部在后端 shell/mock_data.py，本文件不含任何测试数据。
 */
(() => {
  'use strict';

  // ---------- 反诈小常识（轮播） ----------
  const TIPS = [
    '任何人让你<b>先垫付、后返现</b>，都是骗局。前几单返你是为了让你投入更多。',
    '<b>验证码</b>等于你家钥匙，给谁都等于把门打开。客服、公检法、银行都不会问你要。',
    '官方客服<b>永远不会</b>让你转账到"个人账户"或"安全账户"。',
    '看到<b>「内部文件 严禁外传」</b>先问一句：这种文件为什么会发给我？',
    '熟人借钱，<b>先打个电话</b>。现在的声音和脸都能合成。',
    '让你<b>共享屏幕</b>的，多半是想亲眼看你的验证码。',
    '对方说<b>「别告诉别人」</b>的时候，恰恰是你最该告诉别人的时候。',
    '正规兼职不会收<b>押金、入职费、培训费</b>。收钱的都不是招人。',
    '不怕丢脸，<b>早说一分钟，少损失一万块</b>。',
    '<b>96110</b> 是反诈专线，接到它的来电请一定接听。',
    '遇到可疑的人<b>不要打草惊蛇</b>，先把聊天记录和转账凭证存下来。',
    '游戏账号、皮肤低价交易，让你<b>脱离平台</b>聊的一律拒绝。'
  ];

  const SAMPLES = {
    '刷单': `对方: 在吗？我看你也在找兼职
我: 是的，怎么弄
对方: 很简单，先垫付三单，做完连本带利返给你
我: 要多少钱
对方: 第一单 298，加我 V：abc12345`,
    '客服': `对方: 您好，我是平台客服，您购买的商品有质量问题需要退款
对方: 请提供您的银行卡号和短信验证码，我们马上给您办理
我: 为什么要验证码
对方: 系统需要校验，限时10分钟，超时退款通道就关闭了`,
    '玩笑': `对方: 明天中午吃什么
我: 火锅？
对方: [文件] rce_test.php 44 B
对方: [文件] 【内部文件 严禁外传】通知.pdf 1.3 KB
我: 好～
我: 你发5块钱给我叭
对方: 转账 ¥5.00 已被接收`
  };

  const LEVEL = {
    critical: { color: '#D93025', label: '极高风险' },
    high:     { color: '#E8710A', label: '高风险'   },
    medium:   { color: '#B8860B', label: '中风险'   },
    low:      { color: '#1E8E3E', label: '低风险'   },
    none:     { color: '#5F6368', label: '暂未发现' }
  };
  const TAKE = { money:'钱', info:'信息与资料', body:'身体与影像', affection:'情感依赖', action:'让你做事', enlist:'拉你入场', harm:'伤害' };
  const PERSONA = { authority:'官方/权威', acquaintance:'熟人', lover:'恋人', recruiter:'招募方', peer:'同好', stranger:'陌生人', synthetic:'身份无法核实' };
  const LEVER = { benefit:'利益诱惑', fear:'恐惧威胁', bond:'情感绑定', urgency:'时间紧迫', authority:'权威压迫', scarcity:'稀缺机会', shame:'羞耻与把柄', belonging:'群体认同' };

  const $ = s => document.querySelector(s);
  const el = (tag, cls, html) => { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

  let mode = 'text';
  let file = null;

  // ---------- 切换输入方式 ----------
  document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('on'));
    t.classList.add('on');
    mode = t.dataset.mode;
    $('#paneText').classList.toggle('hidden', mode !== 'text');
    $('#paneImage').classList.toggle('hidden', mode !== 'image');
  }));

  // ---------- 样例 ----------
  document.querySelectorAll('#samples .chip').forEach(c => c.addEventListener('click', () => {
    $('#txt').value = SAMPLES[c.dataset.s] || '';
    document.querySelectorAll('#samples .chip').forEach(x => x.classList.remove('on'));
    c.classList.add('on');
    $('#txt').focus();
  }));

  // ---------- 选图 ----------
  const drop = $('#drop'), fileInput = $('#file'), preview = $('#preview'), dropTip = $('#dropTip');
  drop.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    file = f;
    preview.src = URL.createObjectURL(f);
    preview.classList.remove('hidden');
    dropTip.classList.add('hidden');
    drop.classList.add('has');
  });

  // ---------- 小常识轮播 ----------
  let tipTimer = null, tipIdx = -1;
  function startTips() {
    const box = $('#tip');
    const next = () => {
      tipIdx = (tipIdx + 1) % TIPS.length;
      box.style.opacity = 0;
      setTimeout(() => { box.innerHTML = TIPS[tipIdx]; box.style.opacity = 1; }, 220);
    };
    next();
    tipTimer = setInterval(next, 4800);
  }
  function stopTips() { if (tipTimer) { clearInterval(tipTimer); tipTimer = null; } }

  // ---------- 进度 ----------
  const ORDER = ['up', 'ocr', 'rules', 'judge'];
  function startProgress(hasImage) {
    const items = {}; ORDER.forEach(k => items[k] = document.querySelector(`#steps li[data-k="${k}"]`));
    const set = k => {
      ORDER.forEach(x => {
        items[x].classList.remove('now');
        if (ORDER.indexOf(x) < ORDER.indexOf(k)) items[x].classList.add('done');
      });
      items[k].classList.add('now');
    };
    set('up');
    const plan = hasImage
      ? [['ocr', 1500], ['rules', 24000], ['judge', 30000]]
      : [['ocr', 700], ['rules', 3500], ['judge', 7000]];
    const timers = plan.map(([k, ms]) => setTimeout(() => set(k), ms));
    return {
      finish() { timers.forEach(clearTimeout); ORDER.forEach(x => { items[x].classList.remove('now'); items[x].classList.add('done'); }); }
    };
  }

  // ---------- 请求 ----------
  async function callApi(payload) {
    const res = await fetch('/api/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  }

  let lastText = '';      // 上一次用于判定的文本（多轮补充时作为底稿）
  let lastVersion = 0;

  async function analyze(opts) {
    opts = opts || {};
    let text = (opts.baseText != null ? opts.baseText : ($('#txt').value || '')).trim();
    if (opts.supplement) {
      text = text + '\n\n【用户补充说明（用户自述，非聊天原文）】\n' + opts.supplement;
    }
    if (opts.baseText == null) {
      if (mode === 'text' && text.length < 10) { alert('内容太短了，至少贴几句对话'); return; }
      if (mode === 'image' && !file) { alert('请先选择一张聊天截图'); return; }
    }

    $('#cardInput').classList.add('hidden');
    $('#cardReport').classList.add('hidden');
    $('#cardProgress').classList.remove('hidden');
    $('#progHint').textContent = mode === 'image'
      ? '长图识别大约需要 25–40 秒，请稍候'
      : '大约需要 10–20 秒';

    startTips();
    const prog = startProgress(mode === 'image');

    let data = null;
    try {
      const payload = { mode: opts.baseText != null ? 'text' : mode };
      if (payload.mode === 'image') payload.image_base64 = await toBase64(file);
      else payload.text = text;
      data = await callApi(payload);
      if (!data.ok) throw new Error(data.error || '分析失败');
    } catch (e) {
      // 不静默降级：明确告知失败原因，并指向控制面板的"样例模式"
      prog.finish();
      stopTips();
      $('#cardProgress').classList.add('hidden');
      renderError(String(e.message || e));
      return;
    }

    prog.finish();
    stopTips();
    $('#cardProgress').classList.add('hidden');

    // 记住底稿，供"补充情况后再查一次"使用
    lastVersion = opts.version || 1;
    const fromTranscript = data.transcript && data.transcript.messages ? transcriptToText(data.transcript) : '';
    lastText = fromTranscript || text;
    data.__version = lastVersion;

    renderReport(data);
  }

  function toBase64(f) {
    // 上传前把宽压到 ≤1080：长截图 base64 体积可减半，思路见 MINA.md
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => {
        const img = new Image();
        img.onload = () => {
          const MAX = 1080;
          if (img.width <= MAX) { res(String(r.result).split(',')[1]); return; }
          const scale = MAX / img.width;
          const c = document.createElement('canvas');
          c.width = MAX;
          c.height = Math.round(img.height * scale);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          res(c.toDataURL('image/jpeg', 0.9).split(',')[1]);
        };
        img.onerror = () => res(String(r.result).split(',')[1]);
        img.src = String(r.result);
      };
      r.onerror = rej;
      r.readAsDataURL(f);
    });
  }

  // 把结构化转录还原成可再次提交的文本
  function transcriptToText(tr) {
    if (!tr || !tr.messages) return '';
    return tr.messages.map(m => {
      if (m.type === 'file') return (m.speaker === 'me' ? '我' : '对方') + ': [文件] ' + (m.name || '');
      if (m.type === 'transfer') return '系统: 转账 ' + (m.text || '');
      if (m.type === 'system_time') return (m.text || '');
      return (m.speaker === 'me' ? '我' : m.speaker === 'them' ? '对方' : '未知') + ': ' + (m.text || '');
    }).join('\n');
  }

  // ---------- 失败态（绝不静默降级） ----------
  function renderError(msg) {
    const card = $('#cardReport');
    card.innerHTML = '';
    card.classList.remove('hidden');
    const box = el('section', 'card');

    const band = el('div', 'band');
    band.style.background = '#5F6368';
    band.appendChild(el('div', 'lv', '未能完成判定'));
    band.appendChild(el('div', 'one', '这次没有拿到平台的判定结果，我们不会替你编一个。'));
    box.appendChild(band);

    const sec = el('div', 'sec');
    sec.appendChild(el('h3', '', '原因'));
    sec.appendChild(el('div', 'verify', esc(msg)));
    box.appendChild(sec);

    const sec2 = el('div', 'sec');
    sec2.appendChild(el('h3', '', '你可以'));
    const ul = el('ul', 'todo');
    ul.appendChild(el('li', '', '<b>断网或平台额度不足</b>时：在控制面板勾选「使用测试样例」，再点重试'));
    ul.appendChild(el('li', '', '网络正常时：稍等片刻重试（平台偶发 502）'));
    ul.appendChild(el('li', '', '也可以先把这段对话存下来，等有网络再分析'));
    sec2.appendChild(ul);
    box.appendChild(sec2);

    const r = el('button', 'primary', '重试');
    r.style.marginTop = '12px';
    r.onclick = () => analyze();
    box.appendChild(r);

    const b = el('button', 'ghost', '回到输入');
    b.onclick = () => { card.classList.add('hidden'); $('#cardInput').classList.remove('hidden'); };
    box.appendChild(b);

    card.appendChild(box);
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ---------- 渲染报告 ----------
  function renderReport(data) {
    const j = data.judgment || {};
    const lv = LEVEL[j.level] || LEVEL.none;
    const card = $('#cardReport');
    card.innerHTML = '';
    card.classList.remove('hidden');

    const box = el('section', 'card');

    const band = el('div', 'band');
    band.style.background = lv.color;
    band.appendChild(el('div', 'lv', esc(lv.label)
      + (data.meta && data.meta.sample ? ' · 样例结果（未调用平台）' : '')
      + (data.__version > 1 ? ' · 第 ' + data.__version + ' 版（含补充说明）' : '')));
    band.appendChild(el('div', 'one', esc(j.one_line || '')));
    box.appendChild(band);

    const axes = el('div', 'axes');
    const put = (k, v) => { const d = el('div', 'axis'); d.appendChild(el('div', 'k', k)); d.appendChild(el('div', 'v', esc(v))); axes.appendChild(d); };
    put('对方想得到什么', (j.take || []).map(x => TAKE[x] || x).join('、') || '—');
    put('对方扮演谁', (j.persona || []).map(x => PERSONA[x] || x).join('、') || '—');
    put('用什么施压', (j.lever || []).map(x => LEVER[x] || x).join('、') || '—');
    put('你在哪一步', victimLabel(j.victim_state));
    box.appendChild(axes);

    if ((j.hypotheses || []).length) {
      const sec = el('div', 'sec');
      sec.appendChild(el('h3', '', '两种可能，都需要你确认'));
      j.hypotheses.forEach(h => {
        const d = el('div', 'hyp');
        const top = el('div', 'top');
        top.appendChild(el('div', 'nm', esc(h.name)));
        top.appendChild(el('div', 'cf', Math.round((h.confidence || 0) * 100) + '%'));
        d.appendChild(top);
        const bar = el('div', 'bar'); const i = el('i');
        i.style.width = Math.round((h.confidence || 0) * 100) + '%';
        bar.appendChild(i); d.appendChild(bar);
        if (h.supports) d.appendChild(el('div', 'd', '<b>支持：</b>' + esc(h.supports)));
        if (h.against) d.appendChild(el('div', 'd', '<b>反对：</b>' + esc(h.against)));
        sec.appendChild(d);
      });
      box.appendChild(sec);
    }

    if ((j.evidence || []).length) {
      const sec = el('div', 'sec');
      sec.appendChild(el('h3', '', '依据（原文）'));
      j.evidence.forEach(ev => {
        const d = el('div', 'ev');
        d.appendChild(el('div', 'q', '「' + esc(ev.quote) + '」'));
        if (ev.why) d.appendChild(el('div', 'w', esc(ev.why)));
        sec.appendChild(d);
      });
      box.appendChild(sec);
    }

    if (j.identity_check) {
      const sec = el('div', 'sec');
      sec.appendChild(el('h3', '', '先核实身份（换渠道）'));
      sec.appendChild(el('div', 'verify', esc(j.identity_check)));
      box.appendChild(sec);
    }

    if ((j.what_to_do || []).length) {
      const sec = el('div', 'sec');
      sec.appendChild(el('h3', '', '现在就做'));
      const ul = el('ul', 'todo');
      j.what_to_do.forEach(x => ul.appendChild(el('li', '', esc(x))));
      sec.appendChild(ul);
      box.appendChild(sec);
    }

    if ((j.uncertain || []).length) {
      const sec = el('div', 'sec');
      sec.appendChild(el('h3', '', '还不确定的事'));
      const ul = el('ul', 'unc');
      j.uncertain.forEach(x => ul.appendChild(el('li', '', esc(x))));
      sec.appendChild(ul);
      box.appendChild(sec);
    }

    if (data.rules && (data.rules.hits || []).length) {
      const sec = el('div', 'sec');
      sec.appendChild(el('h3', '', '机器规则命中'));
      sec.appendChild(el('div', 'd', esc(data.rules.hits.join('、'))));
      if (j.rule_check) sec.appendChild(el('div', 'd', esc(j.rule_check)));
      box.appendChild(sec);
    }

    box.appendChild(el('div', 'disc', esc(j.disclaimer || 'AI 判断，仅供参考。')));

    const again = el('button', 'ghost', '补充情况后再查一次');
    again.onclick = () => {
      if (again.dataset.open === '1') return;
      again.dataset.open = '1';
      const box2 = el('div', 'sec');
      const h = el('h3', '', '补充情况（会重新研判一次，不覆盖这一版）');
      const ta = document.createElement('textarea');
      ta.placeholder = '例如：他后来还让我下载一个 APP / 我其实已经转了 300 / 这个人是我室友';
      ta.style.cssText = 'width:100%;min-height:78px;border:1px solid var(--line);border-radius:9px;padding:9px;font:inherit;margin-top:6px';
      const go = el('button', 'primary', '带上补充重新研判');
      go.style.marginTop = '9px';
      go.onclick = () => {
        const v = (ta.value || '').trim();
        if (v.length < 2) { alert('写两句再提交'); return; }
        analyze({ baseText: lastText, supplement: v, version: lastVersion + 1 });
      };
      box2.appendChild(h); box2.appendChild(ta); box2.appendChild(go);
      box.appendChild(box2);
      ta.focus();
    };
    box.appendChild(again);

    const del = el('button', 'ghost', '清除这次记录');
    del.onclick = () => {
      file = null; $('#txt').value = '';
      preview.classList.add('hidden'); preview.src = '';
      dropTip.classList.remove('hidden'); drop.classList.remove('has');
      $('#cardReport').classList.add('hidden');
      $('#cardInput').classList.remove('hidden');
    };
    box.appendChild(del);

    if (data.meta) {
      const m = el('div', 'disc');
      m.textContent = '耗时 ' + (data.meta.secs || '—') + ' 秒'
        + (data.meta.sample ? ' · 样例数据（控制面板已开启样例模式）' : '');
      box.appendChild(m);
    }

    card.appendChild(box);
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function victimLabel(v) {
    return ({ none:'还没给出去', money_lost:'已转账', info_leaked:'已给信息', media_held:'影像被持有', acted:'已按指示行动', in_danger:'有人身危险' })[v] || '—';
  }

  $('#go').addEventListener('click', analyze);
})();
