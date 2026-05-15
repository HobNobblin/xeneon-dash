let iframes = [];

async function buildLayout() {
  const config = await fetch("/api/config").then(r => r.json());
  const { columns, rows } = config.display;
  const siteLocation = config.location ?? {};

  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  grid.style.gridTemplateColumns = `repeat(${columns}, minmax(0, 1fr))`;
  grid.style.gridTemplateRows    = `repeat(${rows}, minmax(0, 1fr))`;

  iframes = [];

  for (const widget of config.widgets ?? []) {
    const { id, position: p, config: widgetConfig = {} } = widget;

    const iframe = document.createElement("iframe");
    iframe.src = `/widgets/${id}/index.html`;
    iframe.style.gridColumn = `${p.x + 1} / span ${p.w}`;
    iframe.style.gridRow = `${p.y + 1} / span ${p.h}`;

    iframe.addEventListener("load", () => {
      iframe.contentWindow?.postMessage({ type: "init", config: widgetConfig, location: siteLocation, units: config.display?.units ?? "metric" }, "*");
    });

    grid.appendChild(iframe);
    iframes.push(iframe);
  }
}

function connectWS() {
  const ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    if (msg.type === "reload") { buildLayout(); return; }
    for (const iframe of iframes) {
      iframe.contentWindow?.postMessage(msg, "*");
    }
  };

  ws.onclose = () => setTimeout(connectWS, 2000);
}

buildLayout();
connectWS();
