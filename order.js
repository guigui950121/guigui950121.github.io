(function(){
/* ---------- order form ---------- */
var SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbyeYeJLDi_GgVa3z3f8f63Q82Al1h-6NEbshppt_gan7IbrxhR4crPHzwjHDlxw_MO6/exec';

  var ITEMS = [
    { name: "原味棉袜", price: 48 },
    { name: "原味丝袜", price: 58 },
    { name: "原味内裤", price: 68 },
    { name: "原味老北京布鞋", price: 88 },
    { name: "原味正装衬衫", price: 188.88 },
    { name: "原味正装西裤", price: 188.88 },
    { name: "原味正装皮鞋", price: 588.88 },
    { name: "牛奶", price: 199.99 }
  ];
  var SHIP_FREE_AT = 58;
  var SHIP_FEE = 18;
  var GIFT_AT = 200;
  function fmt(n){ return "¥" + n.toFixed(2); }
  var pickList = document.getElementById("pickList");
  var totalVal = document.getElementById("totalVal");
  var shipHint = document.getElementById("shipHint");

  ITEMS.forEach(function(item, i){
    var row = document.createElement("div");
    row.className = "pick-row";

    var cb = document.createElement("input");
    cb.type = "checkbox";
    cb.id = "pick-" + i;
    cb.setAttribute("aria-label", item.name);

    var name = document.createElement("label");
    name.className = "pick-name";
    name.htmlFor = "pick-" + i;
    name.textContent = item.name;

    var price = document.createElement("span");
    price.className = "pick-price";
    price.textContent = fmt(item.price);

    var qtyWrap = document.createElement("span");
    qtyWrap.className = "pick-qty";
    var qtyLabel = document.createElement("span");
    qtyLabel.textContent = "数量";
    var minusBtn = document.createElement("button");
    minusBtn.type = "button";
    minusBtn.className = "qty-btn";
    minusBtn.textContent = "−";
    minusBtn.disabled = true;
    minusBtn.setAttribute("aria-label", item.name + " 减少数量");
    var qty = document.createElement("input");
    qty.type = "number"; qty.min = "1"; qty.step = "1"; qty.value = "1";
    qty.disabled = true;
    qty.setAttribute("aria-label", item.name + " 数量");
    var plusBtn = document.createElement("button");
    plusBtn.type = "button";
    plusBtn.className = "qty-btn";
    plusBtn.textContent = "+";
    plusBtn.disabled = true;
    plusBtn.setAttribute("aria-label", item.name + " 增加数量");
    qtyWrap.appendChild(qtyLabel);
    qtyWrap.appendChild(minusBtn);
    qtyWrap.appendChild(qty);
    qtyWrap.appendChild(plusBtn);

    row.appendChild(cb); row.appendChild(name); row.appendChild(price); row.appendChild(qtyWrap);
    pickList.appendChild(row);

    item._cb = cb; item._qty = qty; item._minus = minusBtn; item._plus = plusBtn;
    function setQtyEnabled(){
      var on = cb.checked;
      qty.disabled = !on;
      minusBtn.disabled = !on;
      plusBtn.disabled = !on;
    }
    function getQty(){
      var q = parseInt(qty.value, 10);
      if (isNaN(q) || q < 1) q = 1;
      return q;
    }
    cb.addEventListener("change", function(){
      setQtyEnabled();
      if (cb.checked && (!qty.value || parseInt(qty.value, 10) < 1)) qty.value = "1";
      calc();
    });
    minusBtn.addEventListener("click", function(){
      var q = getQty();
      if (q > 1) { qty.value = String(q - 1); calc(); }
    });
    plusBtn.addEventListener("click", function(){
      var q = getQty();
      qty.value = String(q + 1);
      calc();
    });
    qty.addEventListener("input", calc);
    qty.addEventListener("change", function(){
      if (qty.value === "" || parseInt(qty.value, 10) < 1) qty.value = "1";
      calc();
    });
  });

  function calc(){
    var goodsTotal = 0;
    ITEMS.forEach(function(item){
      if (item._cb.checked) {
        var q = parseInt(item._qty.value, 10);
        if (isNaN(q) || q < 1) q = 0;
        goodsTotal += item.price * q;
      }
    });
    var shipFee = (goodsTotal > 0 && goodsTotal < SHIP_FREE_AT) ? SHIP_FEE : 0;
    var total = goodsTotal + shipFee;
    totalVal.textContent = fmt(total);
    if (shipHint) {
      if (goodsTotal === 0) {
        shipHint.innerHTML = "满 <strong>¥58 包邮</strong>，不满 ¥58 自动加运费 <strong>¥18</strong>；满 <strong>¥200 送牛奶</strong>，付款后联系微信确认赠品。";
        shipHint.classList.remove("is-free");
      } else if (goodsTotal >= GIFT_AT) {
        shipHint.innerHTML = "<strong>已包邮，并已满 ¥200</strong>：可获赠牛奶一份，付款后联系微信确认赠品。";
        shipHint.classList.add("is-free");
      } else if (goodsTotal >= SHIP_FREE_AT) {
        var toGift = GIFT_AT - goodsTotal;
        shipHint.innerHTML = "<strong>已满 ¥58 包邮</strong>，已免运费。再选 <strong>" + fmt(toGift) + "</strong> 满 ¥200 还可获赠牛奶。";
        shipHint.classList.add("is-free");
      } else {
        var remain = SHIP_FREE_AT - goodsTotal;
        shipHint.innerHTML = "未满 ¥58，已自动加上运费 <strong>¥18</strong>（商品 " + fmt(goodsTotal) + " ＋ 运费 ¥18.00 ＝ " + fmt(total) + "）。再选 <strong>" + fmt(remain) + "</strong> 即可包邮。";
        shipHint.classList.remove("is-free");
      }
    }
  }
  calc();

  var form = document.getElementById("orderForm");
  var err = document.getElementById("formErr");
  var orderSeq = 0;
  var lastOrderText = "";
  var lastMailText = "";
  document.getElementById("copyOrderBtn").addEventListener("click", function(){
    copyText(lastOrderText, document.getElementById("copyTip"), "订单信息已复制");
  });
  document.getElementById("copyMailBtn").addEventListener("click", function(){
    copyText(lastMailText, document.getElementById("copyMailTip"), "自动回复邮件已复制");
  });
  form.addEventListener("submit", function(e){
    e.preventDefault();
    var anyChecked = ITEMS.some(function(item){ return item._cb.checked; });
    var contact = document.getElementById("contact").value.trim();
    var email = document.getElementById("email").value.trim();
    var repeatRefEl = document.getElementById("repeatRef");
    var repeatRef = repeatRefEl ? repeatRefEl.value.trim() : "";
    var recipient = document.getElementById("recipient").value.trim();
    var phone = document.getElementById("phone").value.trim();
    var address = document.getElementById("address").value.trim();
    var note = document.getElementById("note").value.trim();
    if (!anyChecked) {
      err.textContent = "请至少勾选一件单品。";
      err.classList.add("show");
      return;
    }
    if (!contact) {
      err.textContent = "请填写联系方式。";
      err.classList.add("show");
      return;
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      err.textContent = "请填写有效邮箱，订单自动回复会发到这个邮箱。";
      err.classList.add("show");
      return;
    }
    if (!recipient) {
      err.textContent = "请填写收货人姓名。";
      err.classList.add("show");
      return;
    }
    if (!phone) {
      err.textContent = "请填写手机号。";
      err.classList.add("show");
      return;
    }
    if (!/^\d{11}$/.test(phone)) {
      err.textContent = "手机号格式不对，请填写11位数字手机号。";
      err.classList.add("show");
      return;
    }
    if (!address) {
      err.textContent = "请填写收货地址。";
      err.classList.add("show");
      return;
    }
    err.classList.remove("show");

    /* order reference number: date + sequence, generated on this page */
    orderSeq += 1;
    var now = new Date();
    function pad(n, w){ var t = String(n); while (t.length < w) t = "0" + t; return t; }
    var ref = String(now.getFullYear()) + pad(now.getMonth() + 1, 2) + pad(now.getDate(), 2) + "-" + pad(orderSeq, 3);

    var lines = [], goodsTotal = 0;
    ITEMS.forEach(function(item){
      if (item._cb.checked) {
        var q = parseInt(item._qty.value, 10);
        if (isNaN(q) || q < 1) q = 1;
        goodsTotal += item.price * q;
        lines.push(item.name + " ×" + q + " " + fmt(item.price * q));
      }
    });
    var shipFee2 = (goodsTotal > 0 && goodsTotal < SHIP_FREE_AT) ? SHIP_FEE : 0;
    if (shipFee2 > 0) lines.push("运费（不满¥58自动加） ×1 " + fmt(shipFee2));
    else if (goodsTotal > 0) lines.push("运费：包邮 ¥0.00");
    var hasGift = goodsTotal >= GIFT_AT;
    if (hasGift) lines.push("赠品：满¥200送牛奶 ×1 免费（付款后联系微信确认）");
    var total = goodsTotal + shipFee2;

    lastOrderText =
      "订单参考号：" + ref + "\n" +
      "所选单品：\n" + lines.map(function(l){ return "- " + l; }).join("\n") + "\n" +
      "预估合计：" + fmt(total) + "（具体金额以确认为准）\n" +
      "联系方式：" + contact + "\n" +
      "邮箱：" + email + "\n" +
      (repeatRef ? "老客户／上次订单参考号：" + repeatRef + "\n" : "") +
      "收货人姓名：" + recipient + "\n" +
      "手机号：" + phone + "\n" +
      "收货地址：" + address +
      (note ? "\n备注：" + note : "");

    lastMailText =
      "邮件主题：你的定制意向已收到（订单参考号：" + ref + "）\n\n" +
      "你好，你的定制意向已收到。\n\n" +
      "订单参考号：" + ref + "\n" +
      (repeatRef ? "老客户／上次订单参考号：" + repeatRef + "\n" : "") +
      "所选单品：\n" + lines.map(function(l){ return "- " + l; }).join("\n") + "\n" +
      "预估合计：" + fmt(total) + "（具体金额和交期在微信上确认）\n" +
      "收货人姓名：" + recipient + "\n" +
      "手机号：" + phone + "\n" +
      "收货地址：" + address + "\n\n" +
      "接下来：\n" +
      "1. 请按附件里的收款码扫码付款；\n" +
      "2. 付款后按附件里的加微信二维码加微信，备注订单参考号，并发付款截图；\n" +
      "3. 我们确认收款后，会在微信上和你确认细节和交期；\n" +
      "4. 确认后安排发货。\n\n" +
      "谢谢。";

    var payloadItems = [];
    ITEMS.forEach(function(item){
      if (item._cb.checked) {
        var q = parseInt(item._qty.value, 10);
        if (isNaN(q) || q < 1) q = 1;
        payloadItems.push({ name: item.name, price: item.price, qty: q });
      }
    });
    var submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;
    fetch(SCRIPT_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, mode: 'no-cors', body: JSON.stringify({ ref: ref, contact: contact, email: email, repeatRef: repeatRef, recipient: recipient, phone: phone, address: address, note: note, items: payloadItems }) }).then(function(){
      document.getElementById("successBox").querySelector("p").textContent = "提交成功";
      document.getElementById("refNo").textContent = ref;
      document.getElementById("mailBody").textContent = lastMailText;
      form.style.display = "none";
      document.getElementById("successBox").classList.add("show");
      document.getElementById("successBox").scrollIntoView({ behavior: "smooth", block: "center" });
    }).catch(function(){
      document.getElementById("successBox").querySelector("p").textContent = "提交未成功，订单信息已生成，请先复制保存，再点再次提交重试";
      document.getElementById("refNo").textContent = ref;
      document.getElementById("mailBody").textContent = lastMailText;
      document.getElementById("successBox").classList.add("show");
      err.textContent = "提交失败，网络未连通，请点再次提交重试；也可以先复制订单信息保存。";
      err.classList.add("show");
      if (submitBtn) submitBtn.disabled = false;
    });
  });
  /* ---------- multi-page v2: order-items from a work page ---------- */
  (function(){
    var m = (location.hash || '').match(/^#order-items=([a-z,]+)$/);
    if (!m) return;
    var CAT2IDX = { socks: 0, underwear: 2, cloth: 3, shirt: 4, trousers: 5, leather: 6 };
    m[1].split(',').forEach(function(cat){
      var i = CAT2IDX[cat];
      if (i === undefined) return;
      var cb = document.getElementById('pick-' + i);
      if (cb && !cb.checked) { cb.checked = true; cb.dispatchEvent(new Event('change')); }
    });
    var ord = document.getElementById('order');
    if (ord) ord.scrollIntoView();
  })();

})();
