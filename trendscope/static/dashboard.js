/* TrendScope dashboard — sin onclick inline (CSP script-src 'self'). */
const API = ''; // mismo origen
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

function getCss(v, fb){
  return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || fb;
}
function esc(s){ return (s==null?'':String(s)).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function trunc(s,n){ s=s||''; return s.length>n? s.slice(0,n-1)+'…':s; }
function fmt(n){
  if(n==null) return '—';
  n=Number(n);
  if(n>=1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'')+'M';
  if(n>=1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'')+'K';
  return String(Math.round(n));
}
function signed(n){ n=Math.round(Number(n)||0); return (n>0?'+':'')+n; }
function ago(ts){
  if(!ts) return '';
  const h=(Date.now()/1000-Number(ts))/3600;
  if(h<1) return 'hace '+Math.max(1,Math.round(h*60))+' min';
  if(h<24) return 'hace '+Math.round(h)+' h';
  const d=Math.round(h/24);
  return 'hace '+d+(d===1?' día':' días');
}
function hoursLabel(h){
  if(h==null) return '—';
  if(h<1) return Math.max(1,Math.round(h*60))+' min';
  if(h<48) return Math.round(h)+' h';
  return Math.round(h/24)+' días';
}

/* ---------- Emociones (orden fijo = orden validado para daltonismo) ---------- */
const EMOTIONS = [
  {key:'joy',     label:'Alegría',  css:'--emo-joy'},
  {key:'sadness', label:'Tristeza', css:'--emo-sad'},
  {key:'anger',   label:'Enojo',    css:'--emo-anger'},
  {key:'fear',    label:'Miedo',    css:'--emo-fear'},
  {key:'neutral', label:'Neutral',  css:'--emo-neutral'},
];
const EMO = Object.fromEntries(EMOTIONS.map(e=>[e.key,e]));
function emoColor(key){ return `var(${(EMO[key]||EMO.neutral).css})`; }
function emoLabel(key){ return (EMO[key]||EMO.neutral).label; }

const SOURCE_NAMES = {
  reddit:'Reddit', reddit_comment:'Reddit (comentarios)', twitter:'X / Twitter', twitter_comment:'X (respuestas)',
  tweetclaw:'X (TweetClaw)', bluesky:'Bluesky', hackernews:'Hacker News', hackernews_comment:'HN (comentarios)',
  youtube:'YouTube', google_news:'Google News', bing_news:'Bing News', gdelt:'GDELT', wikipedia:'Wikipedia',
  google_trends_rss:'Google Trends', google_trends_pytrends:'Google Trends', tiktok_trending:'TikTok',
  amazon_bestsellers:'Amazon'
};
function srcLabel(name){ return SOURCE_NAMES[name] || (name||'').replace(/_/g,' '); }

/* ---------- Tooltip ---------- */
const tip = $('tip');
document.addEventListener('mousemove', ev=>{
  const el = ev.target.closest && ev.target.closest('[data-tip]');
  if(!el){ tip.classList.remove('show'); return; }
  tip.textContent = el.getAttribute('data-tip');
  tip.classList.add('show');
  const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  const y = Math.min(ev.clientY + 14, window.innerHeight - tip.offsetHeight - 8);
  tip.style.left = x+'px'; tip.style.top = y+'px';
});

/* ---------- Pestañas ---------- */
function showTab(name){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('hidden', p.id!=='tab-'+name));
  try{ localStorage.setItem('ts_tab', name); }catch(e){}
  if(name==='monitor' && historyChart) historyChart.resize();
}
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>showTab(t.dataset.tab)));

/* ---------- Categorías ---------- */
async function loadCategories(){
  const sel = $('cat');
  try{
    const r = await fetch(API+'/categories', {headers: apiHeaders()});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const j = await r.json();
    const cats = (j && j.categories) || [];
    sel.innerHTML = '<option value="">— ninguna —</option>' +
      cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  }catch(e){
    sel.innerHTML = '<option value="">— ninguna —</option>' +
      ['tecnologia','economia','salud','moda','deportes','politica','emprendimiento','educacion','inmobiliario','crypto']
      .map(c=>`<option value="${c}">${c}</option>`).join('');
  }
}

/* ---------- Fetch ---------- */
async function fetchTrends({category, topic, geo='CO', days, engine}){
  const p = new URLSearchParams();
  if(topic) p.set('topic', topic);
  else if(category) p.set('category', category);
  if(geo) p.set('geo', geo);
  if(days) p.set('days', days);
  if(engine) p.set('sentiment_engine', engine);
  p.set('top_n','30');
  const r = await fetch(API+'/trends?'+p.toString(), {headers: apiHeaders()});
  if(!r.ok){
    let msg='HTTP '+r.status;
    try{ const e=await r.json(); msg=e.detail||msg; }catch(_){}
    throw new Error(typeof msg==='string'?msg:JSON.stringify(msg));
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

/* ---------- Estado ---------- */
let loaderTimer=null;
const STEPS=['Buscando noticias y posts recientes…','Leyendo comentarios de la gente…','Midiendo emociones (alegría, enojo, tristeza, miedo)…','Calculando el índice de ánimo…'];
function showLoading(msg){
  const s=$('status'); let i=0;
  s.innerHTML=`<div class="loader"><div class="spinner"></div><div><b>${esc(msg||'Analizando…')}</b><span id="loaderStep">${STEPS[0]}</span></div></div>`;
  clearInterval(loaderTimer);
  loaderTimer=setInterval(()=>{ i=(i+1)%STEPS.length; const el=$('loaderStep'); if(el) el.textContent=STEPS[i]; }, 3500);
  $('analizar').disabled=true;
}
function showError(msg){
  clearInterval(loaderTimer); $('analizar').disabled=false;
  $('status').innerHTML=`<div class="error"><b>No se pudo completar:</b> ${esc(msg)}</div>`;
}
function clearStatus(){ clearInterval(loaderTimer); $('analizar').disabled=false; $('status').innerHTML=''; }

/* ---------- Hero del ánimo ---------- */
function meterSVG(net, margin){
  const W=400, cx=v=>((Math.max(-100,Math.min(100,v))+100)/200)*W;
  const x=cx(net), lo=cx(net-(margin||0)), hi=cx(net+(margin||0));
  const neg=getCss('--neg','#eb6834'), mid=getCss('--mid','#e6e4de'), pos=getCss('--pos','#1baf7a');
  const ink=getCss('--ink','#0b0b0b'), surf=getCss('--surface','#fcfcfb');
  return `<svg viewBox="0 0 ${W} 44" preserveAspectRatio="none" role="img" aria-label="Índice neto ${signed(net)} de −100 a +100">
    <defs><linearGradient id="dg" x1="0" x2="1">
      <stop offset="0" stop-color="${neg}"/><stop offset=".5" stop-color="${mid}"/><stop offset="1" stop-color="${pos}"/>
    </linearGradient></defs>
    <rect x="0" y="16" width="${W}" height="12" rx="4" fill="url(#dg)"/>
    <line x1="${W/2}" x2="${W/2}" y1="12" y2="32" stroke="${surf}" stroke-width="2"/>
    ${margin?`<rect x="${lo}" y="12" width="${Math.max(2,hi-lo)}" height="20" rx="4" fill="${ink}" opacity=".12"/>`:''}
    <rect x="${x-3}" y="6" width="6" height="32" rx="3" fill="${ink}" stroke="${surf}" stroke-width="2"/>
  </svg>`;
}
function confidencePill(c){
  const txt={alta:'Confianza alta',media:'Confianza media',baja:'Confianza baja'}[c]||'Confianza baja';
  const col={alta:'var(--good)',media:'var(--emo-joy)',baja:'var(--muted)'}[c]||'var(--muted)';
  return `<span class="pill" data-tip="Según cuántas opiniones independientes hay y qué tan ancho es el margen de error"><span class="dot" style="background:${col}"></span>${txt}</span>`;
}
function renderMood(mood, topic){
  const box=$('moodBox');
  if(!box) return;
  if(!mood){ box.innerHTML='<div class="empty" style="grid-column:1/-1">Sin datos de ánimo</div>'; return; }
  const n = mood.sample_size||0;
  box.innerHTML=`
    <div class="mood-face" aria-hidden="true">${esc(mood.emoji||'😶')}</div>
    <div>
      <div class="mood-kicker">La gente está${topic?` · ${esc(topic)}`:''}</div>
      <div class="mood-label">${esc(mood.label||'—')}</div>
      <p class="mood-headline">${esc(mood.headline||mood.description||'')}</p>
      ${n?`<div class="meter">
        <div class="meter-head">
          <span class="net num">${signed(mood.net_score)} <small>índice neto${mood.margin!=null?` · ±${Math.round(mood.margin)}`:''}</small></span>
          ${confidencePill(mood.confidence)}
          ${mood.polarization>=0.35?`<span class="pill" data-tip="Hay opiniones fuertes a favor y en contra al mismo tiempo">⚖️ Polarizado</span>`:''}
        </div>
        ${meterSVG(mood.net_score||0, mood.margin||0)}
        <div class="meter-scale"><span>−100 muy negativo</span><span>0</span><span>+100 muy positivo</span></div>
      </div>`:''}
    </div>`;
}

function kpi(k, v, h, tipText){
  return `<div class="kpi"${tipText?` data-tip="${esc(tipText)}"`:''}><div class="k">${esc(k)}</div><div class="v num">${v}</div>${h?`<div class="h">${h}</div>`:''}</div>`;
}
function renderKpis(meta){
  const mi=meta.mood_index||{}, mt=meta.media_tone||{}, fr=meta.freshness||{}, cm=meta.comments||{};
  const polar=Math.round((mi.polarization||0)*100);
  $('kpis').innerHTML = [
    kpi('Opiniones analizadas', fmt(mi.sample_size||0), `${fmt(cm.count||0)} comentarios`, 'Comentarios, respuestas y posts de personas (no titulares)'),
    kpi('Personas distintas', fmt(mi.authors||0), 'cada una cuenta 1 voto', 'Una cuenta que publica 20 veces cuenta como una sola persona'),
    kpi('Intensidad', Math.round((mi.intensity||0)*100)+'%', 'emoción vs. neutral', 'Qué tanta emoción (no neutral) hay en las opiniones'),
    kpi('Polarización', polar+'%', polar>=35?'opinión dividida':'opinión alineada', '0% = todos opinan igual · 100% = mitad muy a favor y mitad muy en contra'),
    kpi('Tono de medios', mt.n?signed(mt.net_score):'—', mt.n?`${mt.n} titulares · ${esc(mt.label)}`:'sin noticias', 'Índice neto de los titulares de prensa, separado del ánimo de la gente'),
    kpi('Frescura', hoursLabel(fr.median_age_hours), fr.dropped_old?`${fr.dropped_old} viejos descartados`:`últimos ${fr.max_age_days||7} días`, 'Edad mediana del contenido analizado'),
  ].join('');
}

/* ---------- Emociones ---------- */
function renderEmotions(mi){
  const el=$('emotions');
  const emo=(mi&&mi.emotions)||null;
  if(!emo || !mi.sample_size){ el.innerHTML='<div class="empty">No hay suficientes opiniones para medir emociones</div>'; return; }
  const n=mi.sample_size;
  el.innerHTML = EMOTIONS.map(e=>{
    const v=emo[e.key]||0, pct=Math.round(v*100);
    return `<div class="emo-row" data-tip="${e.label}: ${pct}% del peso de ${n} opiniones">
      <div class="emo-name"><span class="sw" style="background:var(${e.css})"></span>${e.label}</div>
      <div class="track"><div class="fill" data-w="${(v*100).toFixed(1)}" style="background:var(${e.css})"></div></div>
      <div class="pct num">${pct}%</div>
    </div>`;
  }).join('');
  requestAnimationFrame(()=>el.querySelectorAll('.fill').forEach(f=>{ f.style.width=f.dataset.w+'%'; }));
}
function renderDrivers(mi){
  const el=$('drivers');
  const d=(mi&&mi.drivers)||{};
  const rows=EMOTIONS.filter(e=>(d[e.key]||[]).length);
  if(!rows.length){ el.innerHTML='<div class="empty">Aún no hay palabras que se repitan lo suficiente</div>'; return; }
  el.innerHTML=rows.map(e=>`
    <div class="driver">
      <div class="driver-h"><span class="sw" style="width:10px;height:10px;border-radius:3px;background:var(${e.css})"></span>${e.label}</div>
      <div class="tags">${d[e.key].map(w=>`<span class="tag">${esc(w)}</span>`).join('')}</div>
    </div>`).join('');
}

/* ---------- Citas ---------- */
let quotesData={}, quoteFilter='all';
function renderQuotes(mi){
  quotesData=(mi&&mi.quotes)||{};
  const keys=EMOTIONS.map(e=>e.key).filter(k=>(quotesData[k]||[]).length);
  if(quoteFilter!=='all' && !keys.includes(quoteFilter)) quoteFilter='all';
  $('quoteFilters').innerHTML = keys.length ? [`<button type="button" class="chip-btn ${quoteFilter==='all'?'active':''}" data-q="all">Todas</button>`]
    .concat(keys.map(k=>`<button type="button" class="chip-btn ${quoteFilter===k?'active':''}" data-q="${k}">${emoLabel(k)} · ${quotesData[k].length}</button>`)).join('') : '';
  const list = (quoteFilter==='all'? keys : [quoteFilter]).flatMap(k=>(quotesData[k]||[]).map(q=>({...q,emo:k})));
  $('quotes').innerHTML = list.length ? list.map(q=>`
    <div class="quote" style="border-left-color:${emoColor(q.emo)}">
      <p>“${esc(q.text)}”</p>
      <div class="by"><span class="emo-chip"><span class="sw" style="background:${emoColor(q.emo)}"></span>${emoLabel(q.emo)}</span>
        <span>${esc(srcLabel(q.source))}</span>${q.author?`<span>@${esc(q.author)}</span>`:''}
        ${q.url?`<a href="${esc(q.url)}" target="_blank" rel="noopener">ver original ↗</a>`:''}</div>
    </div>`).join('') : '<div class="empty">No hay comentarios representativos todavía</div>';
}
$('quoteFilters').addEventListener('click', ev=>{
  const b=ev.target.closest('[data-q]'); if(!b) return;
  quoteFilter=b.dataset.q; renderQuotes({quotes:quotesData});
});

/* ---------- Por fuente (divergente) ---------- */
function renderBySource(mi){
  const el=$('bySource');
  const rows=Object.entries((mi&&mi.by_source)||{});
  if(!rows.length){ el.innerHTML='<div class="empty">Sin opiniones por fuente</div>'; return; }
  el.innerHTML=rows.map(([src,v])=>{
    const net=Math.max(-100,Math.min(100,v.net_score||0)), w=Math.abs(net)/2;
    const style = net>=0 ? `left:50%;width:${w}%;background:var(--pos)` : `right:50%;width:${w}%;background:var(--neg)`;
    return `<div class="src-row" data-tip="${esc(srcLabel(src))}: índice ${signed(net)} con ${v.n} opiniones">
      <div class="src-name">${esc(srcLabel(src))}<small>${v.n}</small></div>
      <div class="div-track"><div class="div-fill" style="${style}"></div></div>
      <div class="pct num">${signed(net)}</div>
    </div>`;
  }).join('');
}

/* ---------- Tendencias ---------- */
function trendsHTML(trends, maxShow){
  const list=(trends||[]).slice(0,maxShow||30);
  if(!list.length) return '<li class="empty">No se encontraron tendencias recientes</li>';
  return list.map((t,i)=>{
    const sc=Number(t.trend_score||0);
    const emo=(t.sentiment&&t.sentiment.emotion)||'neutral';
    const sig=t.signals||{};
    const eng=[];
    if(sig.likes) eng.push(`❤ ${fmt(sig.likes)}`);
    if(sig.retweets) eng.push(`🔁 ${fmt(sig.retweets)}`);
    if(sig.comments) eng.push(`💬 ${fmt(sig.comments)}`);
    if(sig.youtube_views) eng.push(`▶ ${fmt(sig.youtube_views)}`);
    if(sig.google_traffic) eng.push(`📈 ${esc(sig.google_traffic)}`);
    const title = t.url?`<a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(trunc(t.title,160))}</a>`:esc(trunc(t.title,160));
    return `<li class="trend">
      <div class="rank num">${t.rank||i+1}</div>
      <div style="min-width:0">
        <div class="trend-title">${title}</div>
        <div class="meta">
          <span class="badge">${esc(srcLabel(t.source))}</span>
          ${t.created_utc?`<span class="fresh">${ago(t.created_utc)}</span>`:''}
          <span class="emo-chip"><span class="sw" style="background:${emoColor(emo)}"></span>${emoLabel(emo)}</span>
          ${eng.map(x=>`<span class="num">${x}</span>`).join('')}
        </div>
      </div>
      <div class="score" data-tip="Puntaje de tendencia ${sc.toFixed(1)}/100 (engagement + frescura + relevancia)">
        <div class="track"><div class="fill" data-w="${Math.min(sc,100)}"></div></div>
        <div class="n num">${sc.toFixed(0)}</div>
      </div>
    </li>`;
  }).join('');
}
function renderTrends(data){
  const meta=data.meta||{}, q=meta.query||{}, fr=meta.freshness||{};
  $('meta').innerHTML = `${esc(q.topic||'')} · ${esc(q.geo||'CO')} · últimos ${fr.max_age_days||7} días · ${(meta.sources_used||[]).length} fuentes · ${fmt(meta.total_analyzed||0)} señales`;
  $('trends').innerHTML = trendsHTML(data.top_trends);
  $('trendsCount').textContent = (data.top_trends||[]).length;
  requestAnimationFrame(()=>document.querySelectorAll('#trends .fill').forEach(f=>{ f.style.width=f.dataset.w+'%'; }));
}

/* ---------- Render completo ---------- */
function renderSingle(data){
  const meta=data.meta||{}, mi=meta.mood_index;
  const topic=(meta.query||{}).topic;
  renderMood(mi, topic);
  renderKpis(meta);
  renderEmotions(mi);
  renderDrivers(mi);
  renderQuotes(mi);
  renderBySource(mi);
  renderTrends(data);
  // Sin opiniones en /trends (p. ej. recolección desactivada) → /conversation
  if(!mi || !mi.sample_size) loadConversation(topic, undefined, (meta.query||{}).geo);
}

/* ---------- Comparación ---------- */
function cmpPanel(d, title){
  const mi=(d.meta||{}).mood_index||{};
  const emo=mi.emotions||{};
  return `<section class="card">
    <div class="cmp-head"><div class="mood-face">${esc(mi.emoji||'😶')}</div>
      <div><b>${esc(title)}</b><div class="muted">${esc(mi.label||'Sin datos')} · índice <span class="num">${signed(mi.net_score||0)}</span> · ${mi.sample_size||0} opiniones</div></div></div>
    ${mi.sample_size?meterSVG(mi.net_score||0, mi.margin||0):''}
    <div style="margin-top:10px">${EMOTIONS.map(e=>{
      const v=emo[e.key]||0;
      return `<div class="emo-row" data-tip="${e.label}: ${Math.round(v*100)}%">
        <div class="emo-name"><span class="sw" style="background:var(${e.css})"></span>${e.label}</div>
        <div class="track"><div class="fill" style="width:${(v*100).toFixed(1)}%;background:var(${e.css})"></div></div>
        <div class="pct num">${Math.round(v*100)}%</div></div>`;
    }).join('')}</div>
    <p class="sub" style="margin:10px 0 0">${esc(mi.headline||'')}</p>
  </section>`;
}
function renderComparison(d1,d2,t1,t2){
  $('cmpPanels').innerHTML = cmpPanel(d1,t1)+cmpPanel(d2,t2);
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
  if(!watchlistItems.length){ el.innerHTML='<div class="empty">Aún no vigilas ningún tema</div>'; return; }
  // Sin onclick inline: el CSP script-src 'self' los bloquea
  el.innerHTML=watchlistItems.map(item=>`
    <div class="watch-item">
      <div style="min-width:0">
        <div class="watch-topic">${esc(item.topic)}</div>
        <div class="watch-meta">${esc(item.geo)} · cada ${item.interval_minutes} min · ${item.active?'activo':'pausado'}</div>
      </div>
      <div class="watch-actions">
        <button type="button" class="btn sm" data-action="run" data-id="${item.id}" title="Analizar ahora">▶</button>
        <button type="button" class="btn sm ghost" data-action="history" data-topic="${esc(item.topic)}" title="Ver evolución">📈</button>
        <button type="button" class="btn sm danger" data-action="delete" data-id="${item.id}" title="Dejar de vigilar">✕</button>
      </div>
    </div>`).join('');
}
async function addWatchItem(){
  const topic=$('wlTopic').value.trim();
  const interval=parseInt($('wlInterval').value,10)||60;
  if(!topic){ showError('Escribe un tema para vigilar'); return; }
  try{
    await api('POST',`/watchlist?topic=${encodeURIComponent(topic)}&interval_minutes=${interval}`);
    $('wlTopic').value='';
    await loadWatchlist();
  }catch(e){ showError(e.message); }
}
async function deleteWatchItem(id){
  try{ await api('DELETE',`/watchlist/${id}`); await loadWatchlist(); }
  catch(e){ showError(e.message); }
}
async function runWatchItem(id){
  try{
    await api('POST',`/watchlist/${id}/run`);
    await loadWatchlist();
    const item=watchlistItems.find(x=>x.id===id);
    if(item) viewHistory(item.topic);
  }catch(e){ showError(e.message); }
}

/* ---------- Historial: un solo eje (índice neto −100…+100) ---------- */
let historyChart=null;
function recordNet(r){
  const pos=r.positive||0, neg=r.negative||0, neu=r.neutral||0;
  const tot=pos+neg+neu || r.total_signals || 1;
  return Math.round(100*(pos-neg)/tot);
}
async function viewHistory(topic){
  $('histTopic').textContent=topic;
  try{
    const j=await api('GET',`/history?topic=${encodeURIComponent(topic)}&days=30`);
    const records=(j.records||[]).slice().sort((a,b)=>new Date(a.analyzed_at)-new Date(b.analyzed_at));
    $('histCount').textContent=records.length;
    renderHistoryList(records.slice().reverse());
    renderHistoryChart(records);
  }catch(e){ console.error('viewHistory',e); }
}
function renderHistoryList(records){
  if(!records.length){ $('historyList').innerHTML='<div class="empty">Sin mediciones todavía</div>'; return; }
  $('historyList').innerHTML=records.slice(0,20).map(r=>`
    <div class="history-row">
      <span>${new Date(r.analyzed_at).toLocaleString()}</span>
      <span class="num">índice <b>${signed(recordNet(r))}</b></span>
      <span class="num muted">${fmt(r.total_signals)} señales</span>
    </div>`).join('');
}
function renderHistoryChart(records){
  const ctx=$('historyChart').getContext('2d');
  const labels=records.map(r=>new Date(r.analyzed_at).toLocaleDateString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}));
  const nets=records.map(recordNet);
  const ink=getCss('--ink-2','#52514e'), muted=getCss('--muted','#7a7872'), grid=getCss('--grid','#ebe9e3');
  const surface=getCss('--surface','#fcfcfb'), text=getCss('--ink','#0b0b0b');
  if(historyChart) historyChart.destroy();
  historyChart=new Chart(ctx,{
    type:'line',
    data:{labels,datasets:[{label:'Índice neto',data:nets,borderColor:ink,backgroundColor:ink,borderWidth:2,
      tension:.3,pointRadius:4,pointHoverRadius:6,pointBorderColor:surface,pointBorderWidth:2}]},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{display:false},
        tooltip:{backgroundColor:text,titleColor:surface,bodyColor:surface,cornerRadius:8,padding:10,displayColors:false,
          callbacks:{label:c=>`Índice neto ${signed(c.parsed.y)} · ${fmt(records[c.dataIndex].total_signals)} señales`}}
      },
      scales:{
        x:{ticks:{color:muted,font:{size:10},maxRotation:0,autoSkip:true},grid:{display:false},border:{color:grid}},
        y:{min:-100,max:100,ticks:{color:muted,font:{size:10},stepSize:50},
           grid:{color:c=>c.tick.value===0?muted:grid,lineWidth:1},border:{display:false}}
      }
    }
  });
}

/* ---------- WebSocket ---------- */
let ws=null;
function connectWS(){
  try{
    ws=new WebSocket(WS);
    ws.onopen=()=>setWsStatus(true);
    ws.onclose=()=>{ setWsStatus(false); setTimeout(connectWS,4000); };
    ws.onerror=()=>setWsStatus(false);
    ws.onmessage=(ev)=>{
      try{
        const data=JSON.parse(ev.data);
        if(data.error){ showError(data.error); return; }
        clearStatus();
        renderSingle(data);
        const {topic,cat,geo}=formValues();
        loadNarrative(topic||undefined, cat||undefined, geo);
      }catch(e){ console.error('ws message',e); }
    };
  }catch(e){ setWsStatus(false); }
}
function setWsStatus(on){
  $('wsDot').classList.toggle('on',on);
  $('wsText').textContent=on?'En vivo':'Sin conexión';
}

/* ---------- Acciones ---------- */
let cmpMode=false;
function setCompare(on){
  cmpMode=on;
  const t=$('cmpToggle');
  t.classList.toggle('on',on); t.setAttribute('aria-checked', on?'true':'false');
  $('topic2Field').classList.toggle('hidden',!on);
  $('analizar').textContent = on ? 'Comparar' : 'Medir ánimo';
}
function formValues(){
  return {
    cat:$('cat').value, topic:$('topic').value.trim(),
    geo:($('geo').value.trim()||'CO').toUpperCase(),
    days:$('days').value, engine:$('engine').value,
  };
}

async function analyze(){
  clearStatus();
  const {cat, topic, geo, days, engine}=formValues();
  if(cmpMode){
    const t1=topic||cat, t2=($('topic2').value||'').trim();
    if(!t1 || !t2){ showError('Para comparar escribe dos temas.'); return; }
    showTab('compare');
    showLoading(`Comparando «${t1}» vs «${t2}»`);
    try{
      const [d1,d2]=await Promise.all([
        fetchTrends({topic:t1, geo, days, engine}),
        fetchTrends({topic:t2, geo, days, engine}),
      ]);
      clearStatus();
      renderComparison(d1,d2,t1,t2);
    }catch(e){ showError(e.message); }
    return;
  }
  if(!topic && !cat){ showError('Escribe un tema o elige una categoría.'); return; }
  showTab('mood');
  if(ws && ws.readyState===WebSocket.OPEN){
    showLoading(`Midiendo el ánimo sobre «${topic||cat}»`);
    ws.send(JSON.stringify({topic:topic||undefined, category:topic?undefined:(cat||undefined), geo, days:Number(days), sentiment_engine:engine}));
    return;
  }
  showLoading(`Midiendo el ánimo sobre «${topic||cat}»`);
  try{
    const data=await fetchTrends({category:topic?undefined:(cat||undefined), topic:topic||undefined, geo, days, engine});
    clearStatus();
    renderSingle(data);
    loadNarrative(topic||undefined, cat||undefined, geo);
  }catch(e){
    showError(e.message+' — ¿está corriendo la API?');
  }
}

/* ---------- Narrativa IA ---------- */
async function loadNarrative(topic, category, geo){
  const box=$('narrativeBox');
  if(!box) return;
  box.innerHTML='<div class="empty">Generando resumen…</div>';
  try{
    const p=new URLSearchParams();
    if(topic) p.set('topic', topic);
    else if(category) p.set('category', category);
    if(geo) p.set('geo', geo);
    p.set('days', $('days').value||'7');
    p.set('sentiment_engine', $('engine').value||'local');
    p.set('top_n','30');
    p.set('style','executive');
    const r=await fetch(API+'/narrate?'+p.toString(), {headers: apiHeaders()});
    const j=await r.json();
    if(j.provider==='none'){
      box.innerHTML='<div class="empty">El resumen con IA está desactivado (NARRATIVE_ENABLED=false o sin API key).</div>';
      return;
    }
    if(j.error || (j.narrative||'').startsWith('Error')){
      box.innerHTML=`<div class="error">${esc(j.narrative||'No se pudo generar el resumen')}<br><small>proveedor: ${esc(j.provider||'')}</small></div>`;
      return;
    }
    box.innerHTML=`
      <div class="narr-meta">${esc(j.provider||'')} · ${esc(j.model||'')}</div>
      <div class="narr-text">${esc(j.narrative||'').replace(/\n/g,'<br>')}</div>`;
  }catch(e){
    box.innerHTML=`<div class="error">${esc(e.message)}</div>`;
  }
}

/* ---------- Conversación (respaldo si /trends no trajo opiniones) ---------- */
async function loadConversation(topic, category, geo){
  const t = topic || category;
  if(!t) return;
  try{
    const p=new URLSearchParams({topic:t, limit:'8', comments_per_post:'20', days:$('days').value||'7'});
    const r=await fetch(API+'/conversation?'+p.toString(), {headers: apiHeaders()});
    const j=await r.json();
    const mi=j.mood_index;
    if(mi && mi.sample_size){
      renderMood(mi, t); renderEmotions(mi); renderDrivers(mi); renderQuotes(mi); renderBySource(mi);
    }
  }catch(e){
    console.error('conversation', e);
  }
}

/* ---------- Tema ---------- */
function applyTheme(mode){
  if(mode==='light' || mode==='dark') document.documentElement.setAttribute('data-theme', mode);
  else document.documentElement.removeAttribute('data-theme');
  const btn=$('themeToggle');
  if(btn) btn.textContent = currentTheme()==='dark' ? '☀︎ Claro' : '☾ Oscuro';
}
function currentTheme(){
  const attr=document.documentElement.getAttribute('data-theme');
  if(attr) return attr;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
function initTheme(){
  let mode=null;
  try{ mode = localStorage.getItem('ts_theme'); }catch(e){}
  applyTheme(mode); // sin preferencia guardada → sigue al sistema
  const btn=$('themeToggle');
  if(btn) btn.addEventListener('click', ()=>{
    const next = currentTheme()==='light' ? 'dark' : 'light';
    try{ localStorage.setItem('ts_theme', next); }catch(e){}
    applyTheme(next);
    // Recolorear gráficos que leen tokens en JS
    const h=$('histTopic').textContent;
    if(historyChart && h && h!=='—') viewHistory(h);
  });
}

/* ---------- Init ---------- */
$('analizar').addEventListener('click', analyze);
$('topic').addEventListener('keydown',e=>{ if(e.key==='Enter') analyze(); });
$('topic2').addEventListener('keydown',e=>{ if(e.key==='Enter') analyze(); });
$('cat').addEventListener('change',e=>{ if(e.target.value) $('topic').value=''; });
$('cmpToggle').addEventListener('click',()=>setCompare(!cmpMode));
$('cmpToggle').addEventListener('keydown',e=>{ if(e.key===' '||e.key==='Enter'){ e.preventDefault(); setCompare(!cmpMode); } });
$('wlAdd').addEventListener('click', addWatchItem);
$('examples').addEventListener('click', ev=>{
  const b=ev.target.closest('[data-example]'); if(!b) return;
  $('topic').value=b.dataset.example; $('cat').value=''; analyze();
});

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

initTheme();
loadCategories();
loadWatchlist();
connectWS();
try{ const t=localStorage.getItem('ts_tab'); if(t && t!=='compare') showTab(t); }catch(e){}
