(() => {
  const BASE = "https://www.tiktok.com";

  // Lấy chuỗi số dài nhất trong 1 string (thường là videoId 18-19 digits)
  const extractLongNumber = (s) => {
    const nums = (s || "").match(/\d{10,}/g); // >=10 để tránh dính index nhỏ
    if (!nums) return null;
    return nums.sort((a, b) => b.length - a.length)[0];
  };

  const getActivePlayer = () => {
    const players = [...document.querySelectorAll(".tiktok-web-player")];
    if (!players.length) return null;

    // 1) ưu tiên player có video đang phát
    for (const p of players) {
      const v = p.querySelector("video");
      if (v && !v.paused && !v.ended && v.currentTime > 0) return p;
    }

    // 2) fallback: player chiếm nhiều viewport nhất
    const vpH = window.innerHeight;
    const visibleRatio = (el) => {
      const r = el.getBoundingClientRect();
      const visible = Math.max(0, Math.min(r.bottom, vpH) - Math.max(r.top, 0));
      return visible / Math.max(1, r.height);
    };

    return players.sort((a, b) => visibleRatio(b) - visibleRatio(a))[0];
  };

  const findUsernameNear = (root) => {
    // tìm link profile dạng /@username gần card hiện tại
    let node = root;
    for (let i = 0; i < 12 && node; i++) {
      const links = [...(node.querySelectorAll?.('a[href^="/@"]') || [])];
      for (const a of links) {
        const href = a.getAttribute("href") || "";
        const m = href.match(/^\/@([^/?#]+)/);
        if (m?.[1]) return m[1];
      }
      node = node.parentElement;
    }
    return null;
  };

  const getNowWatchingUrl = () => {
    const player = getActivePlayer();
    if (!player) return null;

    const videoId = extractLongNumber(player.id); // KHÔNG phụ thuộc format xgwrapper
    if (!videoId) return null;

    const username = findUsernameNear(player);
    return username
      ? `${BASE}/@${username}/video/${videoId}`
      : `${BASE}/video/${videoId}`;
  };

  let last = null;
  const tick = () => {
    const url = getNowWatchingUrl();
    if (url && url !== last) {
      last = url;
      console.log("Now watching:", url);
    }
  };

  // start
  window.addEventListener("scroll", tick, { passive: true });
  const timer = setInterval(tick, 400);
  tick();

  // stop helper
  window.stopTikTokWatcher = () => {
    clearInterval(timer);
    window.removeEventListener("scroll", tick);
    console.log("Stopped.");
  };

  console.log("✅ Watching. Run `stopTikTokWatcher()` to stop.");
})();
