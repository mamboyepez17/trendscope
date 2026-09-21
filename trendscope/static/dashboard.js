const API = ''; // same origin
const WS_BASE = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
function getApiKey(){
  return sessionStorage.getItem('ts_api_key') || new URLSearchParams(location.search).get('api_key') || '';
}
function apiHeaders(){
  const h = {};
  const k = getApiKey();
  if (k) h['X-API-Key'] = k;
  return h;
}
const WS = (() => {
  const k = getApiKey();
  return k ? WS_BASE + '?api_key=' + encodeURIComponent(k) : WS_BASE;
})();
const $ = id => document.getElementById(id);

const SRC_COLORS = {
  reddit:/^reddit/, twitter:/^twitter/, google_trends:/^google_trends/,
  hackernews:/^hackernews/, youtube:/^youtube/, amazon:/^amazon/, tiktok:/^tiktok/,
  gdelt:/^gdelt/, google_news:/^google_news/, bing:/^bing/, wikipedia:/^wikipedia/,
  bluesky:/^bluesky/
};
const SRC_HEX = {
  reddit:'#c45c26', twitter:'#5b9aa0', google_trends:'#6a7fa8',
  hackernews:'#c96b5c', youtube:'#b85c4a', amazon:'#d4a054', tiktok:'#8b6b9e',
  gdelt:'#6a7fa8', google_news:'#5b9aa0', bing:'#6a7fa8', wikipedia:'#8a938f',
  bluesky:'#5b9aa0', reddit_comment:'#c45c26', twitter_comment:'#5b9aa0'
};

function srcKey(name){
  name = (name||'').toLowerCase();
  for(const k in SRC_COLORS) if(SRC_COLORS[k].test(name)) return k;
  return name.replace(/[^a-z0-9]/g,'_') || 'other';
}
function srcColor(name){ return SRC_HEX[srcKey(name)] || getCss('--muted', '#8a938f'); }
function srcLabel(name){ return (name||'').replace(/_/g,' '); }
function getCss(v, fb){
  return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || fb;
}

function scoreColor(s){ return s>=75?getCss('--neg','#c96b5c'): s>=50?getCss('--accent','#d4a054'):getCss('--pos','#6fbf73'); }
function sentiInfo(label){
  label=(label||'neutral').toLowerCase();
  if(label.startsWith('pos')) return {cls:'pos',sym:'+',col:getCss('--pos','#6fbf73')};
  if(label.startsWith('neg')) return {cls:'neg',sym:'−',col:getCss('--neg','#c96b5c')};
  return {cls:'neu',sym:'~',col:getCss('--muted','#8a938f')};
}
function fmt(n){
  if(n==null) return '—';
  n=Number(n);
  if(n>=1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'')+'M';
  if(n>=1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'')+'K';
  return String(n);
}
function esc(s){ return (s==null?'':String(s)).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function trunc(s,n){ s=s||''; return s.length>n? s.slice(0,n-1)+'…':s; }

/* ---------- Categories ---------- */
async function loadCategories(){
  try{
  const r = await fetch(API+'/categories', {headers: apiHeaders()});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const j = await r.json();
    const cats = (j && j.categories) || [];
    const sel = $('cat');
    sel.innerHTML = '<option value="">— free —</option>' +
      cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  }catch(e){
    const sel=$('cat');
    sel.innerHTML = '<option value="">tecnologia</option>'.replace('tecnologia',
      ['tecnologia','economia','salud','moda','deportes','politica','emprendimiento','educacion','inmobiliario','crypto']
      .map(c=>`<option value="${c}">${c}</option>`).join(''));
  }
}

/* ---------- Fetch ---------- */
async function fetchTrends({category, topic, geo='CO'}){
  const p = new URLSearchParams();
  if(topic) p.set('topic', topic);
  else if(category) p.set('category', category);
  if(geo) p.set('geo', geo);
  p.set('top_n','25');
  const r = await fetch(API+'/trends?'+p.toString(), {headers: apiHeaders()});
  if(!r.ok){
    let msg='HTTP '+r.status;
    try{ const e=await r.json(); msg=e.detail||msg; }catch(_){}
    throw new Error(msg);
  }
  return await r.json();
}

async function api(method, path, body){
  const opts={method,headers: apiHeaders()};
  if(body){opts.headers['Content-Type']='application/json'; opts.body=JSON.stringify(body);}
  const r=await fetch(API+path,opts);
  if(!r.ok){
    let msg='HTTP '+r.status;
    try{const e=await r.json();msg=e.detail||msg;}catch(_){}
    throw new Error(msg);
  }
  return r.status===204?null:await r.json();
}

/* ---------- Status helpers ---------- */
function showLoading(msg){
  const s=$('status'); s.className='status show';
  s.innerHTML=`<div class="loader"><div class="spinner"></div><div>${esc(msg||'Analyzing trends…')}</div></div>`;
}
function showError(msg){
  const s=$('status'); s.className='status show';
  s.innerHTML=`<div class="error"><b>⚠ Error:</b><span>${esc(msg)}</span></div>`;
}
function clearStatus(){ $('status').className='status'; $('status').innerHTML=''; }

/* ---------- Render: stats ---------- */
function renderStats(meta){
  const ss = meta.sentiment_summary||{};
  const total = meta.total_analyzed ?? 0;
  const sources = (meta.sources_used||[]).length;
  const top = meta.top_trends ? meta.top_trends[0]?.trend_score : null;
  const topScore = top!=null ? Math.round(top) : '—';
  const pos=ss.positive||0, neg=ss.negative||0, neu=ss.neutral||0;
  const cpos=getCss('--pos','#6fbf73'), cneg=getCss('--neg','#c96b5c'), cneu=getCss('--muted','#8a938f');
  $('stats').innerHTML = `
    <div class="stat"><div class="k">Total signals</div><div class="v" data-count="${total}">0</div></div>
    <div class="stat"><div class="k">Active sources</div><div class="v" data-count="${sources}">0</div></div>
    <div class="stat"><div class="k">Sentiment</div><div class="v" style="font-size:20px;line-height:1.3">
        <span class="pill" style="color:${cpos}"><span class="dot" style="background:${cpos}"></span>${pos}+</span>
        <span class="pill" style="color:${cneg}"><span class="dot" style="background:${cneg}"></span>${neg}−</span>
        <span class="pill" style="color:${cneu}"><span class="dot" style="background:${cneu}"></span>${neu}~</span></div></div>
    <div class="stat"><div class="k">Top score</div><div class="v" data-count="${topScore}">0</div></div>`;
  animateCounts();
}
function animateCounts(){
  document.querySelectorAll('[data-count]').forEach(el=>{
    const target=el.getAttribute('data-count');
    if(target==='—'){ el.textContent='—'; return; }
    const n=parseInt(target,10); if(isNaN(n)){ el.textContent=target; return; }
    const dur=900, t0=performance.now();
    function step(t){
      const p=Math.min((t-t0)/dur,1); const e=1-Math.pow(1-p,3);
      el.textContent=Math.round(n*e);
      if(p<1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
}

/* ---------- Render: gauge ---------- */
function renderGauge(meta){
  const ss=meta.sentiment_summary||{};
  const pos=ss.positive||0, neg=ss.negative||0, neu=ss.neutral||0;
  const total=Math.max(pos+neg+neu,1);
  const pP=pos/total, pN=neg/total, pU=neu/total;
  const R=70, C=2*Math.PI*R;
  const segs=[
    {v:pP,col:getCss('--pos','#6fbf73'),lbl:'Positive'},
    {v:pU,col:getCss('--muted','#8a938f'),lbl:'Neutral'},
    {v:pN,col:getCss('--neg','#c96b5c'),lbl:'Negative'}
  ];
  let offset=0;
  const arcs = segs.map(s=>{
    const len=s.v*C;
    const el=`<circle cx="100" cy="100" r="${R}" fill="none" stroke="${s.col}" stroke-width="22"
      stroke-dasharray="${len.toFixed(2)} ${(C-len).toFixed(2)}"
      stroke-dashoffset="${(-offset).toFixed(2)}"
      transform="rotate(-90 100 100)" style="transition:stroke-dasharray 1s cubic-bezier(.2,.8,.2,1)"/>`;
    offset+=len; return el;
  }).join('');
  const overall=(ss.overall||'neutral');
  const oi=sentiInfo(overall);
  $('gaugeWrap').innerHTML=`
    <svg viewBox="0 0 200 200" width="200" height="200">
      <circle cx="100" cy="100" r="${R}" fill="none" stroke="#1a2238" stroke-width="22"/>
      ${arcs}
      <text x="100" y="86" text-anchor="middle" fill="#6b7a99" font-size="12" font-weight="700">OVERALL</text>
      <text x="100" y="96" text-anchor="middle" fill="#e0e6ed" font-size="30" font-weight="800">${total}</text>
      <text x="100" y="118" text-anchor="middle" fill="${oi.col}" font-size="12" font-weight="700" style="text-transform:uppercase">${esc(overall)} ${oi.sym}</text>
    </svg>
    <div class="gauge-legend">
      ${segs.map(s=>`<div class="row"><span class="pill"><span class="dot" style="background:${s.col}"></span>${s.lbl}</span>
        <span class="bar-mini"><i style="background:${s.col};transform:scaleX(${s.v})"></i></span>
        <b>${Math.round(s.v*100)}%</b></div>`).join('')}
    </div>`;
}

/* ---------- Render: sources ---------- */
function renderSources(trends){
  const counts={};
  trends.forEach(t=>{ const k=srcKey(t.source); counts[k]=(counts[k]||0)+1; });
  const rows=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  const max=Math.max(...rows.map(r=>r[1]),1);
  $('sources').innerHTML = rows.map(([k,c])=>`
    <div class="src-row">
      <div class="src-name"><span class="dot" style="background:${srcColor(k)}"></span>${esc(srcLabel(k))}</div>
      <div class="src-track"><div class="src-fill" data-w="${(c/max*100).toFixed(1)}" style="background:${srcColor(k)}"></div></div>
      <div class="src-count">${c}</div>
    </div>`).join('') || '<div class="empty">No data</div>';
  requestAnimationFrame(()=>{
    document.querySelectorAll('#sources .src-fill').forEach(el=>{ el.style.width=el.getAttribute('data-w')+'%'; });
  });
}

/* ---------- Render: histogram ---------- */
function renderHistogram(trends){
  const bins=[0,0,0,0,0];
  trends.forEach(t=>{
    let s=t.trend_score||0;
    let i = s>=80?4 : s>=60?3 : s>=40?2 : s>=20?1 : 0;
    bins[i]++;
  });
  const max=Math.max(...bins,1);
  const labels=['0-19','20-39','40-59','60-79','80-100'];
  const cols=[getCss('--pos','#6fbf73'),getCss('--pos','#6fbf73'),getCss('--accent','#d4a054'),getCss('--neg','#c96b5c'),getCss('--neg','#c96b5c')];
  $('hist').innerHTML = bins.map((c,i)=>`
    <div class="hist-col">
      <div class="hist-bar" data-h="${(c/max*100).toFixed(1)}" style="background:linear-gradient(180deg,${cols[i]},${cols[i]}aa)"></div>
      <div class="hist-lbl">${c}</div>
      <div class="hist-lbl">${labels[i]}</div>
    </div>`).join('');
  requestAnimationFrame(()=>{
    document.querySelectorAll('#hist .hist-bar').forEach(el=>{ el.style.height=el.getAttribute('data-h')+'%'; });
  });
}

/* ---------- Render: trends table ---------- */
function trendsHTML(trends, maxShow){
  const list=(trends||[]).slice(0,maxShow||25);
  if(!list.length) return '<div class="empty"><div class="big">∅</div>No trends found</div>';
  return list.map((t,i)=>{
    const s=sentiInfo(t.sentiment?.label);
    const sc=t.trend_score||0;
    const sig=t.signals||{};
    const eng=[];
    if(sig.likes!=null) eng.push(`<span>❤ <b>${fmt(sig.likes)}</b></span>`);
    if(sig.retweets!=null) eng.push(`<span>🔁 <b>${fmt(sig.retweets)}</b></span>`);
    if(sig.comments!=null) eng.push(`<span>💬 <b>${fmt(sig.comments)}</b></span>`);
    if(sig.youtube_views!=null) eng.push(`<span>▶ <b>${fmt(sig.youtube_views)}</b></span>`);
    if(sig.reddit_score!=null) eng.push(`<span>⬆ <b>${fmt(sig.reddit_score)}</b></span>`);
    if(sig.google_traffic!=null) eng.push(`<span>📈 <b>${esc(sig.google_traffic)}</b></span>`);
    if(sig.amazon_rank!=null) eng.push(`<span>🛒 <b>#${fmt(sig.amazon_rank)}</b></span>`);
    const col=scoreColor(sc);
    const url=t.url?`<a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(trunc(t.title,140))}</a>`:esc(trunc(t.title,140));
    return `<li class="trend" style="animation-delay:${Math.min(i*40,600)}ms">
      <div class="rank ${i<3?'top':''}">${t.rank||i+1}</div>
      <div class="trend-main">
        <div class="trend-title">${url}</div>
        <div class="trend-meta">
          <span class="badge" style="background:${srcColor(t.source)}22;color:${srcColor(t.source)};border:1px solid ${srcColor(t.source)}55">${esc(srcLabel(t.source))}</span>
          <span class="senti ${s.cls}"><b class="ico">${s.sym}</b> ${esc(t.sentiment?.label||'neutral')}</span>
          ${t.category?`<span style="color:var(--muted);font-size:11px">${esc(t.category)}</span>`:''}
        </div>
        ${eng.length?`<div class="eng">${eng.join('')}</div>`:''}
      </div>
      <div class="scorebar-wrap">
        <div class="scorebar"><i data-w="${Math.min(sc,100)}" style="background:${col}"></i></div>
        <div class="score-num" style="color:${col}">${sc.toFixed?sc.toFixed(1):sc}</div>
      </div>
    </li>`;
  }).join('');
}
function renderTrends(data){
  const meta=data.meta||{};
  const q=meta.query||{};
  $('meta').innerHTML = `
    <span>📅 <b>${esc(meta.date||'')}</b></span>
    <span>🔍 <b>${esc(q.topic||q.category||'')}</b></span>
    <span>🌍 <b>${esc(q.geo||'CO')}</b></span>
    <span>🛰 <b>${esc((meta.sources_used||[]).join(', '))}</b></span>
    <span>🧠 <b>${esc(meta.sentiment_summary?.engine||'local')}</b></span>`;
  $('trends').innerHTML = trendsHTML(data.top_trends);
  requestAnimationFrame(()=>{
    document.querySelectorAll('#trends .scorebar > i').forEach(el=>{ el.style.width=el.getAttribute('data-w')+'%'; });
  });
}

/* ---------- Render full single ---------- */
function renderSingle(data){
  const meta=data.meta||{};
  renderStats(meta);
  renderGauge(meta);
  renderSources(data.top_trends||[]);
  renderHistogram(data.top_trends||[]);
  renderTrends(data);
}

/* ---------- Comparison ---------- */
function renderComparison(d1,d2,t1,t2){
  const panel=(d,title)=>`
    <div class="panel">
      <div class="ph"><span class="dot" style="background:var(--accent)"></span>${esc(title)}</div>
      <div class="pb">
        ${(d.top_trends||[]).slice(0,10).map((t,i)=>{
          const s=sentiInfo(t.sentiment?.label); const sc=t.trend_score||0; const col=scoreColor(sc);
          return `<div class="trend" style="animation-delay:${i*30}ms">
            <div class="rank ${i<3?'top':''}">${t.rank||i+1}</div>
            <div class="trend-main">
              <div class="trend-title">${t.url?`<a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(trunc(t.title,100))}</a>`:esc(trunc(t.title,100))}</div>
              <div class="trend-meta">
                <span class="badge" style="background:${srcColor(t.source)}22;color:${srcColor(t.source)};border:1px solid ${srcColor(t.source)}55">${esc(srcLabel(t.source))}</span>
                <span class="senti ${s.cls}"><b class="ico">${s.sym}</b></span>
              </div>
            </div>
            <div class="scorebar-wrap"><div class="scorebar"><i data-w="${Math.min(sc,100)}" style="background:${col}"></i></div>
              <div class="score-num" style="color:${col}">${sc.toFixed?sc.toFixed(1):sc}</div></div>
          </div>`;
        }).join('') || '<div class="empty"><div class="big">∅</div>No data</div>'}
      </div>
    </div>`;
  $('cmpPanels').innerHTML = panel(d1,t1)+panel(d2,t2);
  requestAnimationFrame(()=>{
    document.querySelectorAll('#cmpPanels .scorebar > i').forEach(el=>{ el.style.width=el.getAttribute('data-w')+'%'; });
  });
}

/* ---------- Watchlist ---------- */
let watchlistItems=[];
async function loadWatchlist(){
  try{
    const j=await api('GET','/watchlist');
    watchlistItems=j.items||[];
    renderWatchlist();
  }catch(e){ console.error('loadWatchlist',e); }
}
function renderWatchlist(){
  const el=$('watchlist');
  if(!watchlistItems.length){ el.innerHTML='<div class="empty">No items yet</div>'; return; }
  // Sin onclick inline: el CSP script-src 'self' los bloquea
  el.innerHTML=watchlistItems.map(item=>`
    <div class="watch-item">
      <div class="watch-info">
        <div class="watch-topic">${esc(item.topic)}</div>
        <div class="watch-meta">${esc(item.geo)} · every ${item.interval_minutes}m · ${item.active?'active':'paused'}</div>
      </div>
      <div class="watch-actions">
        <button type="button" class="btn sm" data-action="run" data-id="${item.id}">▶</button>
        <button type="button" class="btn sm ghost" data-action="history" data-topic="${esc(item.topic)}">📈</button>
        <button type="button" class="btn sm danger" data-action="delete" data-id="${item.id}">✕</button>
      </div>
    </div>`).join('');
}
async function addWatchItem(){
  const topic=$('wlTopic').value.trim();
  const interval=parseInt($('wlInterval').value,10)||60;
  if(!topic){ showError('Enter a topic'); return; }
  try{
    await api('POST',`/watchlist?topic=${encodeURIComponent(topic)}&interval_minutes=${interval}`);
    $('wlTopic').value='';
    await loadWatchlist();
  }catch(e){ showError(e.message); }
}
async function deleteWatchItem(id){
  try{
    await api('DELETE',`/watchlist/${id}`);
    await loadWatchlist();
  }catch(e){ showError(e.message); }
}
async function runWatchItem(id){
  try{
    await api('POST',`/watchlist/${id}/run`);
    await loadWatchlist();
    const item=watchlistItems.find(x=>x.id===id);
    if(item) viewHistory(item.topic);
  }catch(e){ showError(e.message); }
}

/* ---------- History chart ---------- */
let historyChart=null;
async function viewHistory(topic){
  $('histTopic').textContent=topic;
  try{
    const j=await api('GET',`/history?topic=${encodeURIComponent(topic)}&days=7`);
    const records=j.records||[];
    $('histCount').textContent=records.length;
    renderHistoryList(records);
    renderHistoryChart(records);
  }catch(e){ console.error('viewHistory',e); }
}
function renderHistoryList(records){
  if(!records.length){ $('historyList').innerHTML='<div class="empty">No history</div>'; return; }
  const cpos=getCss('--pos','#6fbf73'), cneg=getCss('--neg','#c96b5c');
  $('historyList').innerHTML=records.slice(0,20).map(r=>`
    <div class="history-row">
      <span>${new Date(r.analyzed_at).toLocaleString()}</span>
      <span>score <b>${r.top_score.toFixed?r.top_score.toFixed(1):r.top_score}</b></span>
      <span>signals <b>${r.total_signals}</b></span>
      <span style="color:${cpos}">+${r.positive}</span>
      <span style="color:${cneg}">−${r.negative}</span>
    </div>`).join('');
}
function renderHistoryChart(records){
  const ctx=$('historyChart').getContext('2d');
  const labels=records.map(r=>new Date(r.analyzed_at).toLocaleDateString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}));
  const scores=records.map(r=>r.top_score);
  const volumes=records.map(r=>r.total_signals);
  const accent=getCss('--accent','#d4a054');
  const teal=getCss('--accent-2','#5b9aa0');
  const muted=getCss('--muted','#8a938f');
  const border=getCss('--border','#24313f');
  if(historyChart) historyChart.destroy();
  historyChart=new Chart(ctx,{
    type:'line',
    data:{
      labels,
      datasets:[
        {label:'Top score',data:scores,borderColor:accent,backgroundColor:accent+'33',fill:true,tension:.35,pointRadius:2,pointHoverRadius:5,yAxisID:'y'},
        {label:'Signals',data:volumes,borderColor:teal,backgroundColor:teal+'22',fill:true,tension:.35,yAxisID:'y1',type:'bar',barPercentage:.65}
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{labels:{color:muted,boxWidth:12,font:{size:11}}},
        tooltip:{backgroundColor:getCss('--card2','#1c2836'),titleColor:getCss('--text','#e8e4dc'),bodyColor:muted,borderColor:border,borderWidth:1,cornerRadius:8,padding:10}
      },
      scales:{
        x:{ticks:{color:muted,font:{size:10}},grid:{color:border,drawBorder:false}},
        y:{position:'left',ticks:{color:muted,font:{size:10}},grid:{color:border,drawBorder:false}},
        y1:{position:'right',ticks:{color:muted,font:{size:10}},grid:{drawOnChartArea:false}}
      }
    }
  });
}

/* ---------- WebSocket ---------- */
let ws=null;
function connectWS(){
  try{
    ws=new WebSocket(WS);
    ws.onopen=()=>{ setWsStatus(true); };
    ws.onclose=()=>{ setWsStatus(false); setTimeout(connectWS,3000); };
    ws.onerror=()=>{ setWsStatus(false); };
    ws.onmessage=(ev)=>{
      try{
        const data=JSON.parse(ev.data);
        if(data.error){ showError(data.error); return; }
        $('singleView').classList.remove('hidden');
        $('cmpView').classList.add('hidden');
        clearStatus();
        renderSingle(data);
        const cat=$('cat').value, topic=$('topic').value.trim(), geo=$('geo').value.trim()||'CO';
        loadNarrative(topic||undefined, cat||undefined, geo);
      }catch(e){ console.error('ws message',e); }
    };
  }catch(e){ setWsStatus(false); }
}
function setWsStatus(on){
  $('wsDot').classList.toggle('on',on);
  $('wsText').textContent=on?'WS live':'WS off';
}
function analyzeWS(){
  const cat=$('cat').value, topic=$('topic').value.trim(), geo=$('geo').value.trim()||'CO';
  if(!topic && !cat){ showError('Select a category or enter a free topic.'); return; }
  if(!ws || ws.readyState!==WebSocket.OPEN){ showError('WebSocket not connected.'); return; }
  showLoading('Analyzing via WebSocket…');
  ws.send(JSON.stringify({topic:topic||undefined,category:cat||undefined,geo}));
}

/* ---------- Actions ---------- */
let cmpMode=false;
function setCompare(on){
  cmpMode=on;
  $('cmpToggle').classList.toggle('on',on);
  $('topic2Field').classList.toggle('hidden',!on);
  $('topicField').querySelector('label').textContent = on? 'Topic 1 (free/cat.)' : 'Free topic (optional)';
}

async function analyze(){
  clearStatus();
  const cat=$('cat').value, topic=$('topic').value.trim(), geo=$('geo').value.trim()||'CO';
  if(cmpMode){
    const t1=topic||cat, t2=($('topic2').value||'').trim();
    if(!t1 || !t2){ showError('Compare mode requires two topics.'); return; }
    $('singleView').classList.add('hidden');
    $('cmpView').classList.remove('hidden');
    showLoading(`Comparing "${t1}" vs "${t2}"…`);
    try{
      const [d1,d2]=await Promise.all([
        fetchTrends({topic:t1, geo}),
        fetchTrends({topic:t2, geo})
      ]);
      clearStatus();
      renderComparison(d1,d2,t1,t2);
    }catch(e){ showError(e.message+' (Is API running at '+API+'?)'); }
    return;
  }
  if(ws && ws.readyState===WebSocket.OPEN){
    analyzeWS();
    return;
  }
  $('singleView').classList.remove('hidden');
  $('cmpView').classList.add('hidden');
  if(!topic && !cat){ showError('Select a category or enter a free topic.'); return; }
  showLoading();
  try{
    const data=await fetchTrends({category:cat||undefined, topic:topic||undefined, geo});
    clearStatus();
    renderSingle(data);
    // Narrativa IA en background (no bloquea el panel de trends)
    loadNarrative(topic||undefined, cat||undefined, geo);
    loadConversation(topic||undefined, cat||undefined, geo);
  }catch(e){
    showError(e.message+' (Is API running at '+API+'?)');
    $('stats').innerHTML=''; $('gaugeWrap').innerHTML=''; $('sources').innerHTML='';
    $('hist').innerHTML=''; $('trends').innerHTML=''; $('meta').innerHTML='';
  }
}

/* ---------- Narrative (DeepSeek / OpenRouter / etc.) ---------- */
async function loadNarrative(topic, category, geo){
  const box=$('narrativeBox');
  if(!box) return;
  box.innerHTML='<div class="empty">Generating narrative…</div>';
  try{
    const p=new URLSearchParams();
    if(topic) p.set('topic', topic);
    else if(category) p.set('category', category);
    if(geo) p.set('geo', geo);
    p.set('style','executive');
    const r=await fetch(API+'/narrate?'+p.toString(), {headers: apiHeaders()});
    const j=await r.json();
    if(j.error || (j.narrative||'').startsWith('Error')){
      box.innerHTML=`<div class="error">${esc(j.narrative||'Narrative failed')}<br><small>provider: ${esc(j.provider||'')}</small></div>`;
      return;
    }
    box.innerHTML=`
      <div class="narr-meta">${esc(j.provider||'')} · ${esc(j.model||'')} · ${esc(j.style||'')}</div>
      <div class="narr-text">${esc(j.narrative||'').replace(/\n/g,'<br>')}</div>`;
  }catch(e){
    box.innerHTML=`<div class="error">${esc(e.message)}</div>`;
  }
}

/* ---------- Theme + Conversation mood ---------- */
function applyTheme(mode){
  document.documentElement.setAttribute('data-theme', mode);
  try{ localStorage.setItem('ts_theme', mode); }catch(e){}
  const btn = $('themeToggle');
  if(btn) btn.textContent = mode==='light' ? 'Dark' : 'Light';
}
function initTheme(){
  let mode='dark';
  try{ mode = localStorage.getItem('ts_theme') || 'dark'; }catch(e){}
  applyTheme(mode);
  const btn=$('themeToggle');
  if(btn) btn.addEventListener('click', ()=>{
    const cur = document.documentElement.getAttribute('data-theme')||'dark';
    applyTheme(cur==='light'?'dark':'light');
  });
}

function renderMood(mood){
  const box=$('moodBox');
  if(!box) return;
  if(!mood){ box.innerHTML='<div class="empty">Run Analyze to inspect comments</div>'; return; }
  const total = Math.max(1, mood.total||1);
  const pct = n => Math.round((n/total)*100);
  const phrases=(mood.top_phrases||[]).slice(0,3);
  box.innerHTML=`
    <div class="mood-face" aria-hidden="true">${esc(mood.emoji||'😶')}</div>
    <div>
      <div class="mood-label">${esc(mood.label||mood.mood||'')}</div>
      <div class="mood-sub">Acceptance ${((mood.acceptance_score||0)*100).toFixed(0)}% · ${mood.total||0} signals · emotion ${esc(mood.dominant_emotion||'')}</div>
      <div class="mood-bars">
        <div class="mood-row"><span>Support</span><div class="bar"><i class="sup" style="width:${pct(mood.support||0)}%"></i></div><span>${mood.support||0}</span></div>
        <div class="mood-row"><span>Against</span><div class="bar"><i class="agn" style="width:${pct(mood.against||0)}%"></i></div><span>${mood.against||0}</span></div>
        <div class="mood-row"><span>Mixed</span><div class="bar"><i class="mix" style="width:${pct(mood.mixed||0)}%"></i></div><span>${mood.mixed||0}</span></div>
        <div class="mood-row"><span>Neutral</span><div class="bar"><i class="neu" style="width:${pct(mood.neutral||0)}%"></i></div><span>${mood.neutral||0}</span></div>
      </div>
      ${phrases.length?`<div class="phrases">“${esc(phrases.join('” · “'))}”</div>`:''}
    </div>`;
}

async function loadConversation(topic, category, geo){
  const t = topic || category;
  if(!t) return;
  try{
    const p=new URLSearchParams({topic:t, limit:'6', comments_per_post:'12'});
    const r=await fetch(API+'/conversation?'+p.toString(), {headers: apiHeaders()});
    const j=await r.json();
    renderMood(j.mood);
  }catch(e){
    console.error('conversation', e);
  }
}

/* ---------- Init ---------- */
$('analizar').addEventListener('click', analyze);
$('topic').addEventListener('keydown',e=>{ if(e.key==='Enter') analyze(); });
$('topic2').addEventListener('keydown',e=>{ if(e.key==='Enter') analyze(); });
$('cat').addEventListener('change',e=>{ if(e.target.value) $('topic').value=''; });
$('cmpToggle').addEventListener('click',()=>setCompare(!cmpMode));
$('wlAdd').addEventListener('click', addWatchItem);

// Delegación de clicks del watchlist (CSP prohíbe onclick inline)
const _wl = $('watchlist');
if(_wl){
  _wl.addEventListener('click', (ev)=>{
    const btn = ev.target.closest('button[data-action]');
    if(!btn) return;
    const action = btn.getAttribute('data-action');
    const id = parseInt(btn.getAttribute('data-id'), 10);
    const topic = btn.getAttribute('data-topic') || '';
    if(action==='run' && id) runWatchItem(id);
    else if(action==='history' && topic) viewHistory(topic);
    else if(action==='delete' && id) deleteWatchItem(id);
  });
}

loadCategories();
loadWatchlist();
connectWS();
initTheme();
