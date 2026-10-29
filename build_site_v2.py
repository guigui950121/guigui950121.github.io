#!/usr/bin/env python3
"""Build wangxiaowu.cc multi-page site v2 from the verified single-page site.
Input : ~/workspace/website-optimize/site/index.html  (live, verified)
Output: ~/workspace/website-optimize/site-v2/  (index, xiaohongshu, shipinhao,
        gongzhonghao, dingzhi, style.css, site.js, order.js)
Rules: prices, copy, form logic, lightbox swipe, preview banner unchanged.
       No email address anywhere. No QR code anywhere. No Jinan Shushuo content.
"""
import re, os, sys, hashlib
from urllib.parse import quote as _urlquote

# Paths: workspace default; Actions run sets SITE_ROOT to the repo checkout
# and SITE_OUT to the repo root (pages are served from root there).
ROOT = os.environ.get('SITE_ROOT', os.path.expanduser('~/workspace/website-optimize'))
SRC = os.path.join(ROOT, 'site', 'index.html')
OUT = os.environ.get('SITE_OUT', os.path.join(ROOT, 'site-v2'))
html = open(SRC, encoding='utf-8').read()

css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
js_full = re.search(r'<script>\n(.*?)\n</script>', html, re.S).group(1)
# Split JS at order form marker
marker = '/* ---------- order form ---------- */'
assert marker in js_full
js_common, js_order = js_full.split(marker, 1)
# js_order ends with "})();" of the outer IIFE; strip it for re-wrapping
assert js_order.rstrip().endswith('})();')
js_order_body = js_order.rstrip()[:-len('})();')].rstrip()

# --- sections from old page ---
def section_by_id(sec_id):
    m = re.search(r'  <section class="section" id="%s".*?</section>' % sec_id, html, re.S)
    assert m, sec_id
    return m.group(0)

pricing = section_by_id('pricing')
process = section_by_id('process')
order = section_by_id('order')
faq = section_by_id('faq')

# --- backend live (2026-10-28): remove pre-launch placeholders ---
process = process.replace('（正式上线时接通），', '，')
faq = faq.replace('（正式上线时接通），', '，')
order = order.replace('正式上线接通邮箱后，自动回复邮件一般 10 分钟内发到你填写的邮箱。先把订单信息复制下来留存。', '自动回复邮件一般 10 分钟内发到你填写的邮箱，内含收款码和加微信二维码，请查收（也看看垃圾箱）。先把订单信息复制下来留存。')
order = order.replace('自动回复邮件 · 模板预览（正式上线接通邮箱后，提交后自动发到你填写的邮箱）', '自动回复邮件 · 已发送到你填写的邮箱（内含收款码和加微信二维码）')
assert '正式上线' not in process + faq + order

# captcha 2026-10-29：表单加图文验证码行（图片由后端 challenge 发 token，答案只在后端验）
assert order.count('<p class="form-err" id="formErr"></p>') == 1
order = order.replace('<p class="form-err" id="formErr"></p>', '''<div class="captcha-row">
        <label for="capAnswer">验证码</label>
        <img id="capImg" src="" alt="验证码图片" width="150" height="50" />
        <input type="text" id="capAnswer" name="capAnswer" placeholder="输入图中字符" autocomplete="off" maxlength="4" />
        <button type="button" class="btn ghost" id="capRefresh">换一张</button>
      </div>
      <p class="form-err" id="formErr"></p>''')

# Works panels (XHS 1-7): from first work panel to just before pricing section
works_start = html.index('  <!-- 第 1 篇 -->')
works_end = html.index('  <section class="section" id="pricing">')
works = html[works_start:works_end]

# Add data-source="xhs" to every XHS panel, and order link to covers
def add_source_and_order(panels_html):
    out = []
    for m in re.finditer(r'<section class="panel (tall|std)"([^>]*)>(.*?)</section>', panels_html, re.S):
        kind, attrs, body = m.group(1), m.group(2), m.group(3)
        # attrs contain data-series, data-cat, optional id
        if 'data-source' not in attrs:
            attrs = attrs + ' data-source="xhs"'
        # cover panels have id="work-N" and a share-row
        idm = re.search(r'id="(work-\d+)"', attrs)
        if idm and 'share-row' in body:
            catm = re.search(r'data-cat="([^"]+)"', attrs)
            cats = catm.group(1).replace(' ', ',') if catm else 'socks'
            _tm = re.search(r'<h2 class="cap-title"[^>]*>([^<]+)</h2>', body)
            _src = '&source=' + _urlquote(_tm.group(1), safe='') if _tm else ''
            order_link = '<a class="order-btn" href="dingzhi.html#order-items=%s%s">订这篇同款</a>' % (cats, _src)
            body = body.replace('</div>\n  </section>', '</div>')  # noop guard
            # insert order link right after the share button inside share-row
            body = re.sub(r'(<button type="button" class="share-btn"[^>]*>[^<]*</button>)',
                          r'\1' + order_link, body, count=1)
        out.append('<section class="panel %s"%s>%s</section>' % (kind, attrs, body))
    return '\n\n'.join(out)

xhs_panels = add_source_and_order(works)

# --- video panels ---
# Video data lives in videos.json (data file, not code) so an Actions run can
# add a video by updating the JSON + images without editing this script.
import json as _vjson
_VIDEO_RAW = _vjson.load(open(os.path.join(ROOT, 'videos.json'), encoding='utf-8'))
VIDEO = [(v['series'], v['title'], v['date'], v['cats'],
          [(vid, alt) for vid, alt in v['imgs']], v['body']) for v in _VIDEO_RAW]
_VIDEO_SHORTS = '、'.join(v['short'] for v in _VIDEO_RAW)
_VIDEO_COUNT = len(_VIDEO_RAW)
_latest_v = _VIDEO_RAW[-1]
_latest_v_num = _latest_v['series'][1:]
_latest_v_short = _latest_v['title'].split('｜', 1)[1] if '｜' in _latest_v['title'] else _latest_v['title']
_latest_v_cover = _latest_v['imgs'][0][0]

def pic(vid, alt, cover=False):
    fetch = ' fetchpriority="high"' if cover else ' loading="lazy"'
    return ('<picture><source type="image/webp" srcset="images/%s-s.webp 720w, images/%s-l.webp 1344w" sizes="100vw">'
            '<img class="ph" src="images/%s-s.jpg" srcset="images/%s-s.jpg 720w, images/%s-l.jpg 1344w" sizes="100vw" '
            'alt="%s" data-full="images/%s-l.jpg" width="1296" height="1616"%s decoding="async"></picture>'
            % (vid, vid, vid, vid, vid, alt, vid, fetch))

video_panels = []
for series, title, date, cats, imgs, body in VIDEO:
    vid_id = 'video-' + series[1:]
    cover_vid, cover_alt = imgs[0]
    cover = ('  <section class="panel tall" data-series="%s" data-cat="%s" data-source="video" id="%s">\n'
             '    %s\n'
             '    <div class="panel-cap reveal">\n'
             '      <p class="cap-kicker">视频号 · %s · %s</p>\n'
             '      <h2 class="cap-title" style="font-size:clamp(30px,5vw,64px)">%s</h2>\n'
             '      <p class="cap-sub">%s</p>\n'
             '    </div>\n'
             '    <div class="share-row"><button type="button" class="share-btn" data-share="%s">复制本篇链接</button>'
             '<a class="order-btn" href="dingzhi.html#order-items=%s&source=%s">订这篇同款</a><span class="share-tip" aria-live="polite"></span></div>\n'
             '  </section>'
             % (series, cats, vid_id, pic(cover_vid, cover_alt), series, date, title, body, vid_id, cats.replace(' ', ','), _urlquote(title, safe='')))
    video_panels.append(cover)
    for vid, alt in imgs[1:]:
        video_panels.append('  <section class="panel std" data-series="%s" data-cat="%s" data-source="video">%s</section>'
                            % (series, cats, pic(vid, alt)))
video_html = '\n\n'.join(video_panels)

# --- extra CSS ---
extra_css = """
  /* ---------- multi-page v2: nav, cards, search, order-btn ---------- */
  .nav-links a.active{border-bottom-color:#fff;color:#fff;}
  .page-head{max-width:1180px;margin:0 auto;padding:150px clamp(20px,5vw,72px) 10px;}
  .page-head h1{margin:0 0 14px;font-size:clamp(34px,5.4vw,64px);font-weight:900;line-height:1.08;}
  .page-head p{color:var(--dim);font-size:16px;line-height:1.8;letter-spacing:.04em;max-width:720px;}
  .platform-grid{max-width:1180px;margin:0 auto;padding:20px clamp(20px,5vw,72px);display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
  @media (max-width:760px){.platform-grid{grid-template-columns:1fr;}}
  .platform-card{display:block;border:1px solid var(--line);background:var(--panel);color:#fff;text-decoration:none;overflow:hidden;}
  .platform-card img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block;}
  .platform-card-body{padding:20px;}
  .platform-card-body h3{margin:0 0 8px;font-size:20px;}
  .platform-card-body p{margin:0;color:var(--dim);font-size:14px;line-height:1.7;}
  .platform-card:hover{border-color:#fff;}
  .feat-grid{max-width:1180px;margin:0 auto;padding:20px clamp(20px,5vw,72px);display:grid;grid-template-columns:1fr 1fr;gap:18px;}
  @media (max-width:760px){.feat-grid{grid-template-columns:1fr;}}
  .feat-grid a{display:block;border:1px solid var(--line);overflow:hidden;}
  .feat-grid img{width:100%;aspect-ratio:3/4;object-fit:cover;display:block;}
  .search-input{width:100%;max-width:420px;background:transparent;border:1px solid var(--line);color:#fff;font:inherit;font-size:15px;padding:10px 14px;border-radius:0;}
  .search-input:focus{outline:none;border-color:#fff;}
  .order-btn{display:inline-block;margin-left:10px;padding:11px 20px;border:1px solid rgba(255,255,255,.55);color:#fff;text-decoration:none;font-size:13px;letter-spacing:.14em;background:transparent;}
  .order-btn:hover{background:#fff;color:#000;border-color:#fff;}
  .mp-list{max-width:1180px;margin:0 auto;padding:20px clamp(20px,5vw,72px);}
  .mp-card{border:1px solid var(--line);background:var(--panel);padding:24px;margin-bottom:16px;}
  .mp-thumb{width:120px;height:120px;object-fit:cover;border-radius:10px;flex-shrink:0;}
  .mp-gallery{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;}
  .mp-gal{width:72px;height:72px;object-fit:cover;border-radius:6px;cursor:pointer;display:block;}
  .mp-text{flex:1;min-width:0;}
  @media (max-width:600px){.mp-thumb{width:84px;height:84px;}.mp-gal{width:60px;height:60px;}.mp-card{padding:16px;gap:12px;}}
  .mp-card h3{margin:0 0 8px;font-size:20px;line-height:1.4;}
  .mp-card p{margin:0 0 14px;color:var(--dim);font-size:14px;line-height:1.7;}
  .mp-card a{color:#fff;}
  .mp-note{color:var(--dim);font-size:14px;line-height:1.8;letter-spacing:.04em;}
  .section{max-width:1180px;margin:0 auto;padding:60px clamp(20px,5vw,72px);}
  /* ---------- professional batch 2026-10-28: footer, back-to-top, mp filter, lightbox zoom ---------- */
  .site-footer{max-width:1180px;margin:0 auto;padding:28px clamp(20px,5vw,72px) 40px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:14px 32px;align-items:flex-start;justify-content:space-between;color:var(--dim);font-size:13px;line-height:1.8;}
  .site-footer a{color:#fff;text-decoration:none;}
  .site-footer nav{display:flex;flex-wrap:wrap;gap:6px 18px;}
  .site-footer .foot-policy{max-width:640px;}
  #backTop{position:fixed;right:18px;bottom:18px;z-index:60;width:46px;height:46px;border:1px solid var(--line);background:rgba(0,0,0,.72);color:#fff;font-size:20px;cursor:pointer;display:none;}
  #backTop.show{display:block;}
  .mp-filter{max-width:1180px;margin:0 auto;padding:10px clamp(20px,5vw,72px) 0;}
  .lightbox img{touch-action:none;}
  /* 2026-10-28 定制页首屏重叠修复（2026-10-28 晚六项改进时移位）：顶栏 fixed 悬浮、导航背景向下渐隐透明，定制页首个区块只有 60px 上边距会顶到品牌字底下；150px 留白现随首个区块走——此前是 #pricing，六项改进后首个区块改为步骤条 #orderSteps，#pricing 回落到 .section 的 60px */
  #orderSteps{padding-top:150px;}
  /* ---------- SpaceX 式六项改进 2026-10-28 晚：首页面板、信任条、最新时间线、定制步骤条、手机菜单 ---------- */
  .trust-strip{max-width:1180px;margin:0 auto;padding:26px clamp(20px,5vw,72px);display:flex;flex-wrap:wrap;gap:14px 28px;justify-content:center;border-top:1px solid var(--line);border-bottom:1px solid var(--line);color:var(--dim);font-size:14px;letter-spacing:.08em;}
  .trust-strip b{color:#fff;font-size:18px;}
  .latest-list{margin-top:8px;border-top:1px solid var(--line);}
  .latest-row{display:flex;gap:16px;align-items:baseline;padding:16px 0;border-bottom:1px solid var(--line);color:#fff;text-decoration:none;}
  .latest-row:hover .latest-title{text-decoration:underline;}
  .latest-date{color:var(--dim);font-size:13px;white-space:nowrap;}
  .latest-title{flex:1;font-size:16px;line-height:1.6;}
  .latest-src{color:var(--dim);font-size:13px;white-space:nowrap;}
  .order-steps{list-style:none;margin:20px 0 0;padding:0;display:grid;grid-template-columns:repeat(5,1fr);gap:14px;}
  @media (max-width:760px){.order-steps{grid-template-columns:1fr;}}
  .order-steps li{border:1px solid var(--line);background:var(--panel);padding:18px;}
  .order-steps li b{display:block;font-size:15px;margin-bottom:6px;}
  .order-steps li span{color:var(--dim);font-size:13px;line-height:1.7;}
  .order-perks{margin:18px 0 0;color:var(--dim);font-size:14px;letter-spacing:.06em;line-height:1.8;}
  .live-section{padding:clamp(64px,10vh,110px) 0;background:#000;}
  .live-head{max-width:1180px;margin:0 auto;padding:0 clamp(20px,5vw,72px);}
  .live-head .sec-kicker{display:flex;align-items:center;gap:10px;}
  .live-dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:#FF3B30;margin-right:0;}
  .live-sub{color:var(--dim);font-size:15px;letter-spacing:.06em;margin:0 0 22px;}
  .live-player{position:relative;width:100%;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden;}
  .live-player iframe{max-width:100%;border:0;}
  .live-fallback{text-align:center;max-width:680px;padding:56px 24px;margin:0;}
  .live-fallback-big{color:#fff;font-size:clamp(24px,5vw,40px);font-weight:900;line-height:1.4;margin:0;}
  .live-fallback-small{color:var(--dim);font-size:13px;line-height:1.8;margin:18px 0 0;}
  /* ---------- captcha 2026-10-29：图文验证码 ---------- */
  .captcha-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0 2px;}
  .captcha-row label{color:#fff;font-size:15px;}
  .captcha-row img{height:50px;width:150px;object-fit:cover;border-radius:8px;background:#fff;}
  .captcha-row input{font-size:17px;padding:10px 12px;border-radius:10px;border:1px solid #555;background:#111;color:#fff;width:140px;}
  .captcha-row .btn{margin:0;}
  .live-note{max-width:1180px;margin:18px auto 0;padding:0 clamp(20px,5vw,72px);color:var(--dim);font-size:13px;letter-spacing:.04em;}
  .nav-toggle{position:absolute;opacity:0;width:1px;height:1px;}
  .nav-toggle-label{display:none;}
  @media (max-width:600px){
    .site-nav{flex-wrap:wrap;}
    .nav-toggle-label{display:block;margin-left:auto;cursor:pointer;padding:8px 4px;}
    .nav-toggle-label span{display:block;width:24px;height:2px;background:#fff;margin:5px 0;transition:transform .3s ease,opacity .3s ease;}
    .nav-toggle:checked + .nav-toggle-label span:nth-child(1){transform:translateY(12px) rotate(45deg);}
    .nav-toggle:checked + .nav-toggle-label span:nth-child(2){opacity:0;}
    .nav-toggle:checked + .nav-toggle-label span:nth-child(3){transform:translateY(-12px) rotate(-45deg);}
    .nav-links{display:none;width:100%;flex-direction:column;gap:10px;padding-top:12px;}
    .nav-toggle:checked ~ .nav-links{display:flex;}
  }
  /* ---------- 高端细节 2026-10-28 晚：页脚 X 图标、favicon、滚动与焦点细节 ---------- */
  html{scroll-behavior:smooth;}
  @media (prefers-reduced-motion: reduce){html{scroll-behavior:auto;}}
  ::selection{background:#fff;color:#000;}
  a:focus-visible,button:focus-visible{outline:1px solid #fff;outline-offset:3px;}
  @media (prefers-reduced-motion: no-preference){.scroll-hint{animation:hintPulse 2.4s ease-in-out infinite;}}
  @keyframes hintPulse{0%,100%{opacity:.55}50%{opacity:1}}
  .foot-social{display:flex;align-items:center;}
  .foot-social a{display:block;}
  .foot-social svg{width:19px;height:19px;fill:#fff;display:block;}
  .foot-social a:hover svg{fill:var(--dim);}
  /* ---------- SpaceX 化五项 2026-10-28 晚：按钮横扫、面板全黑渐隐、首图慢缩放、手机全屏菜单、信任条压暗 ---------- */
  .btn.ghost{position:relative;isolation:isolate;overflow:hidden;transition:color .45s;}
  .btn.ghost::after{content:"";position:absolute;inset:0;background:#fff;transform:scaleX(0);transform-origin:left center;transition:transform .45s cubic-bezier(.22,1,.36,1);z-index:-1;}
  .btn.ghost:hover{background:transparent;color:#000;}
  .btn.ghost:hover::after{transform:scaleX(1);}
  .panel.std.home-panel::after{background:linear-gradient(180deg,rgba(0,0,0,.34) 0%,rgba(0,0,0,0) 26%,rgba(0,0,0,0) 55%,rgba(0,0,0,.85) 78%,rgba(0,0,0,1) 100%);}
  @keyframes heroZoom{from{transform:scale(1);}to{transform:scale(1.08);}}
  .panel.hero > picture > img.ph{animation:heroZoom 30s ease-out forwards;}
  @media (prefers-reduced-motion:reduce){.panel.hero > picture > img.ph{animation:none;}}
  @media (max-width:600px){
    .nav-toggle:checked ~ .nav-links{position:fixed;inset:0;z-index:1;background:rgba(0,0,0,.97);display:flex;flex-direction:column;justify-content:center;align-items:center;gap:32px;padding:0;}
    .nav-toggle:checked ~ .nav-links a{font-size:20px;letter-spacing:.3em;padding:10px 0;}
    .brand{position:relative;z-index:2;}
    .nav-toggle-label{position:relative;z-index:2;}
  }
  .trust-strip{border:0;padding:18px clamp(20px,5vw,72px);font-size:12px;letter-spacing:.06em;color:var(--faint);}
  .trust-strip b{color:var(--dim);font-size:14px;}
  /* ---------- 字号层级收紧 2026-10-28 晚（第 6 项）：标题并为一档、微小字号统一 ---------- */
  .mp-card h3,.platform-card-body h3,.faq-q,.price-name{font-size:clamp(19px,2.4vw,26px);}
  .scroll-hint{font-size:12px;}
  .pick-name,.page-head p,.latest-title{font-size:15px;}
  /* ---------- 移动端防缩放 2026-10-28 晚（数量键连点放大 bug）：禁双击缩放＋输入框 16px 防聚焦缩放 ---------- */
  button,a,input,select,textarea{touch-action:manipulation;}
  .pick-qty input,.search-input{font-size:16px;}
"""

# --- extra JS (appended to common) ---
extra_js = """
  /* ---------- multi-page v2: nav active, old share redirect, search ---------- */
  (function(){
    var path = location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(function(a){
      if (a.getAttribute('href') === path) a.classList.add('active');
    });
    var isHome = (path === '' || path === 'index.html');
    var h = location.hash || '';
    if (isHome && /^#(work-\\d+)$/.test(h)) { location.replace('xiaohongshu.html' + h); return; }
    if (isHome && /^#(video-\\d+)$/.test(h)) { location.replace('shipinhao.html' + h); return; }
  })();
  /* ---------- professional batch 2026-10-28: back-to-top ---------- */
  (function(){
    var bt = document.getElementById("backTop");
    if (!bt) return;
    window.addEventListener("scroll", function(){ bt.classList.toggle("show", window.scrollY > 600); }, {passive:true});
    bt.addEventListener("click", function(){ window.scrollTo({top:0, behavior:"smooth"}); });
  })();
  /* ---------- panel 图片断网自愈 2026-10-28 晚（黑屏面板）：失败自动换 jpg／带退避重试 ---------- */
  (function(){
    function jpgFor(u){
      if (!u || u.indexOf('.webp') < 0) return null;
      return u.replace(/\.webp(\?.*)?$/, '.jpg$1');
    }
    function arm(img){
      if (img._retryArmed) return;
      img._retryArmed = true;
      img._retryStep = 0;
      img.addEventListener('error', function(){
        var step = img._retryStep;
        if (step >= 3) return;
        img._retryStep = step + 1;
        var cur = img.currentSrc || img.getAttribute('src') || '';
        if (!cur) return;
        var next = null;
        if (step === 0) next = jpgFor(cur);
        if (!next) next = cur.split('?')[0] + '?retry=' + step + '&t=' + Date.now();
        setTimeout(function(){
          img.removeAttribute('srcset');
          var pic = (img.parentNode && img.parentNode.tagName === 'PICTURE') ? img.parentNode : null;
          if (pic) { var ss = pic.querySelectorAll('source'); for (var i = 0; i < ss.length; i++) ss[i].removeAttribute('srcset'); }
          img.src = next;
        }, step === 0 ? 0 : 1500 * step);
      });
    }
    function init(){
      var imgs = document.querySelectorAll('img.ph');
      for (var i = 0; i < imgs.length; i++) {
        arm(imgs[i]);
        if (imgs[i].complete && imgs[i].naturalWidth === 0) {
          (function(im){ setTimeout(function(){ im.dispatchEvent(new Event('error')); }, 100); })(imgs[i]);
        }
      }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
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
      var timer = setTimeout(fail, 15000);
      var s = document.createElement("script");
      s.async = true; s.src = "https://platform.x.com/widgets.js";
      s.onerror = function(){ clearTimeout(timer); fail(); };
      s.onload = function(){
        function render(){
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
            } else if (tries >= 20) { clearInterval(iv); clearTimeout(timer); fail(); }
          }, 500);
        }
        if (window.twttr && twttr.ready) { twttr.ready(function(){ render(); }); }
        else { render(); }
      };
      document.head.appendChild(s);
    }).catch(function(){ showFallback(); });
  })();
"""

# Patch filter JS: add search
assert 'var curCat = "all", curSeries = "all";' in js_common
js_common = js_common.replace(
    'var curCat = "all", curSeries = "all";',
    'var curCat = "all", curSeries = "all", curSearch = "";')
assert 'var ok = okCat && okSeries;' in js_common
js_common = js_common.replace(
    'var ok = okCat && okSeries;',
    'var txt = (panel.textContent || "") + " " + Array.prototype.map.call(panel.querySelectorAll("img"), function(i){ return i.alt || ""; }).join(" ");\n'
    '      var okSearch = !curSearch || txt.toLowerCase().indexOf(curSearch) !== -1;\n'
    '      var ok = okCat && okSeries && okSearch;')
# Bind search after bindChips calls
assert 'bindChips("data-series-filter", function(v){ curSeries = v; });' in js_common
js_common = js_common.replace(
    'bindChips("data-series-filter", function(v){ curSeries = v; });',
    'bindChips("data-series-filter", function(v){ curSeries = v; });\n'
    '  var searchEl = document.getElementById("workSearch");\n'
    '  if (searchEl) { searchEl.addEventListener("input", function(){ curSearch = searchEl.value.trim().toLowerCase(); applyFilter(); }); }')

# Patch lightbox: group-scoped viewing for MP galleries (2026-10-28).
# Gallery images carry class "ph mp-gal" + data-group="mpXX". Clicking one
# scopes the lightbox to that article only; images without data-group keep
# the existing global behaviour (XHS/video pages are unaffected).
assert '  allPhotos.forEach(function(img){\n    img.addEventListener("click", function(){\n      refreshPhotos();\n      var i = photos.indexOf(img);\n      openLb(i === -1 ? 0 : i);\n    });\n  });' in js_common
js_common = js_common.replace(
    '  allPhotos.forEach(function(img){\n    img.addEventListener("click", function(){\n      refreshPhotos();\n      var i = photos.indexOf(img);\n      openLb(i === -1 ? 0 : i);\n    });\n  });',
    '  allPhotos.forEach(function(img){\n    img.addEventListener("click", function(){\n      var grp = img.getAttribute("data-group");\n      if (grp) {\n        photos = allPhotos.filter(function(p){ return p.getAttribute("data-group") === grp; });\n      } else {\n        refreshPhotos();\n      }\n      var i = photos.indexOf(img);\n      openLb(i === -1 ? 0 : i);\n    });\n  });')

# Patch lightbox: swipe-down-to-close (2026-10-28, user real-device report).
# Dragging the enlarged photo downward did nothing (only the X button closed
# it). A downward drag (dy > 80, vertical-dominant) now closes the lightbox,
# for both touch swipe and mouse drag, via the shared swipeEnd path.
# Horizontal prev/next is untouched (it requires abs(dx) > abs(dy)); a small
# diagonal drag triggers neither branch, so no accidental close.
assert '  function swipeEnd(dx, dy){\n    if (swipeX === null) return;\n    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)){\n      if (dx < 0) show(idx + 1); else show(idx - 1);\n      /* a drag that ends outside the image would otherwise also fire a\n         backdrop click and close the lightbox right after switching */\n      suppressLbClick = true;\n    }\n    swipeX = null; swipeY = null;\n  }' in js_common
js_common = js_common.replace(
    '  function swipeEnd(dx, dy){\n    if (swipeX === null) return;\n    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)){\n      if (dx < 0) show(idx + 1); else show(idx - 1);\n      /* a drag that ends outside the image would otherwise also fire a\n         backdrop click and close the lightbox right after switching */\n      suppressLbClick = true;\n    }\n    swipeX = null; swipeY = null;\n  }',
    '  function swipeEnd(dx, dy){\n    if (swipeX === null) return;\n    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)){\n      if (dx < 0) show(idx + 1); else show(idx - 1);\n      /* a drag that ends outside the image would otherwise also fire a\n         backdrop click and close the lightbox right after switching */\n      suppressLbClick = true;\n    }\n    /* drag the photo downward to dismiss (swipe-down-to-close) */\n    if (dy > 80 && Math.abs(dy) > Math.abs(dx)){\n      closeLb();\n      suppressLbClick = true;\n    }\n    swipeX = null; swipeY = null;\n  }')

# Patch lightbox: pinch/double-tap/wheel zoom + wide-screen large image
# (2026-10-28 professional batch). Zoom state resets on every image switch
# and on close, so zoom never leaks into the next photo. When zoomed, a
# one-finger drag pans (touch) instead of switching/closing; swipe behaviour
# at 1x is unchanged. Desktop: double-click toggles 2x, wheel zooms 1x-3x.
assert '  function show(i){\n    idx = (i + photos.length) % photos.length;\n    lbImg.src = photos[idx].getAttribute("data-full");\n    lbImg.alt = photos[idx].alt;\n    lbCount.textContent = (idx + 1) + " / " + photos.length;\n  }' in js_common
js_common = js_common.replace(
    '  function show(i){\n    idx = (i + photos.length) % photos.length;\n    lbImg.src = photos[idx].getAttribute("data-full");\n    lbImg.alt = photos[idx].alt;\n    lbCount.textContent = (idx + 1) + " / " + photos.length;\n  }',
    '  var lbScale = 1, lbPanX = 0, lbPanY = 0;\n'
    '  function applyLbTransform(){\n'
    '    lbImg.style.transform = (lbScale === 1 && lbPanX === 0 && lbPanY === 0) ? "" : "translate(" + lbPanX + "px," + lbPanY + "px) scale(" + lbScale + ")";\n'
    '  }\n'
    '  function show(i){\n'
    '    idx = (i + photos.length) % photos.length;\n'
    '    var fullL = photos[idx].getAttribute("data-full-l");\n'
    '    lbImg.src = (window.innerWidth > 900 && fullL) ? fullL : photos[idx].getAttribute("data-full");\n'
    '    lbImg.alt = photos[idx].alt;\n'
    '    lbCount.textContent = (idx + 1) + " / " + photos.length;\n'
    '    lbScale = 1; lbPanX = 0; lbPanY = 0; applyLbTransform();\n'
    '  }')
assert '  function closeLb(){ lb.classList.remove("open"); document.body.style.overflow = ""; }' in js_common
js_common = js_common.replace(
    '  function closeLb(){ lb.classList.remove("open"); document.body.style.overflow = ""; }',
    '  function closeLb(){ lbScale = 1; lbPanX = 0; lbPanY = 0; lbImg.style.transform = ""; lb.classList.remove("open"); document.body.style.overflow = ""; }')
assert '  function swipeEnd(dx, dy){\n    if (swipeX === null) return;' in js_common
js_common = js_common.replace(
    '  function swipeEnd(dx, dy){\n    if (swipeX === null) return;',
    '  function swipeEnd(dx, dy){\n    if (swipeX === null) return;\n    if (lbScale > 1){ swipeX = null; swipeY = null; return; }')
assert '  lb.addEventListener("touchstart", function(e){\n    if (!lb.classList.contains("open")) return;\n    var t = e.changedTouches[0];\n    swipeX = t.clientX; swipeY = t.clientY;\n  }, {passive:true});\n  lb.addEventListener("touchend", function(e){\n    if (swipeX === null) return;\n    var t = e.changedTouches[0];\n    swipeEnd(t.clientX - swipeX, t.clientY - swipeY);\n  }, {passive:true});\n  lb.addEventListener("touchcancel", function(){ swipeX = null; swipeY = null; }, {passive:true});' in js_common
js_common = js_common.replace(
    '  lb.addEventListener("touchstart", function(e){\n    if (!lb.classList.contains("open")) return;\n    var t = e.changedTouches[0];\n    swipeX = t.clientX; swipeY = t.clientY;\n  }, {passive:true});\n  lb.addEventListener("touchend", function(e){\n    if (swipeX === null) return;\n    var t = e.changedTouches[0];\n    swipeEnd(t.clientX - swipeX, t.clientY - swipeY);\n  }, {passive:true});\n  lb.addEventListener("touchcancel", function(){ swipeX = null; swipeY = null; }, {passive:true});',
    '  var pinchDist = 0, pinchScaleStart = 1, isPinch = false, lastTapTime = 0, panStartX = 0, panStartY = 0, panBaseX = 0, panBaseY = 0;\n'
    '  function pinchDistance(e){\n'
    '    var a = e.touches[0], b = e.touches[1];\n'
    '    return Math.sqrt((a.clientX - b.clientX) * (a.clientX - b.clientX) + (a.clientY - b.clientY) * (a.clientY - b.clientY));\n'
    '  }\n'
    '  lb.addEventListener("touchstart", function(e){\n'
    '    if (!lb.classList.contains("open")) return;\n'
    '    if (e.touches.length === 2){ isPinch = true; pinchDist = pinchDistance(e); pinchScaleStart = lbScale; swipeX = null; swipeY = null; return; }\n'
    '    var t = e.changedTouches[0];\n'
    '    swipeX = t.clientX; swipeY = t.clientY;\n'
    '    if (lbScale > 1){ panStartX = t.clientX; panStartY = t.clientY; panBaseX = lbPanX; panBaseY = lbPanY; }\n'
    '  }, {passive:true});\n'
    '  lb.addEventListener("touchmove", function(e){\n'
    '    if (!lb.classList.contains("open")) return;\n'
    '    if (isPinch && e.touches.length === 2){\n'
    '      var d = pinchDistance(e);\n'
    '      if (pinchDist > 0){ lbScale = Math.max(1, Math.min(3, pinchScaleStart * d / pinchDist)); applyLbTransform(); }\n'
    '      return;\n'
    '    }\n'
    '    if (lbScale > 1 && e.touches.length === 1){\n'
    '      var t = e.touches[0];\n'
    '      var span = 90 * lbScale;\n'
    '      lbPanX = Math.max(-span, Math.min(span, panBaseX + (t.clientX - panStartX)));\n'
    '      lbPanY = Math.max(-span, Math.min(span, panBaseY + (t.clientY - panStartY)));\n'
    '      applyLbTransform();\n'
    '    }\n'
    '  }, {passive:true});\n'
    '  lb.addEventListener("touchend", function(e){\n'
    '    if (isPinch){ isPinch = false; if (lbScale < 1.15){ lbScale = 1; lbPanX = 0; lbPanY = 0; applyLbTransform(); } swipeX = null; swipeY = null; return; }\n'
    '    if (swipeX === null) return;\n'
    '    var t = e.changedTouches[0];\n'
    '    var dx = t.clientX - swipeX, dy = t.clientY - swipeY;\n'
    '    var now = Date.now();\n'
    '    if (Math.abs(dx) < 12 && Math.abs(dy) < 12 && now - lastTapTime < 300){\n'
    '      lastTapTime = 0;\n'
    '      if (lbScale > 1){ lbScale = 1; lbPanX = 0; lbPanY = 0; } else { lbScale = 2; }\n'
    '      applyLbTransform(); swipeX = null; swipeY = null; return;\n'
    '    }\n'
    '    if (Math.abs(dx) < 12 && Math.abs(dy) < 12) lastTapTime = now;\n'
    '    swipeEnd(dx, dy);\n'
    '  }, {passive:true});\n'
    '  lb.addEventListener("touchcancel", function(){ isPinch = false; swipeX = null; swipeY = null; }, {passive:true});\n'
    '  lbImg.addEventListener("dblclick", function(){\n'
    '    if (!lb.classList.contains("open")) return;\n'
    '    if (lbScale > 1){ lbScale = 1; lbPanX = 0; lbPanY = 0; } else { lbScale = 2; }\n'
    '    applyLbTransform();\n'
    '  });\n'
    '  lbImg.addEventListener("wheel", function(e){\n'
    '    if (!lb.classList.contains("open")) return;\n'
    '    var step = e.deltaY < 0 ? 0.25 : -0.25;\n'
    '    var ns = Math.max(1, Math.min(3, lbScale + step));\n'
    '    if (ns === 1){ lbPanX = 0; lbPanY = 0; }\n'
    '    lbScale = ns; applyLbTransform();\n'
    '  }, {passive:true});')
# Order-items hash handling, appended to order JS (2026-10-28 professional
# batch: order-through now also carries the work title, so the shop knows
# WHICH work the customer means; old plain #order-items=cats links still work).
order_hash_js = """
  /* ---------- multi-page v2: order-items + source work from a work page ---------- */
  (function(){
    var raw = (location.hash || '').replace(/^#/, '');
    var params = {};
    raw.split('&').forEach(function(pair){
      var eq = pair.indexOf('=');
      if (eq > 0) params[pair.slice(0, eq)] = pair.slice(eq + 1);
    });
    if (!params['order-items']) return;
    var CAT2IDX = { socks: 0, underwear: 2, cloth: 3, shirt: 4, trousers: 5, leather: 6 };
    params['order-items'].split(',').forEach(function(cat){
      var i = CAT2IDX[cat];
      if (i === undefined) return;
      var cb = document.getElementById('pick-' + i);
      if (cb && !cb.checked) { cb.checked = true; cb.dispatchEvent(new Event('change')); }
    });
    var srcTitle = '';
    if (params['source']) {
      try { srcTitle = decodeURIComponent(params['source']); } catch (e) { srcTitle = ''; }
    }
    if (srcTitle) {
      window.__orderSource = srcTitle;
      var ord = document.getElementById('order');
      if (ord) {
        var note = document.createElement('p');
        note.id = 'orderSource';
        note.style.cssText = 'color:#fff;font-size:15px;line-height:1.8;margin:0 0 16px;';
        note.textContent = '订这篇同款：' + srcTitle + '（已勾好对应单品，备注里可补充细节）';
        var form = ord.querySelector('form');
        if (form && form.parentNode) form.parentNode.insertBefore(note, form);
        else ord.insertBefore(note, ord.firstChild);
      }
    }
    var ord2 = document.getElementById('order');
    if (ord2) ord2.scrollIntoView();
  })();
"""

style_css = css + extra_css
site_js = js_common + extra_js + '\n})();\n'

# --- backend live (2026-10-28): wire order form to Apps Script ---
SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbyeYeJLDi_GgVa3z3f8f63Q82Al1h-6NEbshppt_gan7IbrxhR4crPHzwjHDlxw_MO6/exec'
js_order_body = js_order_body.replace('请按下面的收款码扫码付款', '请按附件里的收款码扫码付款')
js_order_body = js_order_body.replace('付款后加微信，备注订单参考号，并发付款截图', '付款后按附件里的加微信二维码加微信，备注订单参考号，并发付款截图')
js_order_body = re.sub(r' *\"收款码位：上线时放入你的收款码\\n\" \+\n *\"加微信二维码／微信号位：上线时放入你的加微信二维码／微信号\\n\\n\" \+\n', '', js_order_body)
assert '上线时放入' not in js_order_body
# captcha 2026-10-29：提交前校验验证码非空（答案本身由后端验）
assert js_order_body.count('err.classList.remove("show");') == 1
js_order_body = js_order_body.replace('''    if (!address) {
      err.textContent = "请填写收货地址。";
      err.classList.add("show");
      return;
    }
    err.classList.remove("show");''', '''    if (!address) {
      err.textContent = "请填写收货地址。";
      err.classList.add("show");
      return;
    }
    var capAnswerEl = document.getElementById("capAnswer");
    var capAnswer = capAnswerEl ? capAnswerEl.value.trim() : "";
    if (!capAnswer) {
      err.textContent = "请填写验证码。";
      err.classList.add("show");
      return;
    }
    err.classList.remove("show");''')
old_tail = '''    document.getElementById("refNo").textContent = ref;
    document.getElementById("mailBody").textContent = lastMailText;
    form.style.display = "none";
    document.getElementById("successBox").classList.add("show");
    document.getElementById("successBox").scrollIntoView({ behavior: "smooth", block: "center" });
  });'''
new_tail = '''    var payloadItems = [];
    ITEMS.forEach(function(item){
      if (item._cb.checked) {
        var q = parseInt(item._qty.value, 10);
        if (isNaN(q) || q < 1) q = 1;
        payloadItems.push({ name: item.name, price: item.price, qty: q });
      }
    });
    var submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;
    fetch(SCRIPT_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify({ ref: ref, contact: contact, email: email, repeatRef: repeatRef, recipient: recipient, phone: phone, address: address, note: note, items: payloadItems, source: (window.__orderSource || ''), captchaToken: capToken, captchaAnswer: capAnswer }) }).then(function(r){ return r.json(); }).then(function(res){
      if (res && res.ok) {
        document.getElementById("successBox").querySelector("p").textContent = "提交成功";
        document.getElementById("refNo").textContent = ref;
        document.getElementById("mailBody").textContent = lastMailText;
        form.style.display = "none";
        document.getElementById("successBox").classList.add("show");
        document.getElementById("successBox").scrollIntoView({ behavior: "smooth", block: "center" });
      } else if (res && (res.error === 'captcha' || res.error === 'captcha_expired')) {
        err.textContent = (res.error === 'captcha_expired') ? "验证码已过期，请重新填写。" : "验证码不对，请重新填写。";
        err.classList.add("show");
        refreshCaptcha();
        if (submitBtn) submitBtn.disabled = false;
      } else {
        document.getElementById("successBox").querySelector("p").textContent = "提交未成功，订单信息已生成，请先复制保存，再点再次提交重试";
        document.getElementById("refNo").textContent = ref;
        document.getElementById("mailBody").textContent = lastMailText;
        document.getElementById("successBox").classList.add("show");
        err.textContent = "提交失败，请点再次提交重试；也可以先复制订单信息保存。";
        err.classList.add("show");
        if (submitBtn) submitBtn.disabled = false;
      }
    }).catch(function(){
      document.getElementById("successBox").querySelector("p").textContent = "提交未成功，订单信息已生成，请先复制保存，再点再次提交重试";
      document.getElementById("refNo").textContent = ref;
      document.getElementById("mailBody").textContent = lastMailText;
      document.getElementById("successBox").classList.add("show");
      err.textContent = "提交失败，网络未连通，请点再次提交重试；也可以先复制订单信息保存。";
      err.classList.add("show");
      if (submitBtn) submitBtn.disabled = false;
    });
  });'''
assert old_tail in js_order_body
js_order_body = js_order_body.replace(old_tail, new_tail)
# captcha 2026-10-29：challenge 取图＋token（答案只在后端脚本里验，前端只传 token＋答案）
js_order_body += '''
  /* ---------- captcha：challenge 取图 ---------- */
  var capToken = "";
  function refreshCaptcha(){
    var img = document.getElementById("capImg");
    fetch(SCRIPT_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: JSON.stringify({ action: 'challenge' }) }).then(function(r){ return r.json(); }).then(function(res){
      if (res && res.ok && res.img) { capToken = res.token; if (img) img.src = 'images/captcha/' + res.img; }
    }).catch(function(){});
  }
  (function(){
    var btn = document.getElementById("capRefresh");
    if (btn) btn.addEventListener("click", refreshCaptcha);
  })();
  refreshCaptcha();
'''
order_js = '(function(){\n' + marker + '\nvar SCRIPT_URL = \'' + SCRIPT_URL + '\';\n' + js_order_body + order_hash_js + '\n})();\n'

# 2026-10-28 晚：样式/脚本链接带内容哈希版本号，内容一变地址就变，访客手机不再沿用旧缓存（此前用户手机缓存旧 style.css，修复后仍显重叠）
_css_v = hashlib.md5(style_css.encode('utf-8')).hexdigest()[:8]
_js_v = hashlib.md5(site_js.encode('utf-8')).hexdigest()[:8]
_order_v = hashlib.md5(order_js.encode('utf-8')).hexdigest()[:8]

NAV = """<header class="site-head">
  <nav class="site-nav">
    <a class="brand" href="index.html">杨树 <span>598</span></a>
    <input type="checkbox" id="navToggle" class="nav-toggle" aria-label="展开或收起导航菜单" />
    <label for="navToggle" class="nav-toggle-label" aria-label="展开或收起导航菜单"><span></span><span></span><span></span></label>
    <div class="nav-links">
      <a href="index.html">首页</a>
      <a href="xiaohongshu.html">小红书</a>
      <a href="shipinhao.html">视频号</a>
      <a href="gongzhonghao.html">公众号</a>
      <a href="dingzhi.html">定制</a>
    </div>
  </nav>
</header>"""

LIGHTBOX = """<div class="lightbox" id="lightbox" role="dialog" aria-label="图片放大查看">
  <img id="lbImg" alt="" draggable="false" />
  <button class="lb-btn lb-close" id="lbClose" aria-label="关闭">✕</button>
  <button class="lb-btn lb-prev" id="lbPrev" aria-label="上一张">‹</button>
  <button class="lb-btn lb-next" id="lbNext" aria-label="下一张">›</button>
  <div class="lb-count" id="lbCount"></div>
</div>"""

FOOTER = """<footer class="site-footer">
  <div><a href="index.html">杨树 598</a><br />© 2026 杨树 598 · 作品与定制</div>
  <nav aria-label="页脚导航">
    <a href="index.html">首页</a>
    <a href="xiaohongshu.html">小红书</a>
    <a href="shipinhao.html">视频号</a>
    <a href="gongzhonghao.html">公众号</a>
    <a href="dingzhi.html">定制</a>
  </nav>
  <div class="foot-social"><a href="https://x.com/dayangshu1975" target="_blank" rel="noopener" aria-label="杨树598 的 X 主页"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"/></svg></a></div>
  <p class="foot-policy">定制接单：交期 10 天内，包装保密，不支持退换；满 ¥58 包邮，满 ¥200 送牛奶。信息仅用于订单联系和发货，不公开。定制请走定制页表单。</p>
</footer>"""

def page(title, desc, og_image, body, extra_scripts='', canonical=''):
    _canon = '<link rel="canonical" href="%s" />\n' % canonical if canonical else ''
    _html = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n'
            '<meta charset="utf-8" />\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />\n'
            '<meta name="color-scheme" content="dark" />\n'
            '<meta name="description" content="%s" />\n'
            '<meta property="og:title" content="%s" />\n'
            '<meta property="og:description" content="%s" />\n'
            '<meta property="og:type" content="website" />\n'
            '<meta property="og:image" content="%s" />\n'
            '<meta name="twitter:card" content="summary_large_image" />\n'
            '%s'
            '<title>%s</title>\n'
            '<link rel="stylesheet" href="style.css" />\n'
            '<link rel="icon" type="image/svg+xml" href="favicon.svg?v=b2" />\n'
            '</head>\n<body>\n%s\n<main id="top">\n%s\n</main>\n%s\n%s\n'
            '<button id="backTop" aria-label="回到顶部">↑</button>\n'
            '<script src="site.js"></script>\n%s\n</body>\n</html>\n'
            % (desc, title, desc, og_image, _canon, title, NAV, body, FOOTER, LIGHTBOX, extra_scripts))
    return _html.replace('href="style.css"', 'href="style.css?v=' + _css_v + '"').replace('src="site.js"', 'src="site.js?v=' + _js_v + '"')

def filter_block(series_chips, series_label='系列'):
    return ('  <div class="filter-wrap" id="filterWrap">\n'
            '    <div class="filter-group" role="group" aria-label="按单品筛选">\n'
            '      <span class="filter-label">单品</span>\n'
            '      <button type="button" class="chip active" data-cat-filter="all">全部</button>\n'
            '      <button type="button" class="chip" data-cat-filter="socks">袜子</button>\n'
            '      <button type="button" class="chip" data-cat-filter="underwear">内裤</button>\n'
            '      <button type="button" class="chip" data-cat-filter="shirt">衬衫</button>\n'
            '      <button type="button" class="chip" data-cat-filter="trousers">西裤</button>\n'
            '      <button type="button" class="chip" data-cat-filter="leather">皮鞋</button>\n'
            '      <button type="button" class="chip" data-cat-filter="cloth">布鞋</button>\n'
            '    </div>\n'
            '    <div class="filter-group" role="group" aria-label="按系列筛选">\n'
            '      <span class="filter-label">%s</span>\n%s\n'
            '    </div>\n'
            '    <div class="filter-group" role="group" aria-label="搜索">\n'
            '      <span class="filter-label">搜索</span>\n'
            '      <input type="search" class="search-input" id="workSearch" placeholder="搜作品，如墨绿袜、领带、书店" aria-label="搜索作品" />\n'
            '    </div>\n'
            '    <p class="filter-count" id="filterCount"></p>\n'
            '    <p class="filter-empty" id="filterEmpty">这个分类下暂时没有作品图，换个分类看看。</p>\n'
            '  </div>\n' % (series_label, series_chips))

xhs_series = ('      <button type="button" class="chip active" data-series-filter="all">全部</button>\n' +
              ''.join('      <button type="button" class="chip" data-series-filter="%d">第 %d 篇</button>\n' % (i, i) for i in range(1, 8)))
vid_series = ('      <button type="button" class="chip active" data-series-filter="all">全部</button>\n' +
              ''.join('      <button type="button" class="chip" data-series-filter="%s">第 %s 篇</button>\n' % (v['series'], v['series'][1:]) for v in _VIDEO_RAW))

# --- HOME ---
# Newest MP article (for the home "latest" block): first entry of the same
# baseline the MP page is built from, so home and MP page cannot drift apart.
_latest_mp_title = _latest_mp_date = ''
for _bl in open(os.path.join(ROOT, 'mp-published-baseline-20261028.md'), encoding='utf-8').read().splitlines():
    _bm = re.match(r'^\d+\.\s+(.+?)\s+—\s+(\d{4}-\d{2}-\d{2})(?:\s+\d{2}:\d{2})?\s+—\s+(https://\S+)\s*$', _bl)
    if _bm:
        _latest_mp_title, _latest_mp_date = _bm.group(1), _bm.group(2)
        break
assert _latest_mp_title, 'no MP baseline entry for home latest block'
hero_start = html.index('  <!-- HERO -->')
hero_end = html.index('  <div id="works"></div>')
hero = html[hero_start:hero_end]
# hero CTA anchors pointed at the old single page; repoint to the new pages.
hero = hero.replace('href="#works"', 'href="xiaohongshu.html"').replace('href="#order"', 'href="dingzhi.html#order"')
home_body = hero + """
  <section class="live-section" id="liveSection">
    <div class="live-head">
      <p class="sec-kicker"><span class="live-dot"></span>LIVE · 慢直播</p>
      <h2 class="sec-title">慢直播</h2>
      <p class="live-sub" id="liveSub"></p>
    </div>
    <div class="live-player" id="livePlayer">
      <div class="live-fallback" id="liveFallback"><p class="live-fallback-big">这不是你的错，也并非我的问题</p><p class="live-fallback-small">很抱歉，我在你所在的国家/地区似乎尚不可用。</p></div>
    </div>
    <p class="live-note" id="liveNote">来源：黄石老忠实 / NASA+（公有领域画面）· 播放器由 X 提供</p>
  </section>
  <section class="panel std home-panel">
    <picture><source type="image/webp" srcset="images/img25-s.webp 720w, images/img25-l.webp 1344w" sizes="100vw"><img class="ph" src="images/img25-s.jpg" srcset="images/img25-s.jpg 720w, images/img25-l.jpg 1344w" sizes="100vw" alt="小红书第 7 篇 · 周日午后他教我系领带" data-full="images/img25-l.jpg" loading="lazy" decoding="async" /></picture>
    <div class="panel-cap reveal">
      <p class="cap-kicker">小红书最新</p>
      <h2 class="cap-title">周日午后他教我系领带</h2>
      <p class="cap-sub">你的叔 · 第 7 篇 · 2026-10-27</p>
      <div class="cta-row"><a class="btn" href="xiaohongshu.html#work-7">看这篇</a></div>
    </div>
  </section>
  <section class="panel std home-panel">
    <picture><source type="image/webp" srcset="images/__LATEST_VIDEO_COVER__-s.webp 720w, images/__LATEST_VIDEO_COVER__-l.webp 1344w" sizes="100vw"><img class="ph" src="images/__LATEST_VIDEO_COVER__-s.jpg" srcset="images/__LATEST_VIDEO_COVER__-s.jpg 720w, images/__LATEST_VIDEO_COVER__-l.jpg 1344w" sizes="100vw" alt="__LATEST_VIDEO_ALT__" data-full="images/__LATEST_VIDEO_COVER__-l.jpg" loading="lazy" decoding="async" /></picture>
    <div class="panel-cap reveal">
      <p class="cap-kicker">视频号最新</p>
      <h2 class="cap-title">__LATEST_VIDEO_TITLE__</h2>
      <p class="cap-sub">你的叔 · 第 __LATEST_VIDEO_NUM__ 篇 · __LATEST_VIDEO_DATE__</p>
      <div class="cta-row"><a class="btn" href="shipinhao.html#video-__LATEST_VIDEO_NUM__">看这篇</a></div>
    </div>
  </section>
  <section class="section">
    <p class="sec-kicker">Latest</p>
    <h2 class="sec-title">最近更新</h2>
    <div class="latest-list">
      <a class="latest-row" href="shipinhao.html#video-__LATEST_VIDEO_NUM__"><span class="latest-date">__LATEST_VIDEO_DATE__</span><span class="latest-title">__LATEST_VIDEO_TITLE__</span><span class="latest-src">视频号</span></a>
      <a class="latest-row" href="gongzhonghao.html#mp-01"><span class="latest-date">__LATEST_MP_DATE__</span><span class="latest-title">__LATEST_MP_TITLE__</span><span class="latest-src">公众号</span></a>
      <a class="latest-row" href="xiaohongshu.html#work-7"><span class="latest-date">2026-10-27</span><span class="latest-title">周日午后他教我系领带</span><span class="latest-src">小红书</span></a>
    </div>
    <p class="sec-note">小红书上新以店主通知为准，视频号发表后自动上站，公众号每日核对同步。</p>
  </section>
  <div class="trust-strip"><span><b>64</b> 篇公众号</span><span><b>7</b> 篇小红书</span><span><b>__VIDEO_COUNT__</b> 篇视频号</span><span>交期 <b>10 天内</b></span><span>满 <b>¥58</b> 包邮</span><span>满 <b>¥200</b> 送牛奶</span></div>
  <section class="section">
    <p class="sec-kicker">Custom Order</p>
    <h2 class="sec-title">定制接单</h2>
    <p class="sec-note">选单品、填表单、查收邮件、扫码付款、付款后加微信确认。交期 10 天内，包装保密，不支持退换。满 ¥58 包邮，满 ¥200 送牛奶。</p>
    <div class="cta-row" style="margin-top:20px">
      <a class="btn" href="dingzhi.html#order">去定制</a>
      <a class="btn ghost" href="dingzhi.html#pricing">看收费</a>
    </div>
  </section>
"""

# --- XHS page ---
xhs_body = ('  <div class="page-head"><h1>小红书作品</h1><p>杨树598 在小红书的 7 篇作品。点图放大，左右滑动切换；每篇封面有“订这篇同款”，点了直接带到定制页并勾好对应单品。</p></div>\n'
            + filter_block(xhs_series) + '\n' + xhs_panels + '\n')

# --- Video page ---
vid_body = ('  <div class="page-head"><h1>视频号作品</h1><p>杨树598 在视频号的图文，助理接手后发表的 __VIDEO_COUNT__ 篇全部在这里：__VIDEO_SHORTS__。点图放大，左右滑动切换；每篇封面有“订这篇同款”。</p></div>\n'
            + filter_block(vid_series) + '\n' + video_html + '\n')
vid_body = vid_body.replace('__VIDEO_COUNT__', str(_VIDEO_COUNT)).replace('__VIDEO_SHORTS__', _VIDEO_SHORTS)

# --- MP page: all 64 published articles (user choice 2026-10-28 15:27) ---
# Source: ~/workspace/website-optimize/mp-published-baseline-20261028.md (read-only check).
# Links fully resolved 2026-10-28 16:09 (61 unique links, no pending item);
# 2026-10-28 nightly check added 1 (2026-10-28 21:16, total 62).
# 2026-10-29 evening check added 2 (2026-10-29 12:12 + 00:21, total 64).
# Covers: one image per article taken from the article itself (og:image cover,
# extracted 2026-10-28 via mobile-UA fetch, see extract_mp_images.py and
# mp-image-map.json); gallery files are site-v2/images/mpXX-YY.jpg where XX
# is the manifest prefix (old articles keep mp01..mp61, new ones mp62+).
# Card ids (mp01 = newest card) are baseline positions, NOT file prefixes.
# Never invent a link or an image.
# Galleries (2026-10-28): every card also carries ALL images of its article
# (cover first, then body, in article order; QR/diversion cards excluded per
# user decision, see mp-gallery-plan.md). Manifest:
# ~/workspace/website-optimize/mp-gallery-final.json, files
# site-v2/images/mpXX-YY.jpg (YY = kept order, gapless). The assert below
# is intentional: a future article with no gallery files must FAIL the build
# loudly (run gallery extraction first) — never remove the assert to ship an
# imageless card, and never invent an image.
import html as _html
import json as _json
_mp_gal = _json.load(open(os.path.join(ROOT, 'mp-gallery-final.json'), encoding='utf-8'))
# Gallery keyed by article URL, NOT by baseline position: inserting a new
# article at the front shifts every position, so a positional key would
# mis-assign all old galleries. New articles get a fresh mp62+ file prefix
# and are appended to mp-gallery-final.json; old files are never renamed.
_mp_gal_by_url = {r['url']: r for r in _mp_gal}
_mp_gal_total = 0
_mp_cards = []
_seen_urls = set()
_mp_idx = 0
_mp_years = set()
_mp_lines = open(os.path.join(ROOT, 'mp-published-baseline-20261028.md'), encoding='utf-8').read()
for _line in _mp_lines.splitlines():
    _m = re.match(r'^\d+\.\s+(.+?)\s+—\s+(\d{4}-\d{2}-\d{2})(?:\s+\d{2}:\d{2})?\s+—\s+(https://\S+)\s*$', _line)
    if not _m:
        continue
    _mp_idx += 1
    _title, _date, _url = _m.group(1), _m.group(2), _m.group(3)
    _mp_years.add(_date[:4])
    _gal = _mp_gal_by_url.get(_url, {}).get('kept', [])
    assert _gal, 'missing MP gallery for article %02d (%s)' % (_mp_idx, _title)
    _gal_files = []
    for _k in _gal:
        _gf = 'images/%s' % _k['final_file']
        assert os.path.exists(os.path.join(OUT, _gf)), 'missing MP gallery file %s' % _gf
        _gal_files.append(_gf)
    _mp_gal_total += len(_gal_files)
    # Professional batch 2026-10-28: strip uses a small 240w thumb (file
    # -t.jpg, must exist), lightbox uses the 720w file, and landscape images
    # also carry a 1080w -l.jpg for wide desktop screens when present.
    # Alt is the article title + position (was empty before).
    _strip_parts = []
    for _pos, _f in enumerate(_gal_files, 1):
        _thumb = _f[:-4] + '-t.jpg'
        assert os.path.exists(os.path.join(OUT, _thumb)), 'missing MP thumb %s' % _thumb
        _large = _f[:-4] + '-l.jpg'
        _large_attr = ''
        if os.path.exists(os.path.join(OUT, _large)):
            _large_attr = ' data-full-l="%s"' % _large
        _strip_parts.append('<img class="ph mp-gal" src="%s" data-full="%s"%s data-group="mp%02d" alt="%s 第 %d 张" loading="lazy" decoding="async">'
                            % (_thumb, _f, _large_attr, _mp_idx, _html.escape(_title, quote=True), _pos))
    _strip = '<div class="mp-gallery">' + ''.join(_strip_parts) + '</div>'
    if _url in _seen_urls:
        _mp_cards.append('    <div class="mp-card" id="mp%02d" data-year="%s"><div class="mp-text"><h3>%s</h3><p>%s</p><p class="mp-note">阅读原文链接正在复核，复核后补上。</p></div>%s</div>'
                         % (_mp_idx, _date[:4], _html.escape(_title), _date, _strip))
    else:
        _seen_urls.add(_url)
        _mp_cards.append('    <div class="mp-card" id="mp%02d" data-year="%s"><div class="mp-text"><h3>%s</h3><p>%s</p><a href="%s" target="_blank" rel="noopener">阅读原文 →</a></div>%s</div>'
                         % (_mp_idx, _date[:4], _html.escape(_title), _date, _url, _strip))
assert len(_mp_cards) == 64, 'MP cards: %d, expected 64' % len(_mp_cards)
assert _mp_gal_total == 275, 'MP gallery images: %d, expected 275' % _mp_gal_total  # 285 minus 20 cover-crop duplicates removed 2026-10-28 (cover was a wide crop of the first body photo; gallery now starts with the full photo) + 4 new-article body photos 2026-10-28 (cover crop excluded likewise) + 6 new-article body photos 2026-10-29
mp_body = ('  <div class="page-head"><h1>公众号文章</h1><p>公众号「杨树598」已发表的 64 篇，按发表时间从新到旧排列，点开在公众号内阅读原文。'
           '正文不全文搬到站里。64 篇阅读原文链接已全部确认。点卡片里的图片，可以看本篇的全部图片，左右滑动只在本篇里切换。以后新发表的文章由每日核对自动追加到这里。</p></div>\n'
           '  <div class="mp-filter"><div class="filter-wrap"><div class="filter-group" role="group" aria-label="按年份筛选">\n'
           '      <span class="filter-label">年份</span>\n'
           '      <button type="button" class="chip active" data-year-filter="all">全部</button>\n'
           + ''.join('      <button type="button" class="chip" data-year-filter="%s">%s</button>\n' % (y, y) for y in sorted(_mp_years, reverse=True))
           + '    </div><div class="filter-group" role="group" aria-label="搜索">\n'
           '      <span class="filter-label">搜索</span>\n'
           '      <input type="search" class="search-input" id="mpSearch" placeholder="搜文章标题，如沙发、公园、书店" aria-label="搜索公众号文章" />\n'
           '    </div><p class="filter-count" id="mpCount"></p></div></div>\n'
           '  <div class="mp-list" id="mpList">\n' + '\n'.join(_mp_cards) + '\n  </div>\n')

# --- Dingzhi page ---
# SpaceX 式六项改进 2026-10-28 晚：定制流程步骤条置于页首（id=orderSteps，承接原 #pricing 的 150px 首屏留白，#pricing 回落到 .section 的 60px）。
_dingzhi_steps = """
  <section class="section" id="orderSteps">
    <p class="sec-kicker">How It Works</p>
    <h2 class="sec-title">定制流程 · 5 步</h2>
    <ol class="order-steps">
      <li><b>1 · 选单品</b><span>勾选想要的单品与数量</span></li>
      <li><b>2 · 填表单</b><span>联系方式与收货信息一次填好</span></li>
      <li><b>3 · 查邮件付款</b><span>提交后查收邮件、扫码付款</span></li>
      <li><b>4 · 加微信确认</b><span>备注订单参考号、发付款截图</span></li>
      <li><b>5 · 等待发货</b><span>10 天内发货，包装保密</span></li>
    </ol>
    <p class="order-perks">满 ¥58 包邮 · 满 ¥200 送牛奶 · 交期 10 天内 · 包装保密 · 不支持退换</p>
  </section>
"""
dingzhi_body = _dingzhi_steps + '\n\n' + pricing + '\n\n' + process + '\n\n' + order + '\n\n' + faq + '\n'

# Home latest block placeholders (defined before the MP loop) get real values now.
home_body = home_body.replace('__LATEST_MP_TITLE__', _html.escape(_latest_mp_title)).replace('__LATEST_MP_DATE__', _latest_mp_date)
home_body = home_body.replace('__LATEST_VIDEO_COVER__', _latest_v_cover).replace('__LATEST_VIDEO_ALT__', '视频号第 %s 篇 · %s' % (_latest_v_num, _latest_v_short)).replace('__LATEST_VIDEO_TITLE__', _latest_v_short).replace('__LATEST_VIDEO_NUM__', _latest_v_num).replace('__LATEST_VIDEO_DATE__', _latest_v['date']).replace('__VIDEO_COUNT__', str(_VIDEO_COUNT))

pages = {
    'index.html': page('杨树598 · 作品与定制', '杨树598 的作品与定制接单站：小红书、视频号、公众号三个平台，一个杨树。',
                       'https://wangxiaowu.cc/images/img01-l.jpg', home_body, canonical='https://wangxiaowu.cc/'),
    'xiaohongshu.html': page('小红书作品 · 杨树598', '杨树598 在小红书的 7 篇作品：穿搭公式与日常细节。',
                             'https://wangxiaowu.cc/images/img25-l.jpg', xhs_body, canonical='https://wangxiaowu.cc/xiaohongshu.html'),
    'shipinhao.html': page('视频号作品 · 杨树598', '杨树598 在视频号的图文：%s，助理接手后发表的 %d 篇。' % (_VIDEO_SHORTS, _VIDEO_COUNT),
                           'https://wangxiaowu.cc/images/%s-l.jpg' % _latest_v_cover, vid_body, canonical='https://wangxiaowu.cc/shipinhao.html'),
    'gongzhonghao.html': page('公众号文章 · 杨树598', '公众号「杨树598」的小短文，发表后由每日核对自动同步。',
                              'https://wangxiaowu.cc/images/img01-l.jpg', mp_body, canonical='https://wangxiaowu.cc/gongzhonghao.html'),
    'dingzhi.html': page('定制接单 · 杨树598', '杨树598 定制接单：收费标准、定制流程、定制表单与常见问题。',
                         'https://wangxiaowu.cc/images/img01-l.jpg', dingzhi_body,
                         extra_scripts='<script src="order.js?v=' + _order_v + '"></script>', canonical='https://wangxiaowu.cc/dingzhi.html'),
}

os.makedirs(OUT, exist_ok=True)
for name, content in pages.items():
    open(os.path.join(OUT, name), 'w', encoding='utf-8').write(content)
    print(name, len(content))
open(os.path.join(OUT, 'style.css'), 'w', encoding='utf-8').write(style_css)
open(os.path.join(OUT, 'site.js'), 'w', encoding='utf-8').write(site_js)
open(os.path.join(OUT, 'order.js'), 'w', encoding='utf-8').write(order_js)
# SEO files (professional batch 2026-10-28): sitemap + robots, rebuilt each run.
import datetime as _dt
_today = _dt.date.today().isoformat()
_sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + ''.join('  <url><loc>https://wangxiaowu.cc/%s</loc><lastmod>%s</lastmod></url>\n' % ('' if n == 'index.html' else n, _today)
                        for n in ['index.html', 'xiaohongshu.html', 'shipinhao.html', 'gongzhonghao.html', 'dingzhi.html'])
            + '</urlset>\n')
open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write(_sitemap)
open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8').write('User-agent: *\nAllow: /\nSitemap: https://wangxiaowu.cc/sitemap.xml\n')
print('style.css', len(style_css), 'site.js', len(site_js), 'order.js', len(order_js))
