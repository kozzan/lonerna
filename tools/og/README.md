`card.html` is the source for `site/assets/og.png`. The numbers on it are typed
(poliser median 2025, 2026 tax), so re-render after the yearly update:

    google-chrome --headless=new --hide-scrollbars --allow-file-access-from-files \
      --window-size=1200,630 --virtual-time-budget=4000 \
      --screenshot=$PWD/site/assets/og.png "file://$PWD/tools/og/card.html"
