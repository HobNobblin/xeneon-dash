async function init() {
  const config = await fetch("/api/config").then(r => r.json());
  const { columns, rows } = config.display;

  const grid = document.getElementById("grid");
  grid.style.gridTemplateColumns = `repeat(${columns}, 1fr)`;
  grid.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

  const iframes = [];

  for (const widget of config.widgets ?? []) {
    const { id, position: p, config: widgetConfig = {} } = widget;

    const iframe = document.createElement("iframe");
    iframe.src = `/widgets/${id}/index.html`;
    iframe.style.gridColumn = `${p.x + 1} / span ${p.w}`;
    iframe.style.gridRow = `${p.y + 1} / span ${p.h}`;

    iframe.addEventListener("load", () => {
      iframe.contentWindow?.postMessage({ type: "init", config: widgetConfig }, "*");
    });

    grid.appendChild(iframe);
    iframes.push(iframe);
  }

  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.type === "reload") { init(); return; }
    for (const iframe of iframes) {
      iframe.contentWindow?.postMessage(msg, "*");
    }
  };

  ws.onclose = () => setTimeout(init, 2000); // reconnect on server restart
}

init();
