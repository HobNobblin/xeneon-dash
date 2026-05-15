// Widget SDK — include this in any widget's index.html
window.xeneon = (() => {
  const handlers = {};

  const api = {
    config: {},
    location: {},

    on(event, callback) {
      (handlers[event] ??= []).push(callback);
      return api;
    },

    _emit(event, data) {
      (handlers[event] ?? []).forEach(cb => {
        try { cb(data); } catch (e) { console.error(`xeneon handler error [${event}]:`, e); }
      });
    },
  };

  window.addEventListener("message", ({ data }) => {
    if (!data?.type) return;
    if (data.type === "init") {
      api.config   = data.config   ?? {};
      api.location = data.location ?? {};
      api._emit("ready", api.config);
    } else if (data.type === "tick") {
      api._emit("tick", data.metrics);
    }
  });

  return api;
})();
