document.addEventListener("DOMContentLoaded", () => {
  if (!window.mermaid) {
    return;
  }

  window.mermaid.initialize({
    startOnLoad: false,
    securityLevel: "loose",
    theme: "default",
  });

  window.mermaid.run({
    querySelector: ".mermaid",
  });
});
