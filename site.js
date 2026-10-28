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
  function show(i){
    idx = (i + photos.length) % photos.length;
    lbImg.src = photos[idx].getAttribute("data-full");
    lbImg.alt = photos[idx].alt;
    lbCount.textContent = (idx + 1) + " / " + photos.length;
  }
  function openLb(i){ show(i); lb.classList.add("open"); document.body.style.overflow = "hidden"; }
  function closeLb(){ lb.classList.remove("open"); document.body.style.overflow = ""; }
  allPhotos.forEach(function(img){
    img.addEventListener("click", function(){
      refreshPhotos();
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
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)){
      if (dx < 0) show(idx + 1); else show(idx - 1);
      /* a drag that ends outside the image would otherwise also fire a
         backdrop click and close the lightbox right after switching */
      suppressLbClick = true;
    }
    swipeX = null; swipeY = null;
  }
  lb.addEventListener("touchstart", function(e){
    if (!lb.classList.contains("open")) return;
    var t = e.changedTouches[0];
    swipeX = t.clientX; swipeY = t.clientY;
  }, {passive:true});
  lb.addEventListener("touchend", function(e){
    if (swipeX === null) return;
    var t = e.changedTouches[0];
    swipeEnd(t.clientX - swipeX, t.clientY - swipeY);
  }, {passive:true});
  lb.addEventListener("touchcancel", function(){ swipeX = null; swipeY = null; }, {passive:true});
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

})();
