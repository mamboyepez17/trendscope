/* TrendScope dashboard — sin onclick inline (CSP script-src 'self'). Multilenguaje es/en/pt. */
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
function store(k, v){ try{ if(v===undefined) return localStorage.getItem(k); localStorage.setItem(k, v); }catch(e){ return null; } }

/* ---------- Idiomas ---------- */
const I18N = {
  es: {
    tagline:'Ánimo de la gente, en tiempo real', wsTitle:'Conexión en vivo (WebSocket)', themeTitle:'Cambiar tema claro / oscuro',
    searchAria:'Buscar tema', heroTitle:'¿Cómo se siente la gente sobre…?',
    heroLead:'Mide si la gente está contenta, enojada, triste o preocupada a partir de comentarios, tweets y noticias recientes.',
    topic:'Tema', topicPh:'Ej: reforma a la salud, Bitcoin, una marca…', analyze:'Medir ánimo', compareBtn:'Comparar',
    period:'Periodo', d1:'Últimas 24 h', d3:'Últimos 3 días', d7:'Últimos 7 días', d30:'Últimos 30 días',
    orCategory:'o una categoría', none:'— ninguna —', country:'País', engine:'Motor', engineLocal:'Local (gratis)', engineClaude:'Claude (premium)',
    compareTitle:'Comparar dos temas', compare:'Comparar', topic2:'Tema 2', tryLabel:'Prueba:',
    examples:['reforma a la salud','Bitcoin','inteligencia artificial','elecciones'],
    tabMood:'Ánimo', tabTrends:'Tendencias', tabCompare:'Comparar', tabMonitor:'Monitoreo',
    welcomeTitle:'Escribe un tema y presiona «Medir ánimo»',
    welcomeText:'Leemos lo que la gente comenta en Reddit, X, YouTube y foros, y lo que dicen las noticias recientes.',
    emoTitle:'Emociones de la gente', emoSub:'Qué tanto de cada emoción hay en las opiniones (ponderado: una persona = un voto).',
    noData:'Sin datos todavía', driversTitle:'¿De qué hablan?', driversSub:'Palabras que más aparecen en cada emoción.',
    quotesTitle:'Voces de la gente', quotesSub:'Comentarios representativos de cada emoción.', noComments:'Sin comentarios todavía',
    bySourceTitle:'Ánimo por fuente', bySourceSub:'Índice neto de cada red (−100 negativo · +100 positivo).',
    aiTitle:'Resumen con IA', aiSub:'Narrativa ejecutiva generada a partir de los datos.', aiEmpty:'Aparece después de analizar',
    trendsTitle:'Lo más destacado del periodo', trendsSub:'Noticias, posts y videos recientes ordenados por relevancia y engagement.',
    trendsEmpty:'Analiza un tema para ver sus tendencias', compareEmpty:'Activa «Comparar», escribe dos temas y presiona el botón.',
    watchTitle:'Temas vigilados', watchSub:'Se analizan solos cada cierto tiempo.', watchPh:'Tema a vigilar', minutes:'minutos', add:'Añadir',
    historyTitle:'Evolución del ánimo', historySub:'mediciones · índice neto por análisis',
    steps:['Buscando noticias y posts recientes…','Leyendo comentarios de la gente…','Midiendo emociones (alegría, enojo, tristeza, miedo)…','Calculando el índice de ánimo…'],
    measuring:'Midiendo el ánimo sobre «{t}»', comparing:'Comparando «{a}» vs «{b}»',
    errNeedTopic:'Escribe un tema o elige una categoría.', errNeedTwo:'Para comparar escribe dos temas.',
    errPrefix:'No se pudo completar:', errApi:'¿está corriendo la API?',
    kicker:'La gente está', netIndex:'índice neto',
    conf:{high:'Confianza alta', medium:'Confianza media', low:'Confianza baja'},
    confTip:'Según cuántas opiniones independientes hay y qué tan ancho es el margen de error',
    polarized:'Polarizado', polarizedTip:'Hay opiniones fuertes a favor y en contra al mismo tiempo',
    scaleNeg:'−100 muy negativo', scalePos:'+100 muy positivo',
    kOpinions:'Opiniones analizadas', kOpinionsH:'{n} comentarios', kOpinionsTip:'Comentarios, respuestas y posts de personas (no titulares)',
    kPeople:'Personas distintas', kPeopleH:'cada una cuenta 1 voto', kPeopleTip:'Una cuenta que publica 20 veces cuenta como una sola persona',
    kIntensity:'Intensidad', kIntensityH:'emoción vs. neutral', kIntensityTip:'Qué tanta emoción (no neutral) hay en las opiniones',
    kPolar:'Polarización', kPolarDiv:'opinión dividida', kPolarAligned:'opinión alineada',
    kPolarTip:'0% = todos opinan igual · 100% = mitad muy a favor y mitad muy en contra',
    kMedia:'Tono de medios', kMediaH:'{n} titulares', kMediaNone:'sin noticias', kMediaTip:'Índice neto de los titulares de prensa, separado del ánimo de la gente',
    kFresh:'Frescura', kFreshDropped:'{n} viejos descartados', kFreshLast:'últimos {d} días', kFreshTip:'Edad mediana del contenido analizado',
    emo:{joy:'Alegría', sadness:'Tristeza', anger:'Enojo', fear:'Miedo', neutral:'Neutral'},
    emoTip:'{e}: {p}% del peso de {n} opiniones', notEnough:'No hay suficientes opiniones para medir emociones',
    noDrivers:'Aún no hay palabras que se repitan lo suficiente', all:'Todas', seeOriginal:'ver original ↗',
    noQuotes:'No hay comentarios representativos todavía', noBySource:'Sin opiniones por fuente',
    srcTip:'{s}: índice {v} con {n} opiniones', noTrends:'No se encontraron tendencias recientes',
    trendsMeta:'{t} · {g} · últimos {d} días · {s} fuentes · {n} señales',
    scoreTip:'Puntaje de tendencia {v}/100 (engagement + frescura + relevancia)',
    agoMin:'hace {n} min', agoH:'hace {n} h', agoD:'hace {n} día', agoDs:'hace {n} días',
    hours:'{n} h', minutesShort:'{n} min', days:'{n} días',
    opinions:'opiniones', index:'índice', noDataShort:'Sin datos',
    watchEmpty:'Aún no vigilas ningún tema', every:'cada {m} min', active:'activo', paused:'pausado',
    runNow:'Analizar ahora', viewHistory:'Ver evolución', stopWatching:'Dejar de vigilar', needWatchTopic:'Escribe un tema para vigilar',
    noHistory:'Sin mediciones todavía', signals:'señales', historyLabel:'Índice neto',
    wsOn:'En vivo', wsOff:'Sin conexión', themeLight:'☀︎ Claro', themeDark:'☾ Oscuro',
    aiGenerating:'Generando resumen…', aiDisabled:'El resumen con IA está desactivado (NARRATIVE_ENABLED=false o sin API key).',
    aiFailed:'No se pudo generar el resumen', provider:'proveedor',
    src:{reddit_comment:'Reddit (comentarios)', hackernews_comment:'HN (comentarios)', twitter_comment:'X (respuestas)', youtube_comment:'YouTube (comentarios)'},
  },
  en: {
    tagline:'How people feel, in real time', wsTitle:'Live connection (WebSocket)', themeTitle:'Toggle light / dark theme',
    searchAria:'Search topic', heroTitle:'How do people feel about…?',
    heroLead:'Measures whether people are happy, angry, sad or worried, from recent comments, posts and news.',
    topic:'Topic', topicPh:'e.g. AI regulation, Bitcoin, a brand…', analyze:'Measure mood', compareBtn:'Compare',
    period:'Period', d1:'Last 24 h', d3:'Last 3 days', d7:'Last 7 days', d30:'Last 30 days',
    orCategory:'or a category', none:'— none —', country:'Country', engine:'Engine', engineLocal:'Local (free)', engineClaude:'Claude (premium)',
    compareTitle:'Compare two topics', compare:'Compare', topic2:'Topic 2', tryLabel:'Try:',
    examples:['AI regulation','Bitcoin','electric cars','elections'],
    tabMood:'Mood', tabTrends:'Trends', tabCompare:'Compare', tabMonitor:'Monitoring',
    welcomeTitle:'Type a topic and press “Measure mood”',
    welcomeText:'We read what people say on Reddit, X, YouTube and forums, plus what recent news says.',
    emoTitle:'People’s emotions', emoSub:'How much of each emotion appears in opinions (weighted: one person = one vote).',
    noData:'No data yet', driversTitle:'What are they talking about?', driversSub:'Words that stand out in each emotion.',
    quotesTitle:'People’s voices', quotesSub:'Representative comments for each emotion.', noComments:'No comments yet',
    bySourceTitle:'Mood by source', bySourceSub:'Net index per network (−100 negative · +100 positive).',
    aiTitle:'AI summary', aiSub:'Executive narrative generated from the data.', aiEmpty:'Appears after analyzing',
    trendsTitle:'Highlights of the period', trendsSub:'Recent news, posts and videos ranked by relevance and engagement.',
    trendsEmpty:'Analyze a topic to see its trends', compareEmpty:'Turn on “Compare”, type two topics and press the button.',
    watchTitle:'Watched topics', watchSub:'Analyzed automatically on a schedule.', watchPh:'Topic to watch', minutes:'minutes', add:'Add',
    historyTitle:'Mood over time', historySub:'measurements · net index per run',
    steps:['Searching recent news and posts…','Reading people’s comments…','Measuring emotions (joy, anger, sadness, fear)…','Computing the mood index…'],
    measuring:'Measuring the mood about “{t}”', comparing:'Comparing “{a}” vs “{b}”',
    errNeedTopic:'Type a topic or pick a category.', errNeedTwo:'Type two topics to compare.',
    errPrefix:'Could not complete:', errApi:'is the API running?',
    kicker:'People are', netIndex:'net index',
    conf:{high:'High confidence', medium:'Medium confidence', low:'Low confidence'},
    confTip:'Based on how many independent opinions there are and how wide the margin of error is',
    polarized:'Polarized', polarizedTip:'Strong opinions for and against at the same time',
    scaleNeg:'−100 very negative', scalePos:'+100 very positive',
    kOpinions:'Opinions analyzed', kOpinionsH:'{n} comments', kOpinionsTip:'Comments, replies and posts by people (not headlines)',
    kPeople:'Distinct people', kPeopleH:'each counts as 1 vote', kPeopleTip:'An account posting 20 times counts as one person',
    kIntensity:'Intensity', kIntensityH:'emotion vs. neutral', kIntensityTip:'How much (non-neutral) emotion the opinions carry',
    kPolar:'Polarization', kPolarDiv:'divided opinion', kPolarAligned:'aligned opinion',
    kPolarTip:'0% = everyone agrees · 100% = half strongly for, half strongly against',
    kMedia:'Media tone', kMediaH:'{n} headlines', kMediaNone:'no news', kMediaTip:'Net index of press headlines, kept apart from people’s mood',
    kFresh:'Freshness', kFreshDropped:'{n} old items dropped', kFreshLast:'last {d} days', kFreshTip:'Median age of the analyzed content',
    emo:{joy:'Joy', sadness:'Sadness', anger:'Anger', fear:'Fear', neutral:'Neutral'},
    emoTip:'{e}: {p}% of the weight of {n} opinions', notEnough:'Not enough opinions to measure emotions',
    noDrivers:'No words repeat often enough yet', all:'All', seeOriginal:'see original ↗',
    noQuotes:'No representative comments yet', noBySource:'No opinions by source',
    srcTip:'{s}: index {v} from {n} opinions', noTrends:'No recent trends found',
    trendsMeta:'{t} · {g} · last {d} days · {s} sources · {n} signals',
    scoreTip:'Trend score {v}/100 (engagement + freshness + relevance)',
    agoMin:'{n} min ago', agoH:'{n} h ago', agoD:'{n} day ago', agoDs:'{n} days ago',
    hours:'{n} h', minutesShort:'{n} min', days:'{n} days',
    opinions:'opinions', index:'index', noDataShort:'No data',
    watchEmpty:'You are not watching any topic yet', every:'every {m} min', active:'active', paused:'paused',
    runNow:'Run now', viewHistory:'View history', stopWatching:'Stop watching', needWatchTopic:'Type a topic to watch',
    noHistory:'No measurements yet', signals:'signals', historyLabel:'Net index',
    wsOn:'Live', wsOff:'Offline', themeLight:'☀︎ Light', themeDark:'☾ Dark',
    aiGenerating:'Generating summary…', aiDisabled:'AI summary is disabled (NARRATIVE_ENABLED=false or no API key).',
    aiFailed:'Could not generate the summary', provider:'provider',
    src:{reddit_comment:'Reddit (comments)', hackernews_comment:'HN (comments)', twitter_comment:'X (replies)', youtube_comment:'YouTube (comments)'},
  },
  pt: {
    tagline:'O humor das pessoas, em tempo real', wsTitle:'Conexão ao vivo (WebSocket)', themeTitle:'Alternar tema claro / escuro',
    searchAria:'Buscar tema', heroTitle:'Como as pessoas se sentem sobre…?',
    heroLead:'Mede se as pessoas estão contentes, irritadas, tristes ou preocupadas a partir de comentários, posts e notícias recentes.',
    topic:'Tema', topicPh:'Ex.: reforma tributária, Bitcoin, uma marca…', analyze:'Medir humor', compareBtn:'Comparar',
    period:'Período', d1:'Últimas 24 h', d3:'Últimos 3 dias', d7:'Últimos 7 dias', d30:'Últimos 30 dias',
    orCategory:'ou uma categoria', none:'— nenhuma —', country:'País', engine:'Motor', engineLocal:'Local (grátis)', engineClaude:'Claude (premium)',
    compareTitle:'Comparar dois temas', compare:'Comparar', topic2:'Tema 2', tryLabel:'Experimente:',
    examples:['reforma tributária','Bitcoin','inteligência artificial','eleições'],
    tabMood:'Humor', tabTrends:'Tendências', tabCompare:'Comparar', tabMonitor:'Monitoramento',
    welcomeTitle:'Digite um tema e clique em «Medir humor»',
    welcomeText:'Lemos o que as pessoas comentam no Reddit, X, YouTube e fóruns, e o que dizem as notícias recentes.',
    emoTitle:'Emoções das pessoas', emoSub:'Quanto de cada emoção aparece nas opiniões (ponderado: uma pessoa = um voto).',
    noData:'Sem dados ainda', driversTitle:'Do que estão falando?', driversSub:'Palavras que mais aparecem em cada emoção.',
    quotesTitle:'Vozes das pessoas', quotesSub:'Comentários representativos de cada emoção.', noComments:'Sem comentários ainda',
    bySourceTitle:'Humor por fonte', bySourceSub:'Índice líquido de cada rede (−100 negativo · +100 positivo).',
    aiTitle:'Resumo com IA', aiSub:'Narrativa executiva gerada a partir dos dados.', aiEmpty:'Aparece depois de analisar',
    trendsTitle:'Destaques do período', trendsSub:'Notícias, posts e vídeos recentes ordenados por relevância e engajamento.',
    trendsEmpty:'Analise um tema para ver suas tendências', compareEmpty:'Ative «Comparar», digite dois temas e clique no botão.',
    watchTitle:'Temas monitorados', watchSub:'São analisados automaticamente de tempos em tempos.', watchPh:'Tema a monitorar', minutes:'minutos', add:'Adicionar',
    historyTitle:'Evolução do humor', historySub:'medições · índice líquido por análise',
    steps:['Buscando notícias e posts recentes…','Lendo comentários das pessoas…','Medindo emoções (alegria, raiva, tristeza, medo)…','Calculando o índice de humor…'],
    measuring:'Medindo o humor sobre «{t}»', comparing:'Comparando «{a}» vs «{b}»',
    errNeedTopic:'Digite um tema ou escolha uma categoria.', errNeedTwo:'Digite dois temas para comparar.',
    errPrefix:'Não foi possível concluir:', errApi:'a API está rodando?',
    kicker:'As pessoas estão', netIndex:'índice líquido',
    conf:{high:'Confiança alta', medium:'Confiança média', low:'Confiança baixa'},
    confTip:'Segundo quantas opiniões independentes existem e quão grande é a margem de erro',
    polarized:'Polarizado', polarizedTip:'Opiniões fortes a favor e contra ao mesmo tempo',
    scaleNeg:'−100 muito negativo', scalePos:'+100 muito positivo',
    kOpinions:'Opiniões analisadas', kOpinionsH:'{n} comentários', kOpinionsTip:'Comentários, respostas e posts de pessoas (não manchetes)',
    kPeople:'Pessoas distintas', kPeopleH:'cada uma vale 1 voto', kPeopleTip:'Uma conta que publica 20 vezes conta como uma pessoa',
    kIntensity:'Intensidade', kIntensityH:'emoção vs. neutro', kIntensityTip:'Quanta emoção (não neutra) há nas opiniões',
    kPolar:'Polarização', kPolarDiv:'opinião dividida', kPolarAligned:'opinião alinhada',
    kPolarTip:'0% = todos concordam · 100% = metade muito a favor e metade muito contra',
    kMedia:'Tom da mídia', kMediaH:'{n} manchetes', kMediaNone:'sem notícias', kMediaTip:'Índice líquido das manchetes, separado do humor das pessoas',
    kFresh:'Atualidade', kFreshDropped:'{n} antigos descartados', kFreshLast:'últimos {d} dias', kFreshTip:'Idade mediana do conteúdo analisado',
    emo:{joy:'Alegria', sadness:'Tristeza', anger:'Raiva', fear:'Medo', neutral:'Neutro'},
    emoTip:'{e}: {p}% do peso de {n} opiniões', notEnough:'Não há opiniões suficientes para medir emoções',
    noDrivers:'Ainda não há palavras que se repitam o suficiente', all:'Todas', seeOriginal:'ver original ↗',
    noQuotes:'Ainda não há comentários representativos', noBySource:'Sem opiniões por fonte',
    srcTip:'{s}: índice {v} com {n} opiniões', noTrends:'Nenhuma tendência recente encontrada',
    trendsMeta:'{t} · {g} · últimos {d} dias · {s} fontes · {n} sinais',
    scoreTip:'Pontuação de tendência {v}/100 (engajamento + atualidade + relevância)',
    agoMin:'há {n} min', agoH:'há {n} h', agoD:'há {n} dia', agoDs:'há {n} dias',
    hours:'{n} h', minutesShort:'{n} min', days:'{n} dias',
    opinions:'opiniões', index:'índice', noDataShort:'Sem dados',
    watchEmpty:'Você ainda não monitora nenhum tema', every:'a cada {m} min', active:'ativo', paused:'pausado',
    runNow:'Analisar agora', viewHistory:'Ver evolução', stopWatching:'Parar de monitorar', needWatchTopic:'Digite um tema para monitorar',
    noHistory:'Sem medições ainda', signals:'sinais', historyLabel:'Índice líquido',
    wsOn:'Ao vivo', wsOff:'Sem conexão', themeLight:'☀︎ Claro', themeDark:'☾ Escuro',
    aiGenerating:'Gerando resumo…', aiDisabled:'O resumo com IA está desativado (NARRATIVE_ENABLED=false ou sem chave de API).',
    aiFailed:'Não foi possível gerar o resumo', provider:'provedor',
    src:{reddit_comment:'Reddit (comentários)', hackernews_comment:'HN (comentários)', twitter_comment:'X (respostas)', youtube_comment:'YouTube (comentários)'},
  },
};
const LANG_DEFAULT_GEO = {es:'CO', en:'US', pt:'BR'};
let LANG = (() => {
  const saved = store('ts_lang');
  if(saved && I18N[saved]) return saved;
  const nav = (navigator.language||'en').slice(0,2).toLowerCase();
  return I18N[nav] ? nav : 'en';
})();
function t(key, vars){
  let s = key.split('.').reduce((o,k)=>o&&o[k], I18N[LANG]);
  if(s===undefined) s = key.split('.').reduce((o,k)=>o&&o[k], I18N.en);
  if(typeof s!=='string') return s===undefined ? key : s;
  return vars ? s.replace(/\{(\w+)\}/g,(m,k)=> vars[k]!=null ? vars[k] : m) : s;
}
function applyI18n(){
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i18n]').forEach(el=>{ el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-ph]').forEach(el=>{ el.placeholder = t(el.dataset.i18nPh); });
  document.querySelectorAll('[data-i18n-title]').forEach(el=>{ el.title = t(el.dataset.i18nTitle); });
  document.querySelectorAll('[data-i18n-aria]').forEach(el=>{ el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
  $('uiLang').value = LANG;
  $('analizar').textContent = cmpMode ? t('compareBtn') : t('analyze');
  renderExamples(); fillCountries(); setWsStatus(wsOn); applyTheme(store('ts_theme'));
  const none = $('cat').querySelector('option[value=""]'); if(none) none.textContent = t('none');
}

/* ---------- Países (cualquier país; nombres en el idioma elegido) ---------- */
const COUNTRIES = ('AR BO BR CA CL CO CR CU DE DO EC ES FR GB GT HN IN IT JP KR MX NI NL PA PE PH PR PT PY SV US UY VE ' +
  'AU AT BE CH CN CZ DK EG FI GR HU ID IE IL KE MA MY NG NO NZ PK PL RO RU SA SE SG TH TR TW UA VN ZA').split(' ');
function fillCountries(){
  let names = null;
  try{ names = new Intl.DisplayNames([LANG], {type:'region'}); }catch(e){}
  $('countries').innerHTML = COUNTRIES
    .map(c=>[c, names ? names.of(c) : c]).sort((a,b)=>a[1].localeCompare(b[1], LANG))
    .map(([c,n])=>`<option value="${c}">${esc(n)}</option>`).join('');
}
function defaultGeo(){
  const saved = store('ts_geo'); if(saved) return saved;
  const region = (navigator.language||'').split('-')[1];
  return (region && region.length===2) ? region.toUpperCase() : (LANG_DEFAULT_GEO[LANG]||'US');
}

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
  if(h<1) return t('agoMin',{n:Math.max(1,Math.round(h*60))});
  if(h<24) return t('agoH',{n:Math.round(h)});
  const d=Math.round(h/24);
  return t(d===1?'agoD':'agoDs',{n:d});
}
function hoursLabel(h){
  if(h==null) return '—';
  if(h<1) return t('minutesShort',{n:Math.max(1,Math.round(h*60))});
  if(h<48) return t('hours',{n:Math.round(h)});
  return t('days',{n:Math.round(h/24)});
}

/* ---------- Emociones (orden fijo = orden validado para daltonismo) ---------- */
const EMOTIONS = [
  {key:'joy', css:'--emo-joy'}, {key:'sadness', css:'--emo-sad'}, {key:'anger', css:'--emo-anger'},
  {key:'fear', css:'--emo-fear'}, {key:'neutral', css:'--emo-neutral'},
];
const EMO = Object.fromEntries(EMOTIONS.map(e=>[e.key,e]));
function emoColor(key){ return `var(${(EMO[key]||EMO.neutral).css})`; }
function emoLabel(key){ return t('emo.'+(EMO[key]?key:'neutral')); }

const SOURCE_NAMES = {
  reddit:'Reddit', twitter:'X / Twitter', tweetclaw:'X (TweetClaw)', bluesky:'Bluesky', hackernews:'Hacker News',
  youtube:'YouTube', google_news:'Google News', bing_news:'Bing News', gdelt:'GDELT', wikipedia:'Wikipedia',
  google_trends_rss:'Google Trends', google_trends_pytrends:'Google Trends', tiktok_trending:'TikTok',
  amazon_bestsellers:'Amazon', amazon:'Amazon'
};
function srcLabel(name){
  const loc = t('src.'+name);
  if(loc && loc!=='src.'+name && typeof loc==='string') return loc;
  return SOURCE_NAMES[name] || (name||'').replace(/_/g,' ');
}

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
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active', x.dataset.tab===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('hidden', p.id!=='tab-'+name));
  store('ts_tab', name);
  if(name==='monitor' && historyChart) historyChart.resize();
}
document.querySelectorAll('.tab').forEach(x=>x.addEventListener('click',()=>showTab(x.dataset.tab)));

/* ---------- Ejemplos ---------- */
function renderExamples(){
  $('examples').innerHTML = `<span class="muted" style="font-size:12px">${esc(t('tryLabel'))}</span>` +
    t('examples').map(x=>`<button type="button" class="chip-btn" data-example="${esc(x)}">${esc(x)}</button>`).join('');
}

/* ---------- Categorías ---------- */
async function loadCategories(){
  const sel = $('cat');
  try{
    const r = await fetch(API+'/categories', {headers: apiHeaders()});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const j = await r.json();
    const cats = (j && j.categories) || [];
    sel.innerHTML = `<option value="">${esc(t('none'))}</option>` +
      cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  }catch(e){
    sel.innerHTML = `<option value="">${esc(t('none'))}</option>`;
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
  p.set('lang', LANG);
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
function showLoading(msg){
  const s=$('status'); let i=0; const steps=t('steps');
  s.innerHTML=`<div class="loader"><div class="spinner"></div><div><b>${esc(msg)}</b><span id="loaderStep">${esc(steps[0])}</span></div></div>`;
  clearInterval(loaderTimer);
  loaderTimer=setInterval(()=>{ i=(i+1)%steps.length; const el=$('loaderStep'); if(el) el.textContent=steps[i]; }, 3500);
  $('analizar').disabled=true;
}
function showError(msg){
  clearInterval(loaderTimer); $('analizar').disabled=false;
  $('status').innerHTML=`<div class="error"><b>${esc(t('errPrefix'))}</b> ${esc(msg)}</div>`;
}
function clearStatus(){ clearInterval(loaderTimer); $('analizar').disabled=false; $('status').innerHTML=''; }

/* ---------- Hero del ánimo ---------- */
function meterSVG(net, margin){
  const W=400, cx=v=>((Math.max(-100,Math.min(100,v))+100)/200)*W;
  const x=cx(net), lo=cx(net-(margin||0)), hi=cx(net+(margin||0));
  const neg=getCss('--neg','#eb6834'), mid=getCss('--mid','#e6e4de'), pos=getCss('--pos','#1baf7a');
  const ink=getCss('--ink','#0b0b0b'), surf=getCss('--surface','#fcfcfb');
  return `<svg viewBox="0 0 ${W} 44" preserveAspectRatio="none" role="img" aria-label="${esc(t('netIndex'))} ${signed(net)} (−100…+100)">
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
  const key = {alta:'high',media:'medium',baja:'low'}[c] || c || 'low';
  const col={high:'var(--good)',medium:'var(--emo-joy)',low:'var(--muted)'}[key]||'var(--muted)';
  return `<span class="pill" data-tip="${esc(t('confTip'))}"><span class="dot" style="background:${col}"></span>${esc(t('conf.'+key))}</span>`;
}
let lastData=null, lastMood=null;
function renderMood(mood, topic){
  const box=$('moodBox');
  if(!box) return;
  lastMood={mood, topic};
  if(!mood){ box.innerHTML=`<div class="empty" style="grid-column:1/-1">${esc(t('noData'))}</div>`; return; }
  const n = mood.sample_size||0;
  box.innerHTML=`
    <div class="mood-face" aria-hidden="true">${esc(mood.emoji||'😶')}</div>
    <div>
      <div class="mood-kicker">${esc(t('kicker'))}${topic?` · ${esc(topic)}`:''}</div>
      <div class="mood-label">${esc(mood.label||'—')}</div>
      <p class="mood-headline">${esc(mood.headline||mood.description||'')}</p>
      ${n?`<div class="meter">
        <div class="meter-head">
          <span class="net num">${signed(mood.net_score)} <small>${esc(t('netIndex'))}${mood.margin!=null?` · ±${Math.round(mood.margin)}`:''}</small></span>
          ${confidencePill(mood.confidence)}
          ${mood.polarization>=0.35?`<span class="pill" data-tip="${esc(t('polarizedTip'))}">⚖️ ${esc(t('polarized'))}</span>`:''}
        </div>
        ${meterSVG(mood.net_score||0, mood.margin||0)}
        <div class="meter-scale"><span>${esc(t('scaleNeg'))}</span><span>0</span><span>${esc(t('scalePos'))}</span></div>
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
    kpi(t('kOpinions'), fmt(mi.sample_size||0), esc(t('kOpinionsH',{n:fmt(cm.count||0)})), t('kOpinionsTip')),
    kpi(t('kPeople'), fmt(mi.authors||0), esc(t('kPeopleH')), t('kPeopleTip')),
    kpi(t('kIntensity'), Math.round((mi.intensity||0)*100)+'%', esc(t('kIntensityH')), t('kIntensityTip')),
    kpi(t('kPolar'), polar+'%', esc(polar>=35?t('kPolarDiv'):t('kPolarAligned')), t('kPolarTip')),
    kpi(t('kMedia'), mt.n?signed(mt.net_score):'—', esc(mt.n?t('kMediaH',{n:mt.n}):t('kMediaNone')), t('kMediaTip')),
    kpi(t('kFresh'), hoursLabel(fr.median_age_hours),
        esc(fr.dropped_old?t('kFreshDropped',{n:fr.dropped_old}):t('kFreshLast',{d:fr.max_age_days||7})), t('kFreshTip')),
  ].join('');
}

/* ---------- Emociones ---------- */
function renderEmotions(mi){
  const el=$('emotions');
  const emo=(mi&&mi.emotions)||null;
  if(!emo || !mi.sample_size){ el.innerHTML=`<div class="empty">${esc(t('notEnough'))}</div>`; return; }
  const n=mi.sample_size;
  el.innerHTML = EMOTIONS.map(e=>{
    const v=emo[e.key]||0, pct=Math.round(v*100);
    return `<div class="emo-row" data-tip="${esc(t('emoTip',{e:emoLabel(e.key),p:pct,n}))}">
      <div class="emo-name"><span class="sw" style="background:var(${e.css})"></span>${esc(emoLabel(e.key))}</div>
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
  if(!rows.length){ el.innerHTML=`<div class="empty">${esc(t('noDrivers'))}</div>`; return; }
  el.innerHTML=rows.map(e=>`
    <div class="driver">
      <div class="driver-h"><span class="sw" style="width:10px;height:10px;border-radius:3px;background:var(${e.css})"></span>${esc(emoLabel(e.key))}</div>
      <div class="tags">${d[e.key].map(w=>`<span class="tag">${esc(w)}</span>`).join('')}</div>
    </div>`).join('');
}

/* ---------- Citas ---------- */
let quotesData={}, quoteFilter='all';
function renderQuotes(mi){
  quotesData=(mi&&mi.quotes)||{};
  const keys=EMOTIONS.map(e=>e.key).filter(k=>(quotesData[k]||[]).length);
  if(quoteFilter!=='all' && !keys.includes(quoteFilter)) quoteFilter='all';
  $('quoteFilters').innerHTML = keys.length ? [`<button type="button" class="chip-btn ${quoteFilter==='all'?'active':''}" data-q="all">${esc(t('all'))}</button>`]
    .concat(keys.map(k=>`<button type="button" class="chip-btn ${quoteFilter===k?'active':''}" data-q="${k}">${esc(emoLabel(k))} · ${quotesData[k].length}</button>`)).join('') : '';
  const list = (quoteFilter==='all'? keys : [quoteFilter]).flatMap(k=>(quotesData[k]||[]).map(q=>({...q,emo:k})));
  $('quotes').innerHTML = list.length ? list.map(q=>`
    <div class="quote" style="border-left-color:${emoColor(q.emo)}">
      <p>“${esc(q.text)}”</p>
      <div class="by"><span class="emo-chip"><span class="sw" style="background:${emoColor(q.emo)}"></span>${esc(emoLabel(q.emo))}</span>
        <span>${esc(srcLabel(q.source))}</span>${q.author?`<span>@${esc(q.author)}</span>`:''}
        ${q.url?`<a href="${esc(q.url)}" target="_blank" rel="noopener">${esc(t('seeOriginal'))}</a>`:''}</div>
    </div>`).join('') : `<div class="empty">${esc(t('noQuotes'))}</div>`;
}
$('quoteFilters').addEventListener('click', ev=>{
  const b=ev.target.closest('[data-q]'); if(!b) return;
  quoteFilter=b.dataset.q; renderQuotes({quotes:quotesData});
});

/* ---------- Por fuente (divergente) ---------- */
function renderBySource(mi){
  const el=$('bySource');
  const rows=Object.entries((mi&&mi.by_source)||{});
  if(!rows.length){ el.innerHTML=`<div class="empty">${esc(t('noBySource'))}</div>`; return; }
  el.innerHTML=rows.map(([src,v])=>{
    const net=Math.max(-100,Math.min(100,v.net_score||0)), w=Math.abs(net)/2;
    const style = net>=0 ? `left:50%;width:${w}%;background:var(--pos)` : `right:50%;width:${w}%;background:var(--neg)`;
    return `<div class="src-row" data-tip="${esc(t('srcTip',{s:srcLabel(src),v:signed(net),n:v.n}))}">
      <div class="src-name">${esc(srcLabel(src))}<small>${v.n}</small></div>
      <div class="div-track"><div class="div-fill" style="${style}"></div></div>
      <div class="pct num">${signed(net)}</div>
    </div>`;
  }).join('');
}

/* ---------- Tendencias ---------- */
function trendsHTML(trends, maxShow){
  const list=(trends||[]).slice(0,maxShow||30);
  if(!list.length) return `<li class="empty">${esc(t('noTrends'))}</li>`;
  return list.map((x,i)=>{
    const sc=Number(x.trend_score||0);
    const emo=(x.sentiment&&x.sentiment.emotion)||'neutral';
    const sig=x.signals||{};
    const eng=[];
    if(sig.likes) eng.push(`❤ ${fmt(sig.likes)}`);
    if(sig.retweets) eng.push(`🔁 ${fmt(sig.retweets)}`);
    if(sig.comments) eng.push(`💬 ${fmt(sig.comments)}`);
    if(sig.youtube_views) eng.push(`▶ ${fmt(sig.youtube_views)}`);
    if(sig.google_traffic) eng.push(`📈 ${esc(sig.google_traffic)}`);
    if(sig.rating) eng.push(`⭐ ${Number(sig.rating).toFixed(1)}${sig.reviews?` (${fmt(sig.reviews)})`:''}`);
    const title = x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(trunc(x.title,160))}</a>`:esc(trunc(x.title,160));
    return `<li class="trend">
      <div class="rank num">${x.rank||i+1}</div>
      <div style="min-width:0">
        <div class="trend-title">${title}</div>
        <div class="meta">
          <span class="badge">${esc(srcLabel(x.source))}</span>
          ${x.created_utc?`<span class="fresh">${esc(ago(x.created_utc))}</span>`:''}
          <span class="emo-chip"><span class="sw" style="background:${emoColor(emo)}"></span>${esc(emoLabel(emo))}</span>
          ${eng.map(e=>`<span class="num">${e}</span>`).join('')}
        </div>
      </div>
      <div class="score" data-tip="${esc(t('scoreTip',{v:sc.toFixed(1)}))}">
        <div class="track"><div class="fill" data-w="${Math.min(sc,100)}"></div></div>
        <div class="n num">${sc.toFixed(0)}</div>
      </div>
    </li>`;
  }).join('');
}
function renderTrends(data){
  const meta=data.meta||{}, q=meta.query||{}, fr=meta.freshness||{};
  $('meta').textContent = t('trendsMeta',{t:q.topic||'', g:q.geo||'', d:fr.max_age_days||7,
    s:(meta.sources_used||[]).length, n:fmt(meta.total_analyzed||0)});
  $('trends').innerHTML = trendsHTML(data.top_trends);
  $('trendsCount').textContent = (data.top_trends||[]).length;
  requestAnimationFrame(()=>document.querySelectorAll('#trends .fill').forEach(f=>{ f.style.width=f.dataset.w+'%'; }));
}

/* ---------- Render completo ---------- */
function renderSingle(data){
  lastData=data;
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
let lastCmp=null;
function cmpPanel(d, title){
  const mi=(d.meta||{}).mood_index||{};
  const emo=mi.emotions||{};
  return `<section class="card">
    <div class="cmp-head"><div class="mood-face">${esc(mi.emoji||'😶')}</div>
      <div><b>${esc(title)}</b><div class="muted">${esc(mi.label||t('noDataShort'))} · ${esc(t('index'))} <span class="num">${signed(mi.net_score||0)}</span> · ${mi.sample_size||0} ${esc(t('opinions'))}</div></div></div>
    ${mi.sample_size?meterSVG(mi.net_score||0, mi.margin||0):''}
    <div style="margin-top:10px">${EMOTIONS.map(e=>{
      const v=emo[e.key]||0;
      return `<div class="emo-row" data-tip="${esc(emoLabel(e.key))}: ${Math.round(v*100)}%">
        <div class="emo-name"><span class="sw" style="background:var(${e.css})"></span>${esc(emoLabel(e.key))}</div>
        <div class="track"><div class="fill" style="width:${(v*100).toFixed(1)}%;background:var(${e.css})"></div></div>
        <div class="pct num">${Math.round(v*100)}%</div></div>`;
    }).join('')}</div>
    <p class="sub" style="margin:10px 0 0">${esc(mi.headline||'')}</p>
  </section>`;
}
function renderComparison(d1,d2,t1,t2){
  lastCmp=[d1,d2,t1,t2];
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
  if(!watchlistItems.length){ el.innerHTML=`<div class="empty">${esc(t('watchEmpty'))}</div>`; return; }
  // Sin onclick inline: el CSP script-src 'self' los bloquea
  el.innerHTML=watchlistItems.map(item=>`
    <div class="watch-item">
      <div style="min-width:0">
        <div class="watch-topic">${esc(item.topic)}</div>
        <div class="watch-meta">${esc(item.geo)} · ${esc(t('every',{m:item.interval_minutes}))} · ${esc(item.active?t('active'):t('paused'))}</div>
      </div>
      <div class="watch-actions">
        <button type="button" class="btn sm" data-action="run" data-id="${item.id}" title="${esc(t('runNow'))}">▶</button>
        <button type="button" class="btn sm ghost" data-action="history" data-topic="${esc(item.topic)}" title="${esc(t('viewHistory'))}">📈</button>
        <button type="button" class="btn sm danger" data-action="delete" data-id="${item.id}" title="${esc(t('stopWatching'))}">✕</button>
      </div>
    </div>`).join('');
}
async function addWatchItem(){
  const topic=$('wlTopic').value.trim();
  const interval=parseInt($('wlInterval').value,10)||60;
  if(!topic){ showError(t('needWatchTopic')); return; }
  try{
    const geo=($('geo').value.trim()||'CO').toUpperCase();
    await api('POST',`/watchlist?topic=${encodeURIComponent(topic)}&interval_minutes=${interval}&geo=${encodeURIComponent(geo)}`);
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
let historyChart=null, historyRecords=[];
function recordNet(r){
  const pos=r.positive||0, neg=r.negative||0, neu=r.neutral||0;
  const tot=pos+neg+neu || r.total_signals || 1;
  return Math.round(100*(pos-neg)/tot);
}
async function viewHistory(topic){
  $('histTopic').textContent=topic;
  try{
    const j=await api('GET',`/history?topic=${encodeURIComponent(topic)}&days=30`);
    historyRecords=(j.records||[]).slice().sort((a,b)=>new Date(a.analyzed_at)-new Date(b.analyzed_at));
    $('histCount').textContent=historyRecords.length;
    renderHistoryList(historyRecords.slice().reverse());
    renderHistoryChart(historyRecords);
  }catch(e){ console.error('viewHistory',e); }
}
function renderHistoryList(records){
  if(!records.length){ $('historyList').innerHTML=`<div class="empty">${esc(t('noHistory'))}</div>`; return; }
  $('historyList').innerHTML=records.slice(0,20).map(r=>`
    <div class="history-row">
      <span>${new Date(r.analyzed_at).toLocaleString(LANG)}</span>
      <span class="num">${esc(t('index'))} <b>${signed(recordNet(r))}</b></span>
      <span class="num muted">${fmt(r.total_signals)} ${esc(t('signals'))}</span>
    </div>`).join('');
}
function renderHistoryChart(records){
  const ctx=$('historyChart').getContext('2d');
  const labels=records.map(r=>new Date(r.analyzed_at).toLocaleDateString(LANG,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}));
  const nets=records.map(recordNet);
  const ink=getCss('--ink-2','#52514e'), muted=getCss('--muted','#7a7872'), grid=getCss('--grid','#ebe9e3');
  const surface=getCss('--surface','#fcfcfb'), text=getCss('--ink','#0b0b0b');
  if(historyChart) historyChart.destroy();
  historyChart=new Chart(ctx,{
    type:'line',
    data:{labels,datasets:[{label:t('historyLabel'),data:nets,borderColor:ink,backgroundColor:ink,borderWidth:2,
      tension:.3,pointRadius:4,pointHoverRadius:6,pointBorderColor:surface,pointBorderWidth:2}]},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{display:false},
        tooltip:{backgroundColor:text,titleColor:surface,bodyColor:surface,cornerRadius:8,padding:10,displayColors:false,
          callbacks:{label:c=>`${t('historyLabel')} ${signed(c.parsed.y)} · ${fmt(records[c.dataIndex].total_signals)} ${t('signals')}`}}
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
let ws=null, wsOn=false;
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
  wsOn=on;
  $('wsDot').classList.toggle('on',on);
  $('wsText').textContent=on?t('wsOn'):t('wsOff');
}

/* ---------- Acciones ---------- */
let cmpMode=false;
function setCompare(on){
  cmpMode=on;
  const el=$('cmpToggle');
  el.classList.toggle('on',on); el.setAttribute('aria-checked', on?'true':'false');
  $('topic2Field').classList.toggle('hidden',!on);
  $('analizar').textContent = on ? t('compareBtn') : t('analyze');
}
function formValues(){
  const geo=($('geo').value.trim()||'CO').toUpperCase();
  store('ts_geo', geo);
  return { cat:$('cat').value, topic:$('topic').value.trim(), geo, days:$('days').value, engine:$('engine').value };
}

async function analyze(){
  clearStatus();
  const {cat, topic, geo, days, engine}=formValues();
  if(cmpMode){
    const t1=topic||cat, t2=($('topic2').value||'').trim();
    if(!t1 || !t2){ showError(t('errNeedTwo')); return; }
    showTab('compare');
    showLoading(t('comparing',{a:t1,b:t2}));
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
  if(!topic && !cat){ showError(t('errNeedTopic')); return; }
  showTab('mood');
  showLoading(t('measuring',{t:topic||cat}));
  if(ws && ws.readyState===WebSocket.OPEN){
    ws.send(JSON.stringify({topic:topic||undefined, category:topic?undefined:(cat||undefined), geo, days:Number(days), sentiment_engine:engine, lang:LANG}));
    return;
  }
  try{
    const data=await fetchTrends({category:topic?undefined:(cat||undefined), topic:topic||undefined, geo, days, engine});
    clearStatus();
    renderSingle(data);
    loadNarrative(topic||undefined, cat||undefined, geo);
  }catch(e){
    showError(e.message+' — '+t('errApi'));
  }
}

/* ---------- Narrativa IA ---------- */
async function loadNarrative(topic, category, geo){
  const box=$('narrativeBox');
  if(!box) return;
  box.innerHTML=`<div class="empty">${esc(t('aiGenerating'))}</div>`;
  try{
    const p=new URLSearchParams();
    if(topic) p.set('topic', topic);
    else if(category) p.set('category', category);
    if(geo) p.set('geo', geo);
    p.set('days', $('days').value||'7');
    p.set('sentiment_engine', $('engine').value||'local');
    p.set('lang', LANG);
    p.set('top_n','30');
    p.set('style','executive');
    const r=await fetch(API+'/narrate?'+p.toString(), {headers: apiHeaders()});
    const j=await r.json();
    if(j.provider==='none'){
      box.innerHTML=`<div class="empty">${esc(t('aiDisabled'))}</div>`;
      return;
    }
    if(j.error || (j.narrative||'').startsWith('Error')){
      box.innerHTML=`<div class="error">${esc(j.narrative||t('aiFailed'))}<br><small>${esc(t('provider'))}: ${esc(j.provider||'')}</small></div>`;
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
  const tp = topic || category;
  if(!tp) return;
  try{
    const p=new URLSearchParams({topic:tp, limit:'8', comments_per_post:'20', days:$('days').value||'7', lang:LANG});
    if(geo) p.set('geo', geo);
    const r=await fetch(API+'/conversation?'+p.toString(), {headers: apiHeaders()});
    const j=await r.json();
    const mi=j.mood_index;
    if(mi && mi.sample_size){
      renderMood(mi, tp); renderEmotions(mi); renderDrivers(mi); renderQuotes(mi); renderBySource(mi);
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
  if(btn) btn.textContent = currentTheme()==='dark' ? t('themeLight') : t('themeDark');
}
function currentTheme(){
  const attr=document.documentElement.getAttribute('data-theme');
  if(attr) return attr;
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
function initTheme(){
  applyTheme(store('ts_theme')); // sin preferencia guardada → sigue al sistema
  const btn=$('themeToggle');
  if(btn) btn.addEventListener('click', ()=>{
    const next = currentTheme()==='light' ? 'dark' : 'light';
    store('ts_theme', next);
    applyTheme(next);
    // Recolorear gráficos que leen tokens en JS
    const h=$('histTopic').textContent;
    if(historyChart && h && h!=='—') viewHistory(h);
    if(lastMood && lastMood.mood) renderMood(lastMood.mood, lastMood.topic);
  });
}

/* ---------- Idioma ---------- */
$('uiLang').addEventListener('change', ev=>{
  LANG = I18N[ev.target.value] ? ev.target.value : 'en';
  store('ts_lang', LANG);
  applyI18n();
  // Re-dibujar lo que ya estaba en pantalla con los textos nuevos
  if(lastData){ renderKpis(lastData.meta||{}); renderTrends(lastData); const mi=(lastData.meta||{}).mood_index;
    renderEmotions(mi); renderDrivers(mi); renderQuotes(mi); renderBySource(mi); }
  if(lastMood && lastMood.mood) renderMood(lastMood.mood, lastMood.topic);
  if(lastCmp) renderComparison(...lastCmp);
  renderWatchlist();
  if(historyRecords.length){ renderHistoryList(historyRecords.slice().reverse()); renderHistoryChart(historyRecords); }
});

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

$('geo').value = defaultGeo();
initTheme();
applyI18n();
loadCategories();
loadWatchlist();
connectWS();
{ const tab=store('ts_tab'); if(tab && tab!=='compare') showTab(tab); }
