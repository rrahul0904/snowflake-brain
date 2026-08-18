const QUESTIONS = [
  { d:'D1 · Architecture', q:'Which Snowflake architectural characteristic allows compute resources to scale independently from persisted table storage?', a:['Shared-disk warehouse nodes','Separation of storage and compute','A single cluster for all workloads','Local SSD storage on every virtual warehouse'], c:1, e:'Snowflake separates centralized storage from independently scalable virtual warehouse compute.' },
  { d:'D1 · Architecture', q:'What is the primary purpose of a Snowflake virtual warehouse?', a:['Store micro-partitions permanently','Provide compute resources for queries and data operations','Manage account-level RBAC','Publish listings to Marketplace'], c:1, e:'A virtual warehouse supplies compute. Persisted table data is stored separately.' },
  { d:'D1 · Architecture', q:'How does Snowflake physically organize table data in its storage layer?', a:['User-managed partitions','Micro-partitions managed automatically','One file per table','B-tree pages'], c:1, e:'Snowflake automatically stores table data in immutable micro-partitions and maintains metadata about them.' },
  { d:'D1 · Architecture', q:'When an identical query can reuse a valid persisted result, which mechanism can avoid recomputing the query?', a:['Result cache','Resource monitor','Snowpipe','Fail-safe'], c:0, e:'The persisted query result cache can return a prior valid result when reuse conditions are satisfied.' },
  { d:'D2 · Governance', q:'Which design principle most directly supports limiting a role to only the privileges it needs?', a:['Data sharing','Least privilege','Auto-suspend','Clustering'], c:1, e:'Least privilege reduces unnecessary access by granting only what a role requires.' },
  { d:'D2 · Governance', q:'Which feature can dynamically obscure sensitive values based on policy logic?', a:['Masking policy','File format','Stream','Warehouse scaling policy'], c:0, e:'Dynamic data masking uses masking policies to control how values are presented.' },
  { d:'D2 · Governance', q:'What is a resource monitor primarily used to control?', a:['Role hierarchy depth','Virtual warehouse credit consumption','Data retention period','Stage encryption keys'], c:1, e:'Resource monitors help track and control credit usage for warehouses.' },
  { d:'D2 · Governance', q:'Which Snowflake capability is designed to access historical table states within the configured retention window?', a:['Time Travel','Search Optimization','Snowpipe','Secure Data Sharing'], c:0, e:'Time Travel provides historical data access and recovery capabilities within the retention period.' },
  { d:'D3 · Loading', q:'In Snowflake, what is a stage primarily used for?', a:['Holding files for data loading/unloading workflows','Assigning object ownership','Caching query results','Scaling clusters automatically'], c:0, e:'Stages are locations used to reference files for loading and unloading data.' },
  { d:'D3 · Loading', q:'Which command is commonly used to load staged files into a Snowflake table?', a:['COPY INTO','GRANT OWNERSHIP','ALTER WAREHOUSE','CREATE STREAM'], c:0, e:'COPY INTO <table> loads data from a stage into a target table.' },
  { d:'D3 · Loading', q:'Which feature supports continuous file ingestion when new files arrive in cloud storage?', a:['Snowpipe','Result cache','Time Travel','Materialized view'], c:0, e:'Snowpipe supports automated continuous ingestion of newly arriving files.' },
  { d:'D3 · Loading', q:'Why define a FILE FORMAT object?', a:['To centralize parsing rules for staged data files','To reserve warehouse credits','To define row access permissions','To cluster a table'], c:0, e:'FILE FORMAT objects capture reusable parsing settings such as type, delimiter, compression and header behavior.' },
  { d:'D3 · Loading', q:'What is a storage integration designed to improve?', a:['Secure access from Snowflake to external cloud storage','Query result caching','Role inheritance','Automatic clustering'], c:0, e:'Storage integrations provide a managed security model for access to external cloud storage.' },
  { d:'D4 · Performance', q:'When would a clustering key be most relevant?', a:['For every small table by default','When very large tables have selective filters and natural clustering is insufficient','To enable Time Travel','To create a role hierarchy'], c:1, e:'Clustering keys can help large tables when pruning on important access patterns is poor enough to justify maintenance cost.' },
  { d:'D4 · Performance', q:'Which interface is most useful for examining where a query spent time across operators?', a:['Query Profile','Marketplace','Resource monitor only','Network policy'], c:0, e:'Query Profile exposes execution operators and timing information useful for diagnosis.' },
  { d:'D4 · Performance', q:'What is the main reason to use a multi-cluster warehouse?', a:['Increase table retention','Handle higher concurrent query demand','Create database clones','Replace file formats'], c:1, e:'Multi-cluster warehouses scale out compute clusters primarily to address concurrency.' },
  { d:'D4 · Transformation', q:'What does a stream primarily track?', a:['Table change data for incremental processing','User login attempts','Warehouse credits','Stage file formats'], c:0, e:'Streams expose change tracking information that can be consumed by downstream incremental workflows.' },
  { d:'D4 · Transformation', q:'What does a task primarily provide?', a:['Scheduled or triggered SQL execution','Long-term table storage','Account authentication','Data marketplace listings'], c:0, e:'Tasks automate SQL execution on a schedule or through task graph dependencies/triggers.' },
  { d:'D5 · Collaboration', q:'What is a key characteristic of Secure Data Sharing?', a:['The consumer must copy all shared data into its account','Data can be shared without creating another stored copy for the consumer','Only CSV files can be shared','It requires the same virtual warehouse'], c:1, e:'Secure Data Sharing lets consumers query shared data without a traditional data-copy workflow.' },
  { d:'D5 · Collaboration', q:'What is Snowflake Marketplace used for?', a:['Discovering and accessing published data/apps/listings','Changing micro-partition size','Managing local passwords only','Replacing virtual warehouses'], c:0, e:'Marketplace is a discovery and distribution channel for listings such as data products and applications.' }
];

let state = { i: 0, answers: Array(QUESTIONS.length).fill(null), score: 0, rating: 0 };

function renderQ() {
  const q = QUESTIONS[state.i];
  const qLabel = document.getElementById('qLabel');
  if (!qLabel) return;
  qLabel.textContent = `Question ${state.i + 1} of ${QUESTIONS.length}`;
  document.getElementById('qDomain').textContent = q.d;
  document.getElementById('qText').textContent = q.q;
  document.getElementById('qProgress').style.width = `${((state.i + 1) / QUESTIONS.length) * 100}%`;

  const root = document.getElementById('answers');
  root.innerHTML = '';
  q.a.forEach((txt, idx) => {
    const button = document.createElement('button');
    button.className = 'answer';
    button.type = 'button';
    button.innerHTML = `<b>${String.fromCharCode(65 + idx)}</b><span>${txt}</span>`;
    if (state.answers[state.i] !== null) {
      button.disabled = true;
      if (idx === q.c) button.classList.add('correct');
      if (idx === state.answers[state.i] && idx !== q.c) button.classList.add('wrong');
    }
    button.addEventListener('click', () => answer(idx));
    root.appendChild(button);
  });

  const explain = document.getElementById('explain');
  if (state.answers[state.i] !== null) {
    explain.textContent = q.e;
    explain.classList.add('show');
  } else {
    explain.textContent = '';
    explain.classList.remove('show');
  }

  document.getElementById('prevQ').disabled = state.i === 0;
  document.getElementById('nextQ').textContent = state.i === QUESTIONS.length - 1 ? 'Finish' : 'Next →';
  renderSide();
}

function answer(idx) {
  if (state.answers[state.i] !== null) return;
  state.answers[state.i] = idx;
  if (idx === QUESTIONS[state.i].c) state.score += 1;
  renderQ();
  if (state.answers.every((value) => value !== null)) {
    window.setTimeout(() => openFeedback('Completed 20-question practice'), 650);
  }
}

function renderSide() {
  const answeredCount = state.answers.filter((value) => value !== null).length;
  document.getElementById('score').textContent = state.score;
  document.getElementById('answered').textContent = answeredCount;
  document.getElementById('dashScore').textContent = `${state.score}/${QUESTIONS.length}`;
  document.getElementById('dashAnswered').textContent = answeredCount;
  const jump = document.getElementById('jump');
  jump.innerHTML = '';
  QUESTIONS.forEach((_, idx) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = idx + 1;
    button.setAttribute('aria-label', `Go to question ${idx + 1}`);
    if (idx === state.i) button.classList.add('current');
    else if (state.answers[idx] !== null) button.classList.add('done');
    button.addEventListener('click', () => {
      state.i = idx;
      renderQ();
      document.querySelector('.question-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    jump.appendChild(button);
  });
}

document.getElementById('prevQ')?.addEventListener('click', () => {
  if (state.i > 0) { state.i -= 1; renderQ(); }
});
document.getElementById('nextQ')?.addEventListener('click', () => {
  if (state.i < QUESTIONS.length - 1) { state.i += 1; renderQ(); }
  else openFeedback('Finished practice');
});
document.getElementById('restart')?.addEventListener('click', () => {
  state = { ...state, i: 0, answers: Array(QUESTIONS.length).fill(null), score: 0 };
  renderQ();
});

function route() {
  const id = (location.hash || '#home').slice(1).split('?')[0];
  document.querySelectorAll('.route').forEach((node) => node.classList.toggle('active', node.id === id));
  document.querySelectorAll('.nav a, .mobile-nav a').forEach((anchor) => anchor.classList.toggle('active', anchor.getAttribute('href') === `#${id}`));
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);
route();
renderQ();

const themeBtn = document.getElementById('themeBtn');
const savedTheme = localStorage.getItem('snowflake-beta-theme');
if (savedTheme === 'light' || savedTheme === 'dark') document.documentElement.dataset.theme = savedTheme;
themeBtn?.addEventListener('click', () => {
  const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = nextTheme;
  localStorage.setItem('snowflake-beta-theme', nextTheme);
  drawGlobe();
});

function openFeedback(context = '') {
  document.getElementById('feedbackContext').value = context;
  document.getElementById('feedbackBack').classList.add('open');
}
function closeFeedback() { document.getElementById('feedbackBack').classList.remove('open'); }
function openLauncher() { document.getElementById('launcherBack').classList.add('open'); }
function closeLauncher() { document.getElementById('launcherBack').classList.remove('open'); }
function go(id) { closeLauncher(); location.hash = id; }
window.openFeedback = openFeedback;
window.closeFeedback = closeFeedback;
window.openLauncher = openLauncher;
window.closeLauncher = closeLauncher;
window.go = go;

document.querySelectorAll('#rating button').forEach((button) => {
  button.addEventListener('click', () => {
    state.rating = Number(button.dataset.v);
    document.querySelectorAll('#rating button').forEach((candidate) => candidate.classList.toggle('on', Number(candidate.dataset.v) <= state.rating));
  });
});

document.getElementById('feedbackForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = document.getElementById('feedbackStatus');
  const formData = new FormData(event.currentTarget);
  const payload = {
    rating: state.rating || null,
    area: formData.get('area'),
    message: String(formData.get('message') || '').slice(0, 3000),
    email: String(formData.get('email') || '').slice(0, 320),
    context: formData.get('context'),
    route: location.hash || '#home',
    theme: document.documentElement.dataset.theme,
    viewport: `${innerWidth}x${innerHeight}`,
    created_at: new Date().toISOString(),
  };
  status.textContent = 'Sending…';
  try {
    const response = await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!response.ok) throw new Error('Feedback request failed');
    status.textContent = 'Thank you — feedback received.';
    event.currentTarget.reset();
    state.rating = 0;
    document.querySelectorAll('#rating button').forEach((button) => button.classList.remove('on'));
  } catch {
    const rows = JSON.parse(localStorage.getItem('snowflake-beta-feedback') || '[]');
    rows.push(payload);
    localStorage.setItem('snowflake-beta-feedback', JSON.stringify(rows.slice(-50)));
    status.textContent = 'Saved on this device. Please try again when online.';
  }
});

const DEG = Math.PI / 180;
const WORLD_GEOMETRY_URL = './world-major-land.geojson';
const ROTATION_PERIOD_MS = 56000;
const AUTO_DEGREES_PER_MS = 360 / ROTATION_PERIOD_MS;
const canvas = document.getElementById('globe');
const ctx = canvas?.getContext('2d');
let globePolygons = [];
let globeLandDots = [];
let globeCenterLon = -24;
let globeCenterLat = 12;
let globeSize = 440;
let globeDpr = Math.min(window.devicePixelRatio || 1, 2);
let globeDragging = false;
let globePointerId = null;
let globeLastX = 0;
let globeLastY = 0;
let globeResumeAfter = 0;
let globeLastFrame = performance.now();

function css(name, fallback) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback; }
function projectPoint(latDeg, lonDeg, radius, center) {
  const lat = latDeg * DEG;
  const lat0 = globeCenterLat * DEG;
  const delta = (lonDeg - globeCenterLon) * DEG;
  const sinLat = Math.sin(lat);
  const cosLat = Math.cos(lat);
  const sin0 = Math.sin(lat0);
  const cos0 = Math.cos(lat0);
  const depth = sin0 * sinLat + cos0 * cosLat * Math.cos(delta);
  return {
    x: center + radius * cosLat * Math.sin(delta),
    y: center - radius * (cos0 * sinLat - sin0 * cosLat * Math.cos(delta)),
    depth,
    visible: depth > 0,
  };
}
function polygonsFromGeometry(geometry) {
  if (!geometry) return [];
  const raw = geometry.type === 'Polygon' ? [geometry.coordinates || []] : geometry.type === 'MultiPolygon' ? geometry.coordinates || [] : [];
  return raw.map((rings) => {
    const outer = rings[0] || [];
    const lons = outer.map((point) => point[0]);
    const lats = outer.map((point) => point[1]);
    return { rings, minLon: Math.min(...lons), maxLon: Math.max(...lons), minLat: Math.min(...lats), maxLat: Math.max(...lats) };
  }).filter((polygon) => polygon.rings[0]?.length > 2);
}
function pointInRing(lon, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0]; const yi = ring[i][1]; const xj = ring[j][0]; const yj = ring[j][1];
    const crosses = ((yi > lat) !== (yj > lat)) && (lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi);
    if (crosses) inside = !inside;
  }
  return inside;
}
function isLand(lon, lat, polygons) {
  for (const polygon of polygons) {
    if (lat < polygon.minLat || lat > polygon.maxLat || lon < polygon.minLon || lon > polygon.maxLon) continue;
    if (!pointInRing(lon, lat, polygon.rings[0])) continue;
    let inHole = false;
    for (let h = 1; h < polygon.rings.length; h += 1) {
      if (pointInRing(lon, lat, polygon.rings[h])) { inHole = true; break; }
    }
    if (!inHole) return true;
  }
  return false;
}
function buildLandDots(polygons) {
  const dots = [];
  const latStep = 2.75;
  for (let lat = -79; lat <= 82; lat += latStep) {
    const lonStep = 2.75 / Math.max(.72, Math.cos(lat * DEG));
    for (let lon = -180; lon < 180; lon += lonStep) if (isLand(lon, lat, polygons)) dots.push({ lat, lon });
  }
  return dots;
}
function colorMix(hex, alpha) {
  if (!hex.startsWith('#')) return hex;
  const h = hex.slice(1);
  const n = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const value = Number.parseInt(n, 16);
  return `rgba(${(value >> 16) & 255},${(value >> 8) & 255},${value & 255},${alpha})`;
}
function drawProjectedLine(points, radius, center, strokeStyle, lineWidth = 1) {
  let segment = [];
  const flush = () => {
    if (segment.length >= 2) {
      ctx.beginPath();
      ctx.moveTo(segment[0].x, segment[0].y);
      for (let i = 1; i < segment.length; i += 1) ctx.lineTo(segment[i].x, segment[i].y);
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }
    segment = [];
  };
  for (const coord of points) {
    const point = projectPoint(coord[1], coord[0], radius, center);
    if (point.visible) segment.push(point); else flush();
  }
  flush();
}
function drawGraticule(radius, center) {
  const grid = colorMix(css('--line', '#233b57'), .42);
  for (let lat = -60; lat <= 60; lat += 30) {
    const points = [];
    for (let lon = -180; lon <= 180; lon += 4) points.push([lon, lat]);
    drawProjectedLine(points, radius, center, grid, .6);
  }
  for (let lon = -180; lon < 180; lon += 30) {
    const points = [];
    for (let lat = -88; lat <= 88; lat += 4) points.push([lon, lat]);
    drawProjectedLine(points, radius, center, grid, .6);
  }
}
function resizeGlobe() {
  if (!canvas || !ctx) return;
  const rect = canvas.getBoundingClientRect();
  globeSize = Math.max(250, Math.round(rect.width || 440));
  globeDpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(globeSize * globeDpr);
  canvas.height = Math.round(globeSize * globeDpr);
  ctx.setTransform(globeDpr, 0, 0, globeDpr, 0, 0);
  drawGlobe();
}
function drawGlobe() {
  if (!canvas || !ctx) return;
  const center = globeSize / 2;
  const radius = globeSize * .455;
  ctx.clearRect(0, 0, globeSize, globeSize);
  const shade = ctx.createRadialGradient(center - radius * .34, center - radius * .34, radius * .05, center, center, radius);
  const light = document.documentElement.dataset.theme === 'light';
  shade.addColorStop(0, light ? 'rgba(255,255,255,.92)' : 'rgba(88,231,255,.075)');
  shade.addColorStop(.72, light ? 'rgba(8,127,210,.035)' : 'rgba(36,153,255,.025)');
  shade.addColorStop(1, light ? 'rgba(8,31,51,.12)' : 'rgba(0,0,0,.32)');
  ctx.beginPath(); ctx.arc(center, center, radius, 0, Math.PI * 2); ctx.fillStyle = shade; ctx.fill();
  ctx.save();
  ctx.beginPath(); ctx.arc(center, center, radius - .5, 0, Math.PI * 2); ctx.clip();
  drawGraticule(radius, center);
  const landDot = light ? 'rgba(8,127,210,.60)' : 'rgba(88,231,255,.66)';
  const baseDot = Math.max(.85, Math.min(1.5, globeSize / 360));
  for (const dot of globeLandDots) {
    const point = projectPoint(dot.lat, dot.lon, radius, center);
    if (!point.visible || point.depth < .015) continue;
    ctx.globalAlpha = Math.min(1, .24 + point.depth * .84);
    ctx.fillStyle = landDot;
    ctx.beginPath(); ctx.arc(point.x, point.y, baseDot * (.74 + point.depth * .34), 0, Math.PI * 2); ctx.fill();
  }
  ctx.globalAlpha = 1;
  const coastline = light ? 'rgba(103,86,217,.24)' : 'rgba(139,124,255,.25)';
  for (const polygon of globePolygons) for (const ring of polygon.rings) drawProjectedLine(ring, radius, center, coastline, .48);
  ctx.restore();
  ctx.beginPath(); ctx.arc(center, center, radius, 0, Math.PI * 2); ctx.strokeStyle = colorMix(css('--line', '#233b57'), .75); ctx.lineWidth = .85; ctx.stroke();
}
async function loadGlobeGeometry() {
  if (!canvas) return;
  try {
    const response = await fetch(WORLD_GEOMETRY_URL, { cache: 'force-cache' });
    if (!response.ok) throw new Error('World geometry unavailable');
    const world = await response.json();
    globePolygons = polygonsFromGeometry(world.geometry);
    globeLandDots = buildLandDots(globePolygons);
    drawGlobe();
  } catch (error) {
    console.error('Unable to load world geometry', error);
    const label = document.querySelector('.globe-label');
    if (label) label.innerHTML = '<i></i>World geometry unavailable';
  }
}
function animateGlobe(now) {
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true;
  const elapsed = Math.min(80, now - globeLastFrame);
  globeLastFrame = now;
  if (!reduceMotion && !document.hidden && !globeDragging && now >= globeResumeAfter) {
    globeCenterLon = ((globeCenterLon + elapsed * AUTO_DEGREES_PER_MS + 540) % 360) - 180;
    drawGlobe();
  }
  requestAnimationFrame(animateGlobe);
}
if (canvas) {
  canvas.addEventListener('pointerdown', (event) => {
    globeDragging = true;
    globePointerId = event.pointerId;
    globeLastX = event.clientX;
    globeLastY = event.clientY;
    globeResumeAfter = Number.POSITIVE_INFINITY;
    canvas.setPointerCapture?.(globePointerId);
  });
  canvas.addEventListener('pointermove', (event) => {
    if (!globeDragging || event.pointerId !== globePointerId) return;
    const dx = event.clientX - globeLastX;
    const dy = event.clientY - globeLastY;
    globeCenterLon -= dx * .33;
    globeCenterLat = Math.max(-55, Math.min(55, globeCenterLat + dy * .20));
    globeLastX = event.clientX;
    globeLastY = event.clientY;
    drawGlobe();
  });
  const endDrag = (event) => {
    if (!globeDragging || (event.pointerId != null && event.pointerId !== globePointerId)) return;
    globeDragging = false;
    globePointerId = null;
    globeResumeAfter = performance.now() + 1800;
  };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  const observer = new ResizeObserver(resizeGlobe);
  observer.observe(canvas);
  resizeGlobe();
  loadGlobeGeometry();
  requestAnimationFrame(animateGlobe);
}
