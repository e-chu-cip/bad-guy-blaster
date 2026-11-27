/* First-party requests only. No analytics beacon, cookies, IP storage, or tracking ID. */
(() => {
  let sequence = 0;
  const responses = new Map();
  window.gameScores = {
    request(path, serialized) {
      const id = ++sequence;
      const options = {method: serialized ? "POST" : "GET", cache: "no-store",
        signal: AbortSignal.timeout(10000), credentials: "same-origin"};
      if (serialized) {
        options.headers = {"Content-Type": "application/json"};
        options.body = serialized;
      }
      fetch(`/api/${path}`, options).then(async response => {
        const data = await response.json();
        responses.set(id, JSON.stringify({ok: response.ok, status: response.status, data}));
      }).catch(() => responses.set(id, JSON.stringify({ok: false, status: 0,
        data: {error: "Connection unavailable. Retrying while the game is open."}})));
      return id;
    },
    poll(id) {
      const value = responses.get(id) || "";
      if (value) responses.delete(id);
      return value;
    }
  };
})();
