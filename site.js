(function(){
  "use strict";

  /* ---------- reveal on scroll ---------- */
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.25 });
    revealEls.forEach(function(el){ io.observe(el); });
  } else {
    revealEls.forEach(function(el){ el.classList.add("in"); });
  }



  /* ---------- copy helper ---------- */
  function copyText(text, tipEl, okMsg){
    function done(){ if (tipEl) tipEl.textContent = okMsg; }
    function fallback(){
      var ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta); done();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else { fallback(); }
  }

  /* ---------- work filter (by item / by series) ---------- */
  var workPanels = Array.prototype.slice.call(document.querySelectorAll(".panel[data-series]"));
  var curCat = "all", curSeries = "all", curSearch = "";
  var filterCount = document.getElementById("filterCount");
  var filterEmpty = document.getElementById("filterEmpty");
  function applyFilter(){
    var shown = 0;
    workPanels.forEach(function(panel){
      var cats = (panel.getAttribute("data-cat") || "").split(" ");
      var okCat = (curCat === "all") || cats.indexOf(curCat) !== -1;
      var okSeries = (curSeries === "all") || panel.getAttribute("data-series") === curSeries;
      var txt = (panel.textContent || "") + " " + Array.prototype.map.call(panel.querySelectorAll("img"), function(i){ return i.alt || ""; }).join(" ");
      var okSearch = !curSearch || txt.toLowerCase().indexOf(curSearch) !== -1;
      var ok = okCat && okSeries && okSearch;
      panel.hidden = !ok;
      if (ok) shown++;
    });
    if (filterCount) filterCount.textContent = "当前显示 " + shown + " / " + workPanels.length + " 张";
    if (filterEmpty) filterEmpty.classList.toggle("show", shown === 0);
    if (typeof refreshPhotos === "function") refreshPhotos();
  }
  function bindChips(attr, set){
    var chips = document.querySelectorAll("[" + attr + "]");
    chips.forEach(function(chip){
      chip.addEventListener("click", function(){
        chips.forEach(function(c){ c.classList.remove("active"); });
        chip.classList.add("active");
        set(chip.getAttribute(attr));
        applyFilter();
      });
    });
  }
  bindChips("data-cat-filter", function(v){ curCat = v; });
  bindChips("data-series-filter", function(v){ curSeries = v; });
  var searchEl = document.getElementById("workSearch");
  if (searchEl) { searchEl.addEventListener("input", function(){ curSearch = searchEl.value.trim().toLowerCase(); applyFilter(); }); }
  applyFilter();

  /* ---------- per-work share link ---------- */
  document.querySelectorAll("[data-share]").forEach(function(btn){
    btn.addEventListener("click", function(){
      var id = btn.getAttribute("data-share");
      var link = location.href.split("#")[0] + "#" + id;
      var tip = btn.parentNode.querySelector(".share-tip");
      copyText(link, tip, "链接已复制");
    });
  });

  /* ---------- lightbox ---------- */
  var allPhotos = Array.prototype.slice.call(document.querySelectorAll("img.ph"));
  var photos = allPhotos.slice();
  function refreshPhotos(){
    if (!allPhotos) return;
    var vis = allPhotos.filter(function(img){
      var panel = img.closest ? img.closest(".panel") : null;
      return !panel || !panel.hidden;
    });
    photos = vis.length ? vis : allPhotos.slice();
  }
  var lb = document.getElementById("lightbox");
  var lbImg = document.getElementById("lbImg");
  var lbCount = document.getElementById("lbCount");
  var idx = 0;
  var lbScale = 1, lbPanX = 0, lbPanY = 0;
  function applyLbTransform(){
    lbImg.style.transform = (lbScale === 1 && lbPanX === 0 && lbPanY === 0) ? "" : "translate(" + lbPanX + "px," + lbPanY + "px) scale(" + lbScale + ")";
  }
  function show(i){
    idx = (i + photos.length) % photos.length;
    var fullL = photos[idx].getAttribute("data-full-l");
    lbImg.src = (window.innerWidth > 900 && fullL) ? fullL : photos[idx].getAttribute("data-full");
    lbImg.alt = photos[idx].alt;
    lbCount.textContent = (idx + 1) + " / " + photos.length;
    lbScale = 1; lbPanX = 0; lbPanY = 0; applyLbTransform();
  }
  function openLb(i){ show(i); lb.classList.add("open"); document.body.style.overflow = "hidden"; }
  function closeLb(){ lbScale = 1; lbPanX = 0; lbPanY = 0; lbImg.style.transform = ""; lb.classList.remove("open"); document.body.style.overflow = ""; }
  allPhotos.forEach(function(img){
    img.addEventListener("click", function(){
      var grp = img.getAttribute("data-group");
      if (grp) {
        photos = allPhotos.filter(function(p){ return p.getAttribute("data-group") === grp; });
      } else {
        refreshPhotos();
      }
      var i = photos.indexOf(img);
      openLb(i === -1 ? 0 : i);
    });
  });
  document.getElementById("lbClose").addEventListener("click", closeLb);
  document.getElementById("lbPrev").addEventListener("click", function(e){ e.stopPropagation(); show(idx - 1); });
  document.getElementById("lbNext").addEventListener("click", function(e){ e.stopPropagation(); show(idx + 1); });
  var suppressLbClick = false;
  lb.addEventListener("click", function(e){
    if (suppressLbClick){ suppressLbClick = false; return; }
    if (e.target === lb) closeLb();
  });
  /* ---------- lightbox swipe: touch swipe + mouse drag, same as prev/next ---------- */
  var swipeX = null, swipeY = null;
  function swipeEnd(dx, dy){
    if (swipeX === null) return;
    if (lbScale > 1){ swipeX = null; swipeY = null; return; }
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)){
      if (dx < 0) show(idx + 1); else show(idx - 1);
      /* a drag that ends outside the image would otherwise also fire a
         backdrop click and close the lightbox right after switching */
      suppressLbClick = true;
    }
    /* drag the photo downward to dismiss (swipe-down-to-close) */
    if (dy > 80 && Math.abs(dy) > Math.abs(dx)){
      closeLb();
      suppressLbClick = true;
    }
    swipeX = null; swipeY = null;
  }
  var pinchDist = 0, pinchScaleStart = 1, isPinch = false, lastTapTime = 0, panStartX = 0, panStartY = 0, panBaseX = 0, panBaseY = 0;
  function pinchDistance(e){
    var a = e.touches[0], b = e.touches[1];
    return Math.sqrt((a.clientX - b.clientX) * (a.clientX - b.clientX) + (a.clientY - b.clientY) * (a.clientY - b.clientY));
  }
  lb.addEventListener("touchstart", function(e){
    if (!lb.classList.contains("open")) return;
    if (e.touches.length === 2){ isPinch = true; pinchDist = pinchDistance(e); pinchScaleStart = lbScale; swipeX = null; swipeY = null; return; }
    var t = e.changedTouches[0];
    swipeX = t.clientX; swipeY = t.clientY;
    if (lbScale > 1){ panStartX = t.clientX; panStartY = t.clientY; panBaseX = lbPanX; panBaseY = lbPanY; }
  }, {passive:true});
  lb.addEventListener("touchmove", function(e){
    if (!lb.classList.contains("open")) return;
    if (isPinch && e.touches.length === 2){
      var d = pinchDistance(e);
      if (pinchDist > 0){ lbScale = Math.max(1, Math.min(3, pinchScaleStart * d / pinchDist)); applyLbTransform(); }
      return;
    }
    if (lbScale > 1 && e.touches.length === 1){
      var t = e.touches[0];
      var span = 90 * lbScale;
      lbPanX = Math.max(-span, Math.min(span, panBaseX + (t.clientX - panStartX)));
      lbPanY = Math.max(-span, Math.min(span, panBaseY + (t.clientY - panStartY)));
      applyLbTransform();
    }
  }, {passive:true});
  lb.addEventListener("touchend", function(e){
    if (isPinch){ isPinch = false; if (lbScale < 1.15){ lbScale = 1; lbPanX = 0; lbPanY = 0; applyLbTransform(); } swipeX = null; swipeY = null; return; }
    if (swipeX === null) return;
    var t = e.changedTouches[0];
    var dx = t.clientX - swipeX, dy = t.clientY - swipeY;
    var now = Date.now();
    if (Math.abs(dx) < 12 && Math.abs(dy) < 12 && now - lastTapTime < 300){
      lastTapTime = 0;
      if (lbScale > 1){ lbScale = 1; lbPanX = 0; lbPanY = 0; } else { lbScale = 2; }
      applyLbTransform(); swipeX = null; swipeY = null; return;
    }
    if (Math.abs(dx) < 12 && Math.abs(dy) < 12) lastTapTime = now;
    swipeEnd(dx, dy);
  }, {passive:true});
  lb.addEventListener("touchcancel", function(){ isPinch = false; swipeX = null; swipeY = null; }, {passive:true});
  lbImg.addEventListener("dblclick", function(){
    if (!lb.classList.contains("open")) return;
    if (lbScale > 1){ lbScale = 1; lbPanX = 0; lbPanY = 0; } else { lbScale = 2; }
    applyLbTransform();
  });
  lbImg.addEventListener("wheel", function(e){
    if (!lb.classList.contains("open")) return;
    var step = e.deltaY < 0 ? 0.25 : -0.25;
    var ns = Math.max(1, Math.min(3, lbScale + step));
    if (ns === 1){ lbPanX = 0; lbPanY = 0; }
    lbScale = ns; applyLbTransform();
  }, {passive:true});
  var swipeMouse = false;
  /* images are natively draggable: without this, a mouse drag starts a
     drag-and-drop instead of a mouseup, so drag-to-switch would never fire */
  lbImg.addEventListener("dragstart", function(e){ e.preventDefault(); });
  lbImg.addEventListener("mousedown", function(e){
    if (!lb.classList.contains("open")) return;
    swipeX = e.clientX; swipeY = e.clientY; swipeMouse = true;
  });
  document.addEventListener("mouseup", function(e){
    if (!swipeMouse || !lb.classList.contains("open")) return;
    swipeMouse = false;
    swipeEnd(e.clientX - swipeX, e.clientY - swipeY);
  });
  document.addEventListener("keydown", function(e){
    if (!lb.classList.contains("open")) return;
    if (e.key === "Escape") closeLb();
    if (e.key === "ArrowLeft") show(idx - 1);
    if (e.key === "ArrowRight") show(idx + 1);
  });

  
  /* ---------- multi-page v2: nav active, old share redirect, search ---------- */
  (function(){
    var path = location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(function(a){
      if (a.getAttribute('href') === path) a.classList.add('active');
    });
    var isHome = (path === '' || path === 'index.html');
    var h = location.hash || '';
    if (isHome && /^#(work-\d+)$/.test(h)) { location.replace('xiaohongshu.html' + h); return; }
    if (isHome && /^#(video-\d+)$/.test(h)) { location.replace('shipinhao.html' + h); return; }
  })();
  /* ---------- professional batch 2026-10-28: back-to-top ---------- */
  (function(){
    var bt = document.getElementById("backTop");
    if (!bt) return;
    window.addEventListener("scroll", function(){ bt.classList.toggle("show", window.scrollY > 600); }, {passive:true});
    bt.addEventListener("click", function(){ window.scrollTo({top:0, behavior:"smooth"}); });
  })();
  /* ---------- professional batch 2026-10-28: MP search + year filter ---------- */
  (function(){
    var mpSearch = document.getElementById("mpSearch");
    if (!mpSearch) return;
    var cards = Array.prototype.slice.call(document.querySelectorAll(".mp-card"));
    var curYear = "all";
    var countEl = document.getElementById("mpCount");
    function applyMp(){
      var q = mpSearch.value.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function(card){
        var okYear = curYear === "all" || card.getAttribute("data-year") === curYear;
        var okSearch = !q || (card.textContent || "").toLowerCase().indexOf(q) !== -1;
        var ok = okYear && okSearch;
        card.style.display = ok ? "" : "none";
        if (ok) shown++;
      });
      if (countEl) countEl.textContent = "当前显示 " + shown + " / " + cards.length + " 篇";
    }
    document.querySelectorAll("[data-year-filter]").forEach(function(btn){
      btn.addEventListener("click", function(){
        document.querySelectorAll("[data-year-filter]").forEach(function(b){ b.classList.remove("active"); });
        btn.classList.add("active");
        curYear = btn.getAttribute("data-year-filter");
        applyMp();
      });
    });
    mpSearch.addEventListener("input", applyMp);
    applyMp();
  })();
  /* ---------- professional batch 2026-10-28: light-weight stats (totals only) ---------- */
  (function(){
    var STATS_URL = 'https://script.google.com/macros/s/AKfycbyeYeJLDi_GgVa3z3f8f63Q82Al1h-6NEbshppt_gan7IbrxhR4crPHzwjHDlxw_MO6/exec';
    function sendStat(event){
      try {
        var page = (location.pathname.split('/').pop() || 'index.html');
        var body = JSON.stringify({ stats: 1, page: page, event: event });
        if (navigator.sendBeacon) {
          var blob = new Blob([body], { type: 'text/plain' });
          if (navigator.sendBeacon(STATS_URL, blob)) return;
        }
        fetch(STATS_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, mode: 'no-cors', body: body, keepalive: true }).catch(function(){});
      } catch (e) {}
    }
    sendStat('view');
    document.addEventListener('click', function(e){
      var t = e.target && e.target.closest ? e.target.closest('.order-btn') : null;
      if (t) sendStat('order_click');
    });
  })();
  /* ---------- live section 2026-10-28: X slow-live embed, two-state ---------- */
  (function(){
    var sec = document.getElementById("liveSection");
    if (!sec) return;
    var player = document.getElementById("livePlayer");
    var fallback = document.getElementById("liveFallback");
    var sub = document.getElementById("liveSub");
    var note = document.getElementById("liveNote");
    function showFallback(){ if (fallback) fallback.style.display = ""; }
    fetch("live.json", {cache: "no-store"}).then(function(r){ return r.json(); }).then(function(data){
      if (!data || data.status !== "live" || !data.broadcast_url) { showFallback(); return; }
      if (sub && data.title) sub.textContent = data.title;
      if (note && data.source) note.textContent = "来源：" + data.source + "（公有领域画面）· 播放器由 X 提供";
      var done = false;
      function fail(){ if (!done) { done = true; showFallback(); } }
      var timer = setTimeout(fail, 8000);
      var s = document.createElement("script");
      s.async = true; s.src = "https://platform.x.com/widgets.js";
      s.onerror = function(){ clearTimeout(timer); fail(); };
      s.onload = function(){
        var m = /broadcasts[/]([A-Za-z0-9]+)/.exec(data.broadcast_url || "");
        if (!m) { clearTimeout(timer); fail(); return; }
        var bq = document.createElement("blockquote");
        bq.className = "twitter-broadcast";
        bq.setAttribute("data-broadcast-id", m[1]);
        var a = document.createElement("a");
        a.href = data.broadcast_url; a.textContent = "Broadcast";
        bq.appendChild(a);
        player.appendChild(bq);
        if (window.twttr && twttr.widgets && twttr.widgets.load) { twttr.widgets.load(player); }
        var tries = 0;
        var iv = setInterval(function(){
          tries++;
          if (player.querySelector("iframe")) {
            clearInterval(iv); clearTimeout(timer); done = true;
            if (fallback) fallback.style.display = "none";
          } else if (tries >= 10) { clearInterval(iv); clearTimeout(timer); fail(); }
        }, 500);
      };
      document.head.appendChild(s);
    }).catch(function(){ showFallback(); });
  })();

})();
