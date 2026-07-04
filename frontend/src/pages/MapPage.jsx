import { useEffect, useRef, useState } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { Layers, ChevronDown } from "lucide-react"
import { ZONES, typeParSup, TYPES, fmtHa } from "../utils/helpers"

/* ─── Fonds de carte ────────────────────────── */
const FONDS = {
  satellite: {
    label:"Satellite",
    url:"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr:"Esri World Imagery",
  },
  terrain: {
    label:"Terrain",
    url:"https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr:"OpenTopoMap",
  },
  plan: {
    label:"Plan",
    url:"https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr:"OpenStreetMap",
  },
}

export default function MapPage({ zone, resultats, loading, msg }) {
  const divRef    = useRef(null)
  const mapRef    = useRef(null)
  const tileRef   = useRef(null)
  const layerRef  = useRef(null)

  const [fond,      setFond]      = useState("satellite")
  const [menu,      setMenu]      = useState(false)
  const [selec,     setSelec]     = useState(null)

  /* ── Init carte ──────────────────────────── */
  useEffect(() => {
    if (mapRef.current) return
    const map = L.map(divRef.current, { center:[14.5,-14.5], zoom:7, zoomControl:false })
    tileRef.current = L.tileLayer(FONDS.satellite.url,
      { attribution:FONDS.satellite.attr, maxZoom:19 }).addTo(map)
    L.control.zoom({ position:"bottomright" }).addTo(map)
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  /* ── Changer fond ────────────────────────── */
  useEffect(() => {
    const map = mapRef.current
    if (!map || !tileRef.current) return
    map.removeLayer(tileRef.current)
    const f = FONDS[fond]
    tileRef.current = L.tileLayer(f.url, { attribution:f.attr, maxZoom:19 }).addTo(map)
  }, [fond])

  /* ── Centrer sur zone ────────────────────── */
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const z = ZONES[zone]
    if (z) map.setView(z.centre, z.zoom, { animate:true })
  }, [zone])

  /* ── Afficher résultats GeoJSON ──────────── */
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (layerRef.current) { map.removeLayer(layerRef.current); layerRef.current = null }
    if (!resultats?.geojson?.features?.length) return

    const layer = L.geoJSON(resultats.geojson, {
      style: feat => {
        const c = typeParSup(feat.properties?.superficie_ha || 0)
        return { color:c.border, weight:1.5, opacity:.9, fillColor:c.fill, fillOpacity:.5 }
      },
      onEachFeature: (feat, lyr) => {
        const p = feat.properties || {}
        const c = typeParSup(p.superficie_ha || 0)
        lyr.bindTooltip(
          `<strong style="color:${c.fill}">${p.type_permanence||"—"}</strong><br>${fmtHa(p.superficie_ha)}`,
          { className:"hm-tip", sticky:true }
        )
        lyr.on("click",     () => setSelec(p))
        lyr.on("mouseover", function(){ this.setStyle({fillOpacity:.75,weight:2.5}) })
        lyr.on("mouseout",  function(){ this.setStyle({fillOpacity:.5, weight:1.5}) })
      },
    })
    layer.addTo(map)
    layerRef.current = layer
    try { if (layer.getBounds().isValid()) map.fitBounds(layer.getBounds(),{padding:[40,40]}) }
    catch(_){}
  }, [resultats])

  return (
    <div className="relative w-full h-full">

      {/* Carte */}
      <div ref={divRef} className="w-full h-full" />

      {/* ── Loader overlay ── */}
      {loading && (
        <div className="absolute inset-0 bg-black/50 z-[500] flex items-center justify-center">
          <div className="glass rounded-2xl p-8 shadow-2xl flex flex-col items-center gap-4 max-w-xs w-full mx-4">
            <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full anim-spin" />
            <div className="text-center">
              <p className="text-sm font-bold text-gray-900">Analyse GEE en cours</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed min-h-[2rem]">
                {msg || "Initialisation…"}
              </p>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1">
              <div className="bg-emerald-500 h-1 rounded-full w-2/3 anim-pulse" />
            </div>
          </div>
        </div>
      )}

      {/* ── Sélecteur fond ── */}
      <div className="absolute top-3 left-3 z-[400]">
        <div className="glass rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <button onClick={() => setMenu(v=>!v)}
            className="flex items-center gap-2 px-3 py-2 text-xs text-gray-700 hover:bg-gray-50">
            <Layers size={13} />
            <span className="font-medium">{FONDS[fond].label}</span>
            <ChevronDown size={11} className={`transition-transform ${menu?"rotate-180":""}`} />
          </button>
          {menu && (
            <div className="border-t border-gray-100">
              {Object.entries(FONDS).map(([id,f]) => (
                <button key={id}
                  onClick={() => { setFond(id); setMenu(false) }}
                  className={`w-full text-left px-3 py-1.5 text-xs transition-colors
                    ${fond===id ? "bg-emerald-50 text-emerald-700 font-medium":"text-gray-600 hover:bg-gray-50"}`}>
                  {f.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Légende ── */}
      <div className="absolute bottom-8 left-3 z-[400] glass rounded-xl shadow-sm
        border border-gray-200 p-3">
        <p className="text-[10px] text-gray-400 font-semibold uppercase tracking-wide mb-2">
          Type de point d'eau
        </p>
        {Object.values(TYPES).map(({ fill, label }) => (
          <div key={label} className="flex items-center gap-2 mb-1.5 last:mb-0">
            <div className="w-3 h-3 rounded-full flex-shrink-0" style={{background:fill}} />
            <span className="text-[11px] text-gray-600">{label}</span>
          </div>
        ))}
      </div>

      {/* ── Barre NDWI ── */}
      <div className="absolute bottom-8 right-14 z-[400] glass rounded-xl shadow-sm
        border border-gray-200 p-3 w-28">
        <p className="text-[10px] text-gray-400 font-semibold mb-1.5">Indice NDWI</p>
        <div className="h-2.5 rounded-full"
          style={{background:"linear-gradient(to right,#d4a76a,#a8c5a0,#0D9E74)"}} />
        <div className="flex justify-between text-[9px] text-gray-400 mt-1">
          <span>−1</span><span>0</span><span>+1</span>
        </div>
        <div className="flex justify-between text-[9px] text-gray-300 mt-0.5">
          <span>Sol sec</span><span>Eau</span>
        </div>
      </div>

      {/* ── Stats flottantes ── */}
      {resultats && !loading && (
        <div className="absolute top-3 right-3 z-[400] glass rounded-xl shadow-sm
          border border-gray-200 p-4 w-52 anim-fade">
          <div className="flex items-center gap-1.5 mb-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500 anim-pulse" />
            <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wide">
              Résultats
            </span>
          </div>
          {[
            ["Points détectés",  resultats.n_points_detectes],
            ["Superficie tot.",  fmtHa(resultats.statistiques?.superficie_totale_ha)],
            ["Permanents",       resultats.statistiques?.n_permanents],
            ["Temporaires",      resultats.statistiques?.n_temporaires],
            ["Méthode", resultats.methode==="random_forest"?"RF":
                        resultats.methode==="les_deux"?"RF+Seuil":"Seuillage"],
            ["Durée GEE", resultats.duree_secondes ? `${resultats.duree_secondes}s`:"—"],
          ].map(([k,v]) => (
            <div key={k} className="flex justify-between text-xs py-1
              border-b border-gray-100 last:border-0">
              <span className="text-gray-400">{k}</span>
              <span className="font-semibold text-gray-800">{v}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── Popup point sélectionné ── */}
      {selec && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[400]
          glass rounded-2xl shadow-lg border border-gray-200 p-4 w-72 anim-fade">
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="text-sm font-bold text-gray-900 capitalize">{selec.type_permanence}</p>
              <p className="text-[11px] text-gray-400">{selec.zone}</p>
            </div>
            <button onClick={() => setSelec(null)}
              className="text-gray-300 hover:text-gray-600 text-xl leading-none">×</button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              ["Superficie", fmtHa(selec.superficie_ha)],
              ["En m²", `${Math.round(selec.superficie_m2||0).toLocaleString()}`],
              ["Latitude",  (+selec.latitude||0).toFixed(5)],
              ["Longitude", (+selec.longitude||0).toFixed(5)],
            ].map(([k,v]) => (
              <div key={k} className="bg-gray-50 rounded-lg p-2">
                <p className="text-[9px] text-gray-400 uppercase tracking-wide">{k}</p>
                <p className="text-xs font-semibold text-gray-800 mt-0.5">{v}</p>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-gray-400 text-center mt-2">
            Détecté le {selec.date_detection || "—"}
          </p>
        </div>
      )}

      {/* ── État vide ── */}
      {!resultats && !loading && (
        <div className="absolute inset-0 pointer-events-none z-[300]
          flex items-center justify-center">
          <div className="glass rounded-2xl p-6 border border-gray-200 text-center shadow-sm max-w-xs">
            <p className="text-3xl mb-2">🛰️</p>
            <p className="text-sm font-semibold text-gray-700">Aucune détection</p>
            <p className="text-xs text-gray-400 mt-1 leading-relaxed">
              Configurez les paramètres<br/>et cliquez sur <strong>Lancer la détection</strong>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
