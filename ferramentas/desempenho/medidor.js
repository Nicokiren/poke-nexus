// Medidor de quadros e de resposta da página (ferramentas/desempenho/medir.py).
// Roda num MUNDO ISOLADO criado pelo DevTools (Page.createIsolatedWorld): enxerga o DOM, mas não as
// variáveis do jogo, e o jogo não enxerga ele. Só LÊ: guarda o tempo entre quadros
// (requestAnimationFrame), o atraso entre uma tecla F24 (mandada pela ferramenta, nenhuma página usa
// essa tecla) e o próximo quadro, a duração dos eventos (Event Timing) e os quadros longos. Some quando
// a página recarrega ou fecha; não fica em nada que é entregue ao usuário.
(() => {
  if (globalThis.__pnMed) return "ja";
  const m = globalThis.__pnMed = { raf: [], ent: [], et: [], loaf: [], pend: [], ultimo: 0, rec: 0 };
  const quadro = (t) => {
    if (document.visibilityState === "visible") {
      if (m.ultimo) m.raf.push(+(t - m.ultimo).toFixed(2));
      m.ultimo = t;
      if (m.pend.length) {
        for (const ts of m.pend) m.ent.push(+(t - ts).toFixed(2));
        m.pend = [];
      }
    } else {
      m.ultimo = 0;
    }
    requestAnimationFrame(quadro);
  };
  requestAnimationFrame(quadro);
  document.addEventListener("visibilitychange", () => { m.ultimo = 0; m.pend = []; });
  addEventListener("keydown", (e) => {
    if (e.key === "F24" && document.visibilityState === "visible") { m.pend.push(e.timeStamp); m.rec++; }
  }, true);
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) if (e.name === "keydown") m.et.push(e.duration); })
      .observe({ type: "event", durationThreshold: 16 });
  } catch (_) {}
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) m.loaf.push(+e.duration.toFixed(1)); })
      .observe({ type: "long-animation-frame" });
  } catch (_) {
    try {
      new PerformanceObserver((l) => { for (const e of l.getEntries()) m.loaf.push(+e.duration.toFixed(1)); })
        .observe({ type: "longtask" });
    } catch (__) {}
  }
  return "ok";
})()
