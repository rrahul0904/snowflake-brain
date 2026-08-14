import { getGlobeActivity } from "../api.js";

const DEG = Math.PI / 180;
const WORLD_GEOMETRY_URL = "/static/assets/world-major-land.geojson";
const ROTATION_PERIOD_MS = 56000;
const AUTO_DEGREES_PER_MS = 360 / ROTATION_PERIOD_MS;

function css(name, fallback) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

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
      minLon: Math.min(...lons),
      maxLon: Math.max(...lons),
      minLat: Math.min(...lats),
      maxLat: Math.max(...lats),
    };
  }).filter((polygon) => polygon.rings[0]?.length > 2);
}

function pointInRing(lon, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
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
    const lonStep = 2.75 / Math.max(0.72, Math.cos(lat * DEG));
    for (let lon = -180; lon < 180; lon += lonStep) {
      if (isLand(lon, lat, polygons)) dots.push({ lat, lon });
    }
  }
  return dots;
}

function drawProjectedLine(ctx, points, projection, strokeStyle, lineWidth = 1) {
  let segment = [];
  const flush = () => {
    if (segment.length < 2) { segment = []; return; }
    ctx.beginPath();
    ctx.moveTo(segment[0].x, segment[0].y);
    for (let i = 1; i < segment.length; i += 1) ctx.lineTo(segment[i].x, segment[i].y);
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
    segment = [];
  };
  for (const coord of points) {
    const p = projection(coord[1], coord[0]);
    if (p.visible) segment.push(p);
    else flush();
  }
  flush();
}

function drawGraticule(ctx, projection) {
  const line = css("--v-globe-grid", "rgba(240,229,216,.06)");
  for (let lat = -60; lat <= 60; lat += 30) {
    const points = [];
    for (let lon = -180; lon <= 180; lon += 4) points.push([lon, lat]);
    drawProjectedLine(ctx, points, projection, line, 0.65);
  }
  for (let lon = -180; lon < 180; lon += 30) {
    const points = [];
    for (let lat = -88; lat <= 88; lat += 4) points.push([lon, lat]);
    drawProjectedLine(ctx, points, projection, line, 0.65);
  }
}

export function renderActivityGlobe(container) {
  if (!container) return () => {};
  container.innerHTML = `
    <figure class="v26-globe-wrap" role="img" aria-label="Rotating globe showing real world geography. Learner markers appear only when privacy-safe aggregated activity is available.">
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
  let centerLon = -24;
  let centerLat = 12;
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

  const projection = (lat, lon) => project(lat, lon, centerLat, centerLon, size * 0.455, size / 2);

  function resize() {
    const rect = globe.getBoundingClientRect();
    size = Math.max(250, Math.round(rect.width || 410));
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
    const radius = size * 0.455;
    ctx.clearRect(0, 0, size, size);
    const shade = ctx.createRadialGradient(center - radius * 0.34, center - radius * 0.34, radius * 0.05, center, center, radius);
    shade.addColorStop(0, css("--v-globe-highlight", "rgba(240,229,216,.05)"));
    shade.addColorStop(0.72, css("--v-globe-fill", "rgba(240,229,216,.02)"));
    shade.addColorStop(1, css("--v-globe-edge", "rgba(0,0,0,.2)"));
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.fillStyle = shade;
    ctx.fill();
    ctx.save();
    ctx.beginPath();
    ctx.arc(center, center, radius - 0.5, 0, Math.PI * 2);
    ctx.clip();
    drawGraticule(ctx, projection);

    const dotColor = css("--v-globe-land-dot", "rgba(240,229,216,.5)");
    ctx.fillStyle = dotColor;
    const baseDot = Math.max(0.8, Math.min(1.45, size / 360));
    for (const dot of landDots) {
      const p = projection(dot.lat, dot.lon);
      if (!p.visible || p.depth < 0.015) continue;
      const alpha = Math.min(1, 0.22 + p.depth * 0.88);
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(p.x, p.y, baseDot * (0.76 + p.depth * 0.34), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    const coastline = css("--v-globe-land-stroke", "rgba(226,168,124,.16)");
    for (const polygon of polygons) {
      for (const ring of polygon.rings) drawProjectedLine(ctx, ring, projection, coastline, 0.45);
    }
    ctx.restore();
    ctx.beginPath();
    ctx.arc(center, center, radius, 0, Math.PI * 2);
    ctx.strokeStyle = css("--v-globe-outline", "rgba(240,229,216,.16)");
    ctx.lineWidth = 0.8;
    ctx.stroke();
  }

  function placeActivity() {
    const visible = activity
      .map((item, index) => ({ item, index, p: projection(item.lat, item.lon) }))
      .filter((row) => row.p.visible && row.p.depth > 0.03)
      .sort((a, b) => (b.item.count || 0) - (a.item.count || 0));
    const labelled = new Set(visible.slice(0, 6).map((row) => row.index));
    activityNodes.forEach((row, index) => {
      const p = projection(row.item.lat, row.item.lon);
      if (!p.visible || p.depth < 0.04) {
        row.node.hidden = true;
        return;
      }
      row.node.hidden = false;
      row.node.style.left = `${p.x}px`;
      row.node.style.top = `${p.y}px`;
      row.node.style.opacity = String(Math.min(1, 0.38 + p.depth * 0.72));
      row.node.style.transform = `translate(-50%,-50%) scale(${0.82 + p.depth * 0.22})`;
      row.node.toggleAttribute("data-label", labelled.has(index) && p.depth > 0.34);
    });
  }

  function draw() {
    if (!ctx) return;
    drawSphere();
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
      node.className = "v26-globe-point";
      node.innerHTML = `<i></i><b>${item.label}</b><em>${item.count}</em>`;
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
      globe.closest("figure")?.setAttribute(
        "aria-label",
        live
          ? `Rotating real-world globe with ${activityResult.value.active_total} privacy-safe aggregated active learners in the last ${activityResult.value.window_minutes} minutes.`
          : "Rotating real-world globe. No fabricated learner locations are shown when privacy-safe live activity is unavailable."
      );
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
    centerLon -= dx * 0.33;
    centerLat = Math.max(-55, Math.min(55, centerLat + dy * 0.20));
    lastX = event.clientX;
    lastY = event.clientY;
    draw();
  }

  function end(event) {
    if (!dragging || (event.pointerId != null && event.pointerId !== pointerId)) return;
    dragging = false;
    pointerId = null;
    resumeAfter = performance.now() + 1800;
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
