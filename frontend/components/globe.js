import { getGlobeActivity } from "../api.js";

const DEG = Math.PI / 180;
const WORLD_GEOMETRY_URL = "/static/assets/world-major-land.geojson";
const ROTATION_PERIOD_MS = 78000;
const AUTO_DEGREES_PER_MS = 360 / ROTATION_PERIOD_MS;

const LANDMARKS = [
  { label: "NEW ZEALAND", lat: -41.2, lon: 174.7, dx: -42, dy: -10 },
  { label: "AUSTRALIA", lat: -25.3, lon: 133.8, dx: 38, dy: -8 },
  { label: "SINGAPORE", lat: 1.35, lon: 103.82, dx: 44, dy: -2 },
  { label: "MALAYSIA", lat: 4.2, lon: 102.0, dx: -48, dy: 14 },
  { label: "INDIA", lat: 21.1, lon: 78.9, dx: 46, dy: 0 },
  { label: "VIETNAM", lat: 14.05, lon: 108.28, dx: 44, dy: 4 },
  { label: "PAKISTAN", lat: 30.4, lon: 69.35, dx: 44, dy: 8 },
  { label: "TAIWAN", lat: 23.7, lon: 121.0, dx: 42, dy: -4 },
  { label: "KYRGYZSTAN", lat: 41.2, lon: 74.8, dx: 50, dy: 6 },
  { label: "JAPAN & KOREA", lat: 36.1, lon: 135.2, dx: -58, dy: 12 },
  { label: "INDONESIA", lat: -2.5, lon: 118.0, dx: 48, dy: 10 },
  { label: "PHILIPPINES", lat: 12.8, lon: 122.7, dx: 48, dy: -10 },
  { label: "BRAZIL", lat: -14.2, lon: -51.9, dx: 46, dy: 8 },
  { label: "NETHERLANDS", lat: 52.13, lon: 5.29, dx: 46, dy: 10 },
  { label: "CANADA", lat: 56.13, lon: -106.35, dx: 48, dy: -4 },
  { label: "UNITED STATES", lat: 39.5, lon: -98.35, dx: 58, dy: 7, radius: 2.8, halo: 7.8 },
  { label: "MEXICO", lat: 23.63, lon: -102.55, dx: 44, dy: 6 },
  { label: "COSTA RICA", lat: 9.75, lon: -83.75, dx: 48, dy: 6 },
];

function project(latDeg, lonDeg, centerLatDeg, centerLonDeg, radius, center) {
  const lat = latDeg * DEG;
  const lat0 = centerLatDeg * DEG;
  const delta = (lonDeg - centerLonDeg) * DEG;
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
  const raw = geometry.type === "Polygon" ? [geometry.coordinates || []] : geometry.type === "MultiPolygon" ? geometry.coordinates || [] : [];
  return raw.map((rings) => {
    const outer = rings[0] || [];
    const lons = outer.map((point) => point[0]);
    const lats = outer.map((point) => point[1]);
    return {
      rings,
      minLon: Math.min(...lons), maxLon: Math.max(...lons),
      minLat: Math.min(...lats), maxLat: Math.max(...lats),
    };
  }).filter((polygon) => polygon.rings[0]?.length > 2);
}

function pointInRing(lon, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    const crosses = ((yi > lat) !== (yj > lat)) && (lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-12) + xi);
    if (crosses) inside = !inside;
  }
  return inside;
}

function isLand(lon, lat, polygons) {
  for (const polygon of polygons) {
    if (lat < polygon.minLat || lat > polygon.maxLat || lon < polygon.minLon || lon > polygon.maxLon) continue;
    if (!pointInRing(lon, lat, polygon.rings[0])) continue;
    if (!polygon.rings.slice(1).some((ring) => pointInRing(lon, lat, ring))) return true;
  }
  return false;
}

function buildLandDots(polygons) {
  const dots = [];
  const latStep = 2.35;
  for (let lat = -78; lat <= 82; lat += latStep) {
    const lonStep = 2.35 / Math.max(0.68, Math.cos(lat * DEG));
    for (let lon = -180; lon < 180; lon += lonStep) if (isLand(lon, lat, polygons)) dots.push({ lat, lon });
  }
  return dots;
}

function overlaps(a, b, pad = 5) {
  return !(a.right + pad < b.left || b.right + pad < a.left || a.bottom + pad < b.top || b.bottom + pad < a.top);
}

export function renderActivityGlobe(container) {
  if (!container) return () => {};
  container.innerHTML = `
    <figure class="v26-globe-wrap" role="img" aria-label="Rotating dotted globe with geographic labels. Privacy-safe live learner activity is shown only when available.">
      <div class="v26-globe" data-globe>
        <canvas class="v26-globe-canvas" data-globe-canvas aria-hidden="true"></canvas>
        <div class="v26-globe-points" data-globe-points aria-hidden="true"></div>
      </div>
      <figcaption class="v26-globe-caption" data-globe-caption><span class="v26-live-dot"></span><span>Snowflake certification study, worldwide</span></figcaption>
    </figure>`;

  const globe = container.querySelector("[data-globe]");
  const canvas = container.querySelector("[data-globe-canvas]");
  const ctx = canvas.getContext("2d");
  const pointsRoot = container.querySelector("[data-globe-points]");
  const caption = container.querySelector("[data-globe-caption] span:last-child");
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;

  let polygons = [];
  let landDots = [];
  let activity = [];
  let activityNodes = [];
  let centerLon = 123;
  let centerLat = -8;
  let size = 410;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);
  let dragging = false;
  let pointerId = null;
  let lastX = 0;
  let lastY = 0;
  let resumeAfter = 0;
  let raf = 0;
  let lastFrame = performance.now();
  let disposed = false;

  const projection = (lat, lon) => project(lat, lon, centerLat, centerLon, size * 0.43, size / 2);

  function resize() {
    const rect = globe.getBoundingClientRect();
    size = Math.max(260, Math.round(rect.width || 410));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  function drawSphere() {
    const center = size / 2;
    const radius = size * 0.43;
    ctx.clearRect(0, 0, size, size);

    ctx.save();
    ctx.shadowColor = "rgba(128,166,211,.34)";
    ctx.shadowBlur = Math.max(16, size * 0.045);
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(145,177,214,.17)";
    ctx.lineWidth = 1.1;
    ctx.stroke();
    ctx.restore();

    const shade = ctx.createRadialGradient(center - radius * 0.38, center - radius * 0.42, radius * 0.06, center, center, radius);
    shade.addColorStop(0, "rgba(17,20,25,.94)");
    shade.addColorStop(0.56, "rgba(8,10,13,.99)");
    shade.addColorStop(0.84, "rgba(3,5,8,1)");
    shade.addColorStop(1, "rgba(0,1,3,1)");
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.fillStyle = shade;
    ctx.fill();

    ctx.save();
    ctx.beginPath();
    ctx.arc(center, center, radius - 1, 0, Math.PI * 2);
    ctx.clip();

    const baseDot = Math.max(0.7, Math.min(1.18, size / 430));
    for (const dot of landDots) {
      const p = projection(dot.lat, dot.lon);
      if (!p.visible || p.depth < 0.02) continue;
      ctx.globalAlpha = Math.min(0.78, 0.12 + p.depth * 0.64);
      ctx.beginPath();
      ctx.arc(p.x, p.y, baseDot * (0.72 + p.depth * 0.30), 0, Math.PI * 2);
      ctx.fillStyle = "rgba(210,216,226,.9)";
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.restore();

    const rim = ctx.createRadialGradient(center, center, radius * 0.74, center, center, radius * 1.04);
    rim.addColorStop(0, "rgba(0,0,0,0)");
    rim.addColorStop(0.88, "rgba(82,115,151,.015)");
    rim.addColorStop(1, "rgba(118,151,192,.16)");
    ctx.beginPath();
    ctx.arc(center, center, radius * 1.04, 0, Math.PI * 2);
    ctx.fillStyle = rim;
    ctx.fill();
  }

  function drawLabels() {
    const candidates = LANDMARKS.map((item) => ({ item, p: projection(item.lat, item.lon) }))
      .filter(({ p }) => p.visible && p.depth > 0.22)
      .sort((a, b) => b.p.depth - a.p.depth);
    const occupied = [];
    ctx.save();
    ctx.font = `${Math.max(7, Math.round(size / 58))}px Inter, ui-sans-serif, system-ui, sans-serif`;
    ctx.textBaseline = "middle";
    for (const { item, p } of candidates) {
      const alpha = Math.min(1, 0.42 + p.depth * 0.68);
      const labelX = p.x + item.dx;
      const labelY = p.y + item.dy;
      const width = ctx.measureText(item.label).width;
      const left = item.dx >= 0 ? labelX + 8 : labelX - width - 8;
      const box = { left, right: left + width, top: labelY - 7, bottom: labelY + 7 };
      if (occupied.some((other) => overlaps(box, other, 6))) continue;
      occupied.push(box);

      ctx.globalAlpha = alpha;
      const anchorRadius = item.radius || Math.max(1.7, size / 180);
      const haloRadius = item.halo || Math.max(4, size / 96);
      ctx.beginPath();
      ctx.arc(p.x, p.y, anchorRadius, 0, Math.PI * 2);
      ctx.fillStyle = "#ef9778";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(p.x, p.y, haloRadius, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(239,151,120,.22)";
      ctx.lineWidth = 1;
      ctx.stroke();

      const endX = item.dx >= 0 ? labelX + 4 : labelX - 4;
      ctx.beginPath();
      ctx.moveTo(p.x + (item.dx >= 0 ? 5 : -5), p.y);
      ctx.lineTo(endX, labelY);
      ctx.strokeStyle = "rgba(225,229,236,.34)";
      ctx.lineWidth = 0.65;
      ctx.stroke();

      ctx.fillStyle = "rgba(239,240,244,.92)";
      ctx.fillText(item.label, left, labelY);
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  function placeActivity() {
    activityNodes.forEach((row) => {
      const p = projection(row.item.lat, row.item.lon);
      if (!p.visible || p.depth < 0.08) { row.node.hidden = true; return; }
      row.node.hidden = false;
      row.node.style.left = `${p.x}px`;
      row.node.style.top = `${p.y}px`;
      row.node.style.opacity = String(Math.min(1, 0.28 + p.depth * 0.62));
      row.node.style.transform = `translate(-50%,-50%) scale(${0.72 + p.depth * 0.18})`;
    });
  }

  function draw() {
    if (!ctx) return;
    drawSphere();
    drawLabels();
    placeActivity();
  }

  function tick(now) {
    if (disposed) return;
    const elapsed = Math.min(80, now - lastFrame);
    lastFrame = now;
    if (!document.hidden && !reduceMotion && !dragging && now >= resumeAfter) {
      centerLon = ((centerLon + elapsed * AUTO_DEGREES_PER_MS + 540) % 360) - 180;
      draw();
    }
    raf = requestAnimationFrame(tick);
  }

  function renderActivityNodes() {
    pointsRoot.innerHTML = "";
    activityNodes = activity.map((item) => {
      const node = document.createElement("span");
      node.className = "v26-globe-point v26-globe-point-live";
      node.innerHTML = `<i></i>`;
      pointsRoot.appendChild(node);
      return { item, node };
    });
  }

  async function loadData() {
    const [worldResult, activityResult] = await Promise.allSettled([
      fetch(WORLD_GEOMETRY_URL, { cache: "force-cache" }).then((response) => {
        if (!response.ok) throw new Error("World geometry unavailable");
        return response.json();
      }),
      getGlobeActivity(),
    ]);
    if (worldResult.status === "fulfilled") {
      polygons = polygonsFromGeometry(worldResult.value.geometry);
      landDots = buildLandDots(polygons);
    }
    if (activityResult.status === "fulfilled") {
      activity = Array.isArray(activityResult.value.locations) ? activityResult.value.locations : [];
      const live = activityResult.value.mode === "live" && activity.length > 0;
      caption.textContent = live
        ? `${activityResult.value.active_total} learners active in the last ${activityResult.value.window_minutes} minutes`
        : "Snowflake certification study, worldwide";
      container.querySelector(".v26-live-dot")?.classList.toggle("is-live", live);
    }
    renderActivityNodes();
    draw();
  }

  function begin(event) {
    dragging = true;
    pointerId = event.pointerId;
    lastX = event.clientX;
    lastY = event.clientY;
    resumeAfter = Number.POSITIVE_INFINITY;
    globe.classList.add("is-dragging");
    globe.setPointerCapture?.(pointerId);
  }
  function move(event) {
    if (!dragging || event.pointerId !== pointerId) return;
    const dx = event.clientX - lastX;
    const dy = event.clientY - lastY;
    centerLon -= dx * 0.31;
    centerLat = Math.max(-52, Math.min(52, centerLat + dy * 0.18));
    lastX = event.clientX;
    lastY = event.clientY;
    draw();
  }
  function end(event) {
    if (!dragging || (event.pointerId != null && event.pointerId !== pointerId)) return;
    dragging = false;
    pointerId = null;
    resumeAfter = performance.now() + 2200;
    globe.classList.remove("is-dragging");
  }

  globe.addEventListener("pointerdown", begin);
  globe.addEventListener("pointermove", move);
  globe.addEventListener("pointerup", end);
  globe.addEventListener("pointercancel", end);
  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(globe);
  const onVisibility = () => { lastFrame = performance.now(); };
  document.addEventListener("visibilitychange", onVisibility);

  resize();
  loadData();
  if (!reduceMotion) raf = requestAnimationFrame(tick);

  return () => {
    disposed = true;
    cancelAnimationFrame(raf);
    resizeObserver.disconnect();
    document.removeEventListener("visibilitychange", onVisibility);
    globe.removeEventListener("pointerdown", begin);
    globe.removeEventListener("pointermove", move);
    globe.removeEventListener("pointerup", end);
    globe.removeEventListener("pointercancel", end);
  };
}
