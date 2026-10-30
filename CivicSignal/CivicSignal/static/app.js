document.addEventListener("DOMContentLoaded", () => {
  const mapEl = document.getElementById("report-map");
  if (!mapEl || typeof L === "undefined") return;
  let reports = [];
  try { reports = JSON.parse(mapEl.dataset.reports || "[]"); } catch (e) {}
  const map = L.map("report-map").setView([12.9716, 77.5946], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  const bounds = [];
  reports.forEach(r => {
    const marker = L.marker([r.latitude, r.longitude]).addTo(map);
    marker.bindPopup(`<b>${escapeHtml(r.title)}</b><br>${escapeHtml(r.category)} · ${escapeHtml(r.priority)}<br>${escapeHtml(r.status)}<br>${escapeHtml(r.location)}`);
    bounds.push([r.latitude, r.longitude]);
  });
  if (bounds.length) map.fitBounds(bounds, {padding: [25, 25], maxZoom: 14});
});
function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
