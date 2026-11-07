/* Line-for-line port of tools/tax.py (SKV 433, inkomstår 2026, column 1).
   Change both or neither; tools/test.py runs this file against Skatteverket's tables. */
(function (root) {
  'use strict';
  var PBB = 59200, IBB = 83400, SKIKT = 643000, PS_MAX = Math.floor(IBB * 1.42 * 0.01);
  var E = 1e-9;
  function ceil100(x) { return Math.ceil(x / 100 - E) * 100; }
  function floor100(x) { return Math.floor(x / 100 + E) * 100; }

  function grundavdrag(ffi) {
    var ga;
    if (ffi <= 0.99 * PBB) ga = 0.423 * PBB;
    else if (ffi <= 2.72 * PBB) ga = 0.423 * PBB + 0.20 * (ffi - 0.99 * PBB);
    else if (ffi <= 3.11 * PBB) ga = 0.77 * PBB;
    else if (ffi <= 7.88 * PBB) ga = 0.77 * PBB - 0.10 * (ffi - 3.11 * PBB);
    else ga = 0.293 * PBB;
    return Math.min(ceil100(ga), ffi);
  }

  function jobbskatteavdrag(ai, ga, ki) {
    ai = floor100(ai);
    var base;
    if (ai <= 0.91 * PBB) base = ai;
    else if (ai <= 3.24 * PBB) base = 0.91 * PBB + 0.3874 * (ai - 0.91 * PBB);
    else if (ai <= 8.08 * PBB) base = 1.813 * PBB + 0.251 * (ai - 3.24 * PBB);
    else base = 3.027 * PBB;
    return Math.max(0, Math.floor((base - ga) * ki + E));
  }

  function pensionsavgift(ffi) {
    if (ffi < 0.423 * PBB) return 0;
    var fee = 0.07 * Math.min(ffi, 8.07 * IBB);
    return fee % 100 === 50 ? fee - 50 : Math.floor(fee / 100 + 0.5 - E) * 100;
  }

  function annual(ffi, ki, fees) {
    ffi = floor100(ffi);
    var ga = grundavdrag(ffi);
    var bfi = Math.max(0, ffi - ga);
    var statlig = bfi - SKIKT >= 200 ? Math.floor(0.20 * (bfi - SKIKT)) : 0;
    var kommunal = Math.floor(bfi * ki + E);
    var avgifter = Math.floor(bfi * fees + E);
    var pension = pensionsavgift(ffi);
    var redPension = Math.min(pension, statlig + kommunal);
    var komLeft = Math.max(0, kommunal - redPension);
    var jsa = Math.min(jobbskatteavdrag(ffi, ga, ki), komLeft); komLeft -= jsa;
    var redFfi = Math.min(bfi > 240000 ? 1500 : Math.max(0, Math.floor((bfi - 40000) * 0.0075)), komLeft);
    var ps = Math.min(Math.floor(bfi * 0.01), PS_MAX);
    return {
      brutto: ffi, grundavdrag: ga, beskattningsbar: bfi, statlig: statlig, kommunal: kommunal,
      avgifter: avgifter, pensionsavgift: pension, red_pension: redPension, jobbskatteavdrag: jsa,
      red_forvarvsinkomst: redFfi, public_service: ps,
      skatt: statlig + kommunal - redPension - jsa - redFfi + avgifter + pension + ps
    };
  }

  function monthlyNet(salary, kommunRate, burial, church) {
    var a = annual(salary * 12, kommunRate / 100, ((burial || 0) + (church || 0)) / 100);
    var tax = Math.floor(a.skatt / 12);
    return { net: salary - tax, tax: tax, annual: a };
  }

  function tableWithholding(top, table) {
    return Math.floor(annual(top * 12, (table - 1.16) / 100, 0.0116).skatt / 12);
  }

  var api = { annual: annual, monthlyNet: monthlyNet, tableWithholding: tableWithholding };
  if (typeof module === 'object' && module.exports) module.exports = api; else root.Tax = api;
})(this);
