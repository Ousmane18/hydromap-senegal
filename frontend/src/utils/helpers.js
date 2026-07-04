/**
 * utils/helpers.js
 * CORRECTION v2 : seuils superficie adaptés aux mares sahéliennes réelles
 *
 * Données terrain Ferlo/Sénégal :
 *   - Mares typiques du Ferlo   : 0.5 à 8 ha
 *   - Grandes retenues           : 10 à 50 ha
 *   - Lac de Guiers / grands lacs: > 100 ha
 *   → Les anciens seuils (>50 ha perm, >5 ha temp) étaient trop restrictifs
 */

// ── Zones d'étude ──────────────────────────
export const ZONES = {
  ferlo_nord:        { label:"Ferlo Nord",        centre:[15.25,-14.5],  zoom:8 },
  ferlo_sud:         { label:"Ferlo Sud",          centre:[14.0, -13.5],  zoom:8 },
  sine_saloum:       { label:"Sine-Saloum",        centre:[14.0, -15.5],  zoom:8 },
  bassin_arachidier: { label:"Bassin Arachidier",  centre:[14.5, -15.0],  zoom:8 },
  senegal_nord:      { label:"Sénégal Nord",       centre:[15.75,-14.75], zoom:7 },
}

// ── Types adaptés aux mares sahéliennes ────
// CORRECTION v2 : seuils abaissés
//   permanent  : > 10 ha  (retenues, grands lacs)
//   temporaire : 1–10 ha  (mares typiques du Ferlo)
//   secondaire : < 1 ha   (petites mares, à vérifier terrain)
export const TYPES = {
  permanent:  { fill:"#0D9E74", border:"#065f46", label:"Permanent  (> 10 ha)" },
  temporaire: { fill:"#EF9F27", border:"#92400e", label:"Temporaire (1–10 ha)" },
  secondaire: { fill:"#378ADD", border:"#1e40af", label:"Secondaire (<  1 ha)"  },
}

export function typeParSup(ha) {
  if (ha > 10) return TYPES.permanent   // > 10 ha
  if (ha > 1)  return TYPES.temporaire  // 1–10 ha
  return TYPES.secondaire               // < 1 ha
}

// ── Formatage ──────────────────────────────
export function fmtHa(v) {
  if (v == null || isNaN(v)) return "—"
  if (v >= 1000) return `${(v/1000).toFixed(1)} kha`
  if (v >= 1)    return `${(+v).toFixed(2)} ha`
  return `${Math.round(v*10000)} m²`
}

export function fmtDate(s) {
  if (!s) return "—"
  return new Date(s).toLocaleDateString("fr-FR",
    { day:"2-digit", month:"short", year:"numeric" })
}

export function nomFichier(zone, date, ext) {
  return `hydromap_${zone}_${date}.${ext}`
}

export function labelSaison(saison, annee) {
  return saison === "hivernage" ? `Hivern. ${annee}` : `S.sèche ${annee}`
}

// ── Palette RF ─────────────────────────────
export const PAL_RF = [
  "#0D9E74","#1ABAAB","#378ADD","#5B8CF7",
  "#9B6FD8","#EF9F27","#EF5F27","#C74B4B",
  "#85C740","#C7A040","#40B8C7","#C74070",
]
