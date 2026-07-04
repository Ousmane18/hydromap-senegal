import { useEffect, useState } from "react"
import { CheckCircle, Wifi, WifiOff } from "lucide-react"
import { getSante } from "../utils/api"
import { ZONES } from "../utils/helpers"

const TITRES = {
  carte:    "Carte interactive",
  analyse:  "Analyse Random Forest",
  temporel: "Dynamique temporelle",
  export:   "Export des données",
}

export default function Topbar({ page, zone, resultats }) {
  const [sante, setSante] = useState(null)

  useEffect(() => {
    getSante()
      .then(setSante)
      .catch(() => setSante({ gee_connecte: false }))
  }, [])

  return (
    <header className="flex items-center justify-between px-5 py-3
      border-b border-gray-200 bg-white flex-shrink-0">

      {/* Titre */}
      <div>
        <h1 className="text-sm font-bold text-gray-900 leading-none">{TITRES[page]}</h1>
        <p className="text-[11px] text-gray-400 mt-0.5">
          Sentinel-2 · Google Earth Engine · Random Forest
        </p>
      </div>

      {/* Badges droite */}
      <div className="flex items-center gap-2">

        {/* Zone active */}
        <span className="text-[11px] bg-blue-50 text-blue-600 border border-blue-100
          px-2.5 py-1 rounded-full font-medium">
          📍 {ZONES[zone]?.label}
        </span>

        {/* Résultats */}
        {resultats && (
          <span className="anim-fade flex items-center gap-1 text-[11px] bg-emerald-50
            text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
            <CheckCircle size={11} />
            {resultats.n_points_detectes} points détectés
          </span>
        )}

        {/* Statut GEE */}
        {sante && (
          <span className={`flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full
            border font-medium
            ${sante.gee_connecte
              ? "bg-green-50 text-green-700 border-green-200"
              : "bg-gray-50 text-gray-400 border-gray-200"}`}>
            {sante.gee_connecte
              ? <><Wifi size={11}/> GEE actif</>
              : <><WifiOff size={11}/> GEE offline</>}
          </span>
        )}
      </div>
    </header>
  )
}
