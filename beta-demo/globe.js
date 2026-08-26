(() => {
  const LAND = [
    // North America
    [-168,66],[-156,58],[-145,61],[-137,55],[-129,51],[-124,44],[-122,37],[-117,33],[-111,29],[-104,25],[-97,20],[-91,18],[-86,21],[-82,26],[-80,31],[-76,35],[-71,41],[-66,45],[-61,51],[-67,57],[-79,61],[-92,64],[-110,69],[-128,70],[-148,70],
    [-112,49],[-105,45],[-99,39],[-95,35],[-90,31],[-84,29],[-77,37],[-87,42],[-98,45],[-108,42],
    // Central America / Caribbean
    [-92,17],[-88,16],[-84,10],[-80,9],[-77,8],[-75,18],[-70,19],[-66,18],
    // South America
    [-79,10],[-75,4],[-73,-5],[-70,-13],[-66,-21],[-63,-29],[-60,-37],[-66,-46],[-70,-53],[-74,-47],[-76,-35],[-79,-21],[-81,-8],[-78,1],[-70,5],[-61,7],[-53,4],[-47,-1],[-43,-8],[-39,-15],[-42,-23],[-48,-29],[-54,-34],[-60,-32],[-64,-21],[-60,-12],[-55,-5],[-63,-2],[-70,-6],
    // Europe
    [-10,36],[-8,43],[-2,48],[4,51],[10,55],[18,58],[24,60],[30,59],[34,55],[29,51],[24,48],[18,45],[13,44],[8,46],[3,44],[-3,42],[0,38],[8,40],[15,41],[22,39],[28,41],
    // Scandinavia / UK
    [-7,50],[-4,55],[0,58],[3,55],[1,51],[10,58],[14,64],[20,69],[27,70],[31,65],[24,61],[17,59],
    // Africa
    [-17,32],[-8,35],[2,36],[12,34],[20,31],[27,31],[34,27],[39,15],[44,10],[46,2],[42,-8],[37,-17],[31,-25],[24,-31],[17,-35],[10,-34],[5,-29],[0,-22],[-5,-12],[-10,-2],[-15,10],[-17,22],[-12,28],[-2,30],[8,27],[17,22],[24,15],[29,6],[27,-4],[22,-11],[17,-18],[12,-24],[7,-18],[5,-7],[1,3],[-4,12],[-7,22],[0,27],
    // Asia
    [30,40],[38,44],[46,48],[55,53],[66,55],[78,58],[90,61],[104,62],[119,58],[133,53],[146,49],[157,55],[165,60],[171,55],[165,48],[153,44],[144,41],[137,35],[130,31],[123,24],[117,18],[109,12],[103,8],[97,10],[91,17],[84,21],[77,24],[70,25],[62,28],[55,31],[48,31],[42,35],[35,37],
    [62,42],[72,43],[80,40],[88,35],[96,31],[104,29],[113,31],[120,36],[127,40],[136,42],[143,46],[151,50],[158,47],[151,40],[142,36],[134,31],[127,26],[121,21],[113,18],[107,22],[101,25],[94,24],[88,27],[81,30],[74,33],[67,35],
    // India / SE Asia / Japan
    [68,24],[72,18],[76,10],[80,7],[84,10],[88,21],[92,24],[96,19],[100,15],[104,11],[108,7],[111,2],[115,1],[118,5],[121,12],[124,18],[129,31],[133,34],[137,37],[141,40],[144,44],
    // Indonesia
    [96,5],[102,1],[108,-4],[114,-7],[120,-5],[126,-3],[132,-4],[139,-6],[145,-5],
    // Australia / NZ
    [113,-22],[117,-14],[124,-12],[132,-12],[140,-15],[148,-20],[153,-28],[151,-35],[144,-39],[135,-36],[128,-33],[121,-31],[115,-27],[126,-20],[136,-19],[145,-24],[138,-28],[129,-27],
    [166,-35],[172,-39],[176,-44],[170,-46],[166,-42],
    // Greenland / Iceland
    [-53,60],[-45,64],[-38,70],[-42,77],[-52,81],[-61,77],[-66,70],[-61,64],[-20,64],[-17,66]
  ];

  const DEG = Math.PI / 180;
  let raf = 0;
  let observer;

  function mount() {
    const side = document.querySelector('.hero-side');
    if (!side || side.querySelector('.earth-card')) return;

    const readiness = side.querySelector('.readiness-ring');
    const note = side.querySelector('.hero-side-note');
    const card = document.createElement('div');
    card.className = 'earth-card';
    card.innerHTML = `
      <div class="earth-stage" aria-label="Animated earth visualization">
        <canvas class="earth-canvas" width="520" height="520" aria-hidden="true"></canvas>
        <div class="earth-orbit earth-orbit-a"></div>
        <div class="earth-orbit earth-orbit-b"></div>
        <div class="earth-badge"><span></span> Global Snowflake learning</div>
      </div>
      <div class="earth-meta">
        <div><strong>5</strong><span>exam domains</span></div>
        <div><strong>19</strong><span>objectives</span></div>
        <div><strong>1,200</strong><span>mapped questions</span></div>
      </div>`;

    side.insertBefore(card, readiness || note || null);
    if (readiness) readiness.classList.add('hero-readiness-compact');
    if (note) note.classList.add('hero-note-compact');
    draw(card.querySelector('canvas'));
  }

  function draw(canvas) {
    cancelAnimationFrame(raf);
    const ctx = canvas.getContext('2d');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const css = 260;
    canvas.width = css * dpr;
    canvas.height = css * dpr;
    canvas.style.width = css + 'px';
    canvas.style.height = css + 'px';
    ctx.setTransform(dpr,0,0,dpr,0,0);

    let start = performance.now();
    function frame(now) {
      const theme = document.documentElement.dataset.theme === 'dark';
      const cx = css/2, cy = css/2, r = css * 0.36;
      const rot = reduced ? 0.2 : ((now-start) * 0.00013 + 0.45);
      ctx.clearRect(0,0,css,css);

      const glow = ctx.createRadialGradient(cx-r*.28,cy-r*.35,r*.05,cx,cy,r*1.18);
      glow.addColorStop(0, theme ? 'rgba(90,202,242,.27)' : 'rgba(80,195,239,.25)');
      glow.addColorStop(.58, theme ? 'rgba(14,96,139,.18)' : 'rgba(13,136,190,.12)');
      glow.addColorStop(1,'rgba(0,0,0,0)');
      ctx.fillStyle = glow;
      ctx.beginPath(); ctx.arc(cx,cy,r*1.18,0,Math.PI*2); ctx.fill();

      // Ocean sphere
      const ocean = ctx.createRadialGradient(cx-r*.38,cy-r*.44,r*.08,cx,cy,r);
      ocean.addColorStop(0, theme ? '#173b50' : '#dff5fd');
      ocean.addColorStop(.62, theme ? '#0a2738' : '#b9e8f8');
      ocean.addColorStop(1, theme ? '#061925' : '#6fc5e7');
      ctx.fillStyle = ocean;
      ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.fill();

      ctx.save();
      ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.clip();

      // Latitude/longitude grid
      ctx.strokeStyle = theme ? 'rgba(133,211,241,.13)' : 'rgba(4,103,151,.12)';
      ctx.lineWidth = .7;
      for (let lat=-60; lat<=60; lat+=30) {
        const y = cy - Math.sin(lat*DEG)*r;
        const rx = Math.cos(lat*DEG)*r;
        ctx.beginPath(); ctx.ellipse(cx,y,rx,rx*.12,0,0,Math.PI*2); ctx.stroke();
      }
      for (let lon=0; lon<180; lon+=30) {
        const phase = lon*DEG + rot;
        ctx.beginPath();
        for(let a=-90;a<=90;a+=3){
          const lat=a*DEG, x3=Math.cos(lat)*Math.sin(phase), y3=Math.sin(lat), z3=Math.cos(lat)*Math.cos(phase);
          if(z3<-.02) continue;
          const x=cx+x3*r, y=cy-y3*r;
          if(a===-90) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }
        ctx.stroke();
      }

      // Simplified continental point cloud projected on the sphere
      LAND.forEach(([lon,lat],i)=>{
        const la=lat*DEG, lo=lon*DEG+rot;
        const x3=Math.cos(la)*Math.sin(lo), y3=Math.sin(la), z3=Math.cos(la)*Math.cos(lo);
        if(z3<=-.03) return;
        const px=cx+x3*r, py=cy-y3*r;
        const depth=.35+.65*z3;
        ctx.fillStyle = theme ? `rgba(119,219,180,${0.38+depth*.48})` : `rgba(14,124,108,${0.38+depth*.5})`;
        ctx.beginPath(); ctx.arc(px,py,1.15+depth*.85,0,Math.PI*2); ctx.fill();
        if(i%9===0){
          ctx.fillStyle = theme ? `rgba(118,212,245,${.25+depth*.55})` : `rgba(7,135,190,${.25+depth*.45})`;
          ctx.beginPath(); ctx.arc(px,py,2.4+depth,0,Math.PI*2); ctx.fill();
        }
      });
      ctx.restore();

      // Atmospheric rim
      ctx.strokeStyle = theme ? 'rgba(112,206,242,.56)' : 'rgba(11,135,188,.5)';
      ctx.lineWidth = 1.25;
      ctx.beginPath(); ctx.arc(cx,cy,r+.6,0,Math.PI*2); ctx.stroke();
      ctx.strokeStyle = theme ? 'rgba(112,206,242,.13)' : 'rgba(11,135,188,.13)';
      ctx.lineWidth = 8;
      ctx.beginPath(); ctx.arc(cx,cy,r+2,0,Math.PI*2); ctx.stroke();

      if (!reduced) raf = requestAnimationFrame(frame);
    }
    frame(performance.now());
  }

  function watch() {
    mount();
    observer = new MutationObserver(() => mount());
    const route = document.querySelector('#routeView');
    if (route) observer.observe(route,{childList:true,subtree:false});
    window.addEventListener('hashchange', () => setTimeout(mount,0));
    document.querySelector('#themeToggle')?.addEventListener('click', () => setTimeout(() => {
      const c=document.querySelector('.earth-canvas'); if(c) draw(c);
    },20));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',watch);
  else watch();
})();
