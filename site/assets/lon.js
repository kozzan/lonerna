/* Payslip recalculation, "where do you land" marker, table filter, search redirect.
   Pages render fully without this; it only personalises. */
(function () {
  'use strict';
  var BP = window.BASE_PATH || '';
  var fmt = function (n) { return Math.round(n).toLocaleString('sv-SE').replace(/\s/g, ' ') + ' kr'; };
  var data = null;
  function load(cb) {
    if (data) return cb(data);
    fetch(BP + '/assets/data.json').then(function (r) { return r.json(); }).then(function (d) { data = d; cb(d); }).catch(function () {});
  }
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  // ---- payslip ----
  Array.prototype.forEach.call(document.querySelectorAll('[data-slip]'), function (slip) {
    var gross = slip.querySelector('[data-gross]'), sel = slip.querySelector('[data-kommun]'), church = slip.querySelector('[data-church]');
    var out = function (k) { return slip.querySelector('[data-k="' + k + '"]'); };
    var D = slip.dataset, rate = +D.rate, burial = +D.burial, churchFee = +D.church;

    function render() {
      var g = parseInt(String(gross.value).replace(/\D/g, ''), 10) || 0;
      if (!window.Tax) return;
      var r = Tax.monthlyNet(g, rate, burial, church.checked ? churchFee : 0), a = r.annual;
      var m = function (x) { return fmt(x / 12); };
      out('brutto').textContent = fmt(g);
      out('kommunal').textContent = '−' + m(a.kommunal);
      out('statlig').textContent = '−' + m(a.statlig);
      slip.querySelector('[data-row="statlig"]').hidden = !a.statlig;
      out('pensionsavgift').textContent = '−' + m(a.pensionsavgift);
      out('red').textContent = '+' + m(a.red_pension + a.jobbskatteavdrag + a.red_forvarvsinkomst);
      out('avg').textContent = '−' + m(a.avgifter + a.public_service);
      out('skatt').textContent = '−' + fmt(r.tax);
      out('net').textContent = fmt(r.net);
      out('eff').textContent = g ? (r.tax / g * 100).toFixed(1).replace('.', ',') + ' %' : '–';
    }

    load(function (d) {
      d.k.forEach(function (k, i) {
        var o = document.createElement('option'); o.value = i; o.textContent = k[0] + ', ' + k[1].toFixed(2).replace('.', ',') + ' %';
        sel.appendChild(o);
      });
      var saved = store.get('kommun');
      if (saved !== null && d.k[saved]) { sel.value = saved; pick(); }
    });
    function pick() {
      var k = data && data.k[sel.value];
      if (k) { rate = k[1]; burial = k[2]; churchFee = k[3]; } else { rate = +D.rate; burial = +D.burial; churchFee = +D.church; }
      store.set('kommun', sel.value); render();
    }
    sel.addEventListener('change', pick);
    church.addEventListener('change', render);
    gross.addEventListener('input', render);
  });

  // ---- "Är din lön rimlig?": band marker + verdict, synced both ways with the payslip ----
  Array.prototype.forEach.call(document.querySelectorAll('[data-band]'), function (band) {
    var p = JSON.parse(band.dataset.band), lo = +band.dataset.lo, hi = +band.dataset.hi, name = band.dataset.name;
    var you = band.querySelector('.you'), cap = band.querySelector('[data-you-text]'), original = cap.textContent;
    var input = document.querySelector('[data-you]'), gross = document.querySelector('[data-gross]');
    var pts = [[p.p10, 10], [p.p25, 25], [p.p50, 50], [p.p75, 75], [p.p90, 90]];
    var parse = function (v) { return parseInt(String(v).replace(/\D/g, ''), 10) || 0; };

    function show(g) {
      if (!g) { you.hidden = true; cap.textContent = original; return; }
      you.hidden = false;
      you.style.left = Math.max(0, Math.min(100, (g - lo) / (hi - lo) * 100)) + '%';
      var share, diff = g - p.p50;
      if (g < p.p10) share = 'Du tjänar mindre än 9 av 10 ' + name + '.';
      else if (g > p.p90) share = 'Du tjänar mer än 9 av 10 ' + name + '.';
      else {
        for (var i = 1; i < pts.length; i++) if (g <= pts[i][0]) break;
        var a = pts[i - 1], b = pts[i], q = a[1] + (g - a[0]) / Math.max(1, b[0] - a[0]) * (b[1] - a[1]);
        share = 'Du tjänar mer än ungefär ' + Math.round(q) + ' % av alla ' + name + '.';
      }
      share += Math.abs(diff) < 100 ? ' Det är precis medianlönen.'
        : ' Det är ' + fmt(Math.abs(diff)) + (diff < 0 ? ' under' : ' över') + ' medianlönen på ' + fmt(p.p50) + '.';
      cap.textContent = share;
    }
    if (input) input.addEventListener('input', function () {
      var g = parse(input.value); show(g);
      if (gross && g) { gross.value = g; gross.dispatchEvent(new Event('input')); }
    });
    if (gross) gross.addEventListener('input', function (e) {
      if (!e.isTrusted) return;                      // our own sync above
      var g = parse(gross.value); if (input) input.value = g || ''; show(g);
    });
  });

  // ---- table filter (/yrken/, /kommunalskatt/) ----
  var filter = document.querySelector('[data-filter]');
  if (filter) {
    var rows = document.querySelectorAll('main tbody tr');
    var q0 = new URLSearchParams(location.search).get('q');
    var run = function () {
      var q = filter.value.trim().toLowerCase();
      Array.prototype.forEach.call(rows, function (r) { r.hidden = q && r.textContent.toLowerCase().indexOf(q) < 0; });
    };
    filter.addEventListener('input', run);
    if (q0) { filter.value = q0; run(); }
  }

  // ---- search: exact occupation name -> straight to its page ----
  var search = document.querySelector('form.search');
  if (search) {
    load(function () {});   // warm the list so submit can decide synchronously
    search.addEventListener('submit', function (e) {
      var q = search.querySelector('input').value.trim().toLowerCase();
      var hit = data && data.o.filter(function (o) { return o[0].toLowerCase() === q; })[0];
      if (hit) { e.preventDefault(); location.href = BP + '/yrke/' + hit[1] + '/'; }
      // otherwise the form goes to /yrken/?q=... and the filter picks it up
    });
  }
})();
