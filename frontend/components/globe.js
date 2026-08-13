const LOCATIONS = [
  { label: "Seattle", lat: 47.6, lon: -122.3 },
  { label: "San Francisco", lat: 37.8, lon: -122.4 },
  { label: "Toronto", lat: 43.7, lon: -79.4 },
  { label: "New York", lat: 40.7, lon: -74.0 },
  { label: "São Paulo", lat: -23.6, lon: -46.6 },
  { label: "London", lat: 51.5, lon: -0.1 },
  { label: "Paris", lat: 48.9, lon: 2.3 },
  { label: "Berlin", lat: 52.5, lon: 13.4 },
  { label: "Dubai", lat: 25.2, lon: 55.3 },
  { label: "Bengaluru", lat: 12.9, lon: 77.6 },
  { label: "Singapore", lat: 1.35, lon: 103.8 },
  { label: "Tokyo", lat: 35.7, lon: 139.7 },
  { label: "Sydney", lat: -33.9, lon: 151.2 },
];

const DEG = Math.PI / 180;

export function renderActivityGlobe(container) {
  if (!container) return () => {};
  container.innerHTML = `
    <div class="v26-globe-wrap" role="img" aria-label="Animated globe showing Snowflake certification learners around the world">
      <div class="v26-globe" data-globe>
        <svg class="v26-globe-grid" viewBox="0 0 400 400" aria-hidden="true">
          <defs>
            <radialGradient id="globeShade" cx="35%" cy="30%" r="70%">
              <stop offset="0" stop-color="currentColor" stop-opacity=".03" />
              <stop offset=".82" stop-color="currentColor" stop-opacity=".07" />
              <stop offset="1" stop-color="currentColor" stop-opacity=".18" />
            </radialGradient>
            <clipPath id="globeClip"><circle cx="200" cy="200" r="176" /></clipPath>
          </defs>
          <circle class="v26-globe-fill" cx="200" cy="200" r="176" fill="url(#globeShade)" />
          <g clip-path="url(#globeClip)" class="v26-globe-lines">
            <ellipse cx="200" cy="200" rx="176" ry="55" />
            <ellipse cx="200" cy="200" rx="176" ry="112" />
            <ellipse cx="200" cy="200" rx="176" ry="154" />
            <ellipse cx="200" cy="200" rx="55" ry="176" />
            <ellipse cx="200" cy="200" rx="112" ry="176" />
            <ellipse cx="200" cy="200" rx="154" ry="176" />
            <path d="M33 171 C95 149 129 116 139 72 C163 91 184 101 203 102 C224 104 241 92 254 72 C274 104 307 126 367 139 C321 166 307 203 319 249 C278 228 243 232 217 262 C199 231 166 216 118 218 C131 188 101 169 33 171Z" class="v26-continent" />
            <path d="M83 251 C127 242 158 253 177 282 C148 300 132 329 129 370 C104 337 89 297 83 251Z" class="v26-continent" />
            <path d="M238 253 C272 245 301 250 326 271 C306 288 298 309 302 333 C277 323 256 296 238 253Z" class="v26-continent" />
          </g>
          <circle class="v26-globe-outline" cx="200" cy="200" r="176" />
        </svg>
        <div class="v26-globe-points" data-globe-points></div>
      </div>
      <div class="v26-globe-caption"><span class="v26-live-dot"></span> Snowflake certification study, worldwide</div>
    </div>`;

  const globe = container.querySelector("[data-globe]");
  const pointsRoot = container.querySelector("[data-globe-points]");
  const points = LOCATIONS.map((item) => {
    const node = document.createElement("span");
    node.className = "v26-globe-point";
    node.innerHTML = `<i></i><b>${item.label}</b>`;
    pointsRoot.appendChild(node);
    return { ...item, node };
  });

  let rotation = -35;
  let dragging = false;
  let lastX = 0;
  let raf = 0;
  let last = performance.now();
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

  function place() {
    const size = globe.clientWidth || 400;
    const radius = size * 0.44;
    const center = size / 2;
    for (const point of points) {
      const lat = point.lat * DEG;
      const lon = (point.lon + rotation) * DEG;
      const depth = Math.cos(lat) * Math.cos(lon);
      const x = center + radius * Math.cos(lat) * Math.sin(lon);
      const y = center - radius * Math.sin(lat);
      const scale = 0.72 + Math.max(0, depth) * 0.34;
      point.node.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%) scale(${scale})`;
      point.node.style.opacity = depth > -0.05 ? String(0.32 + Math.max(0, depth) * 0.68) : "0";
      point.node.style.zIndex = depth > 0 ? "3" : "1";
      point.node.toggleAttribute("data-front", depth > 0.24);
    }
  }

  function tick(now) {
    if (!dragging && !reduceMotion) rotation += Math.min(0.035 * (now - last), 0.75);
    last = now;
    place();
    raf = requestAnimationFrame(tick);
  }

  const begin = (event) => {
    dragging = true;
    lastX = event.clientX ?? event.touches?.[0]?.clientX ?? 0;
    globe.classList.add("is-dragging");
  };
  const move = (event) => {
    if (!dragging) return;
    const x = event.clientX ?? event.touches?.[0]?.clientX ?? lastX;
    rotation += (x - lastX) * 0.34;
    lastX = x;
    place();
  };
  const end = () => {
    dragging = false;
    globe.classList.remove("is-dragging");
  };

  globe.addEventListener("pointerdown", begin);
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", end);
  place();
  raf = requestAnimationFrame(tick);

  return () => {
    cancelAnimationFrame(raf);
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", end);
  };
}
