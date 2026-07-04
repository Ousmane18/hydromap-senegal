/**
 * utils/api.js
 * Toutes les fonctions d'appel à l'API FastAPI HydroMap.
 * Proxy Vite : /api/* → http://localhost:8000
 */

const BASE = import.meta.env.VITE_API_URL || ""

/* ─── Helper central ─────────────────────────── */
async function req(url, opts = {}) {
  const res = await fetch(BASE + url, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  })
  if (!res.ok) {
    let msg = `Erreur ${res.status}`
    try { msg = (await res.json()).detail || msg } catch (_) {}
    throw new Error(msg)
  }
  return res
}

/* ─── Endpoints ─────────────────────────────── */
export const lancerDetection   = (p) => req("/api/detection", { method:"POST", body:JSON.stringify(p) }).then(r=>r.json())
export const getZones          = ()  => req("/api/zones").then(r=>r.json())
export const getSante          = ()  => req("/api/health").then(r=>r.json())
export const getAnalyseTemp    = (zone, annees, methode="random_forest") =>
  req("/api/temporel", { method:"POST", body:JSON.stringify({zone,annees,methode}) }).then(r=>r.json())

/* ─── Téléchargement client ─────────────────── */
export function dlGeoJSON(geojson, nom) {
  _dl(new Blob([JSON.stringify(geojson,null,2)], {type:"application/geo+json"}), nom)
}
export function dlCSV(features, nom) {
  const head  = "id,lat,lon,superficie_m2,superficie_ha,type,zone,date"
  const rows  = features.map((f,i)=>{
    const p   = f.properties||{}
    return [i+1,(+p.latitude||0).toFixed(6),(+p.longitude||0).toFixed(6),
            (+p.superficie_m2||0).toFixed(1),(+p.superficie_ha||0).toFixed(4),
            p.type_permanence||"",p.zone||"",p.date_detection||""].join(",")
  })
  _dl(new Blob([[head,...rows].join("\n")],{type:"text/csv"}), nom)
}
function _dl(blob, nom) {
  const a = Object.assign(document.createElement("a"),
    { href: URL.createObjectURL(blob), download: nom })
  document.body.appendChild(a); a.click()
  document.body.removeChild(a); URL.revokeObjectURL(a.href)
}
