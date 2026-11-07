/* Site-wide: theme toggle + consent. Both are deliberately tiny and
   dependency-free; nothing here should ever block a game from starting. */

(function () {
  'use strict';

  // ---- theme -------------------------------------------------------------
  var root = document.documentElement;
  var toggle = document.getElementById('theme-toggle');

  function currentTheme() {
    if (root.dataset.theme) return root.dataset.theme;
    return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function paintToggle() {
    if (toggle) toggle.textContent = currentTheme() === 'dark' ? '☀' : '☾';
  }
  paintToggle();

  if (toggle) {
    toggle.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (e) {}
      paintToggle();
    });
  }

  // ---- ads ---------------------------------------------------------------
  // AdSense needs exactly one push per <ins>. Pushing twice for the same
  // element is a policy violation, so mounted slots are marked.
  // AdSense throws "No slot size for availableWidth=0" if the slot is hidden
  // when pushed -- which is every responsive-hidden ad and everything inside a
  // collapsed result panel. Wait until the element actually has width.
  var pending = [];
  window.mountAd = function (el) {
    if (!el || el.dataset.adsbygoogleStatus || el.dataset.mounted) return;
    if (!el.getBoundingClientRect().width) {
      if (pending.indexOf(el) < 0) pending.push(el);
      return;
    }
    el.dataset.mounted = '1';
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) {}
  };
  function sweep() {
    for (var i = pending.length - 1; i >= 0; i--) {
      var el = pending[i];
      if (el.getBoundingClientRect().width) { pending.splice(i, 1); window.mountAd(el); }
    }
  }
  Array.prototype.forEach.call(
    document.querySelectorAll('ins.adsbygoogle'), window.mountAd);
  // Slots appear when a result panel opens or the viewport crosses a breakpoint.
  window.addEventListener('resize', sweep);
  if (window.MutationObserver) {
    new MutationObserver(sweep).observe(document.body, {
      attributes: true, subtree: true, attributeFilter: ['hidden', 'style', 'class']
    });
  }

  // ---- consent -----------------------------------------------------------
  // Google's certified CMP (Funding Choices) owns the consent dialog and the
  // Consent Mode updates. We only set the denied-by-default signals in <head>
  // before it loads. Do NOT add a second banner or write our own consent
  // value -- that would grant consent the CMP never actually collected.
  //
  // The footer link re-opens Google's dialog, and stays hidden unless the CMP
  // actually loaded (it only serves EEA/UK/CH, and ad blockers eat it).
  // Google's CMP exposes the reopen dialog through googlefc, but only once it
  // has actually collected a decision. Calling showRevocationMessage() while
  // the status is UNKNOWN silently does nothing, so the link is revealed only
  // when there is a real choice to change -- otherwise it is a dead control.
  var reopen = document.getElementById('cmp-reopen');
  if (reopen) {
    reopen.addEventListener('click', function () {
      if (!window.googlefc) return;
      googlefc.callbackQueue = googlefc.callbackQueue || [];
      googlefc.callbackQueue.push({
        CONSENT_DATA_READY: function () { googlefc.showRevocationMessage(); }
      });
    });

    var tries = 0;
    var poll = setInterval(function () {
      var fc = window.googlefc;
      if (fc && typeof fc.getConsentStatus === 'function' && fc.ConsentStatusEnum) {
        var st = fc.getConsentStatus();
        var E = fc.ConsentStatusEnum;
        // UNKNOWN = never asked (nothing to revoke).
        // CONSENT_NOT_REQUIRED = outside the EEA, no dialog exists.
        if (st !== E.UNKNOWN && st !== E.CONSENT_NOT_REQUIRED) {
          reopen.hidden = false;
          clearInterval(poll);
          return;
        }
      }
      // Consent can be collected after load, so keep looking for a while.
      if (++tries > 40) clearInterval(poll);
    }, 500);
  }
})();

