import { Droplets, Map, BarChart2, Clock, Download, Play, Loader, RotateCcw, Info } from "lucide-react"
import { ZONES } from "../utils/helpers"

const NAV = [
  { id:"carte",    label:"Carte",      Icon:Map       },
  { id:"analyse",  label:"Analyse RF", Icon:BarChart2 },
  { id:"temporel", label:"Temporel",   Icon:Clock     },
  { id:"export",   label:"Export",     Icon:Download  },
]

function Slider({ label, value, min, max, step, color="emerald", unit="", onChange, hint }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500">{label}</span>
        <span className={`font-bold text-${color}-600`}>{value}{unit}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(+e.target.value)}
        className={`w-full h-1.5 rounded-full accent-${color}-600`} />
      <div className="flex justify-between text-[9px] text-gray-300 mt-0.5">
        <span>{min}{unit}</span><span>{max}{unit}</span>
      </div>
      {hint && <p className="text-[10px] text-gray-400 mt-0.5 italic">{hint}</p>}
    </div>
  )
}

// Config par défaut optimisée v2
export const CONFIG_DEFAUT = {
  date_debut:     "2023-08-01",   // pic hivernage
  date_fin:       "2023-09-30",   // meilleure période pour les mares
  methode:        "awei",          // AWEI : plus sensible pour débuter
  n_arbres:       50,              // rapide pour les tests
  n_points_train: 150,
  seuil_ndwi:     0.0,
  seuil_mndwi:    0.0,
  nuage_max:      30,              // plus permissif
  surface_min_m2: 400,             // 1 pixel = 400 m² (20m × 20m)
}

export default function Sidebar({ page, setPage, zone, setZone, config, setConfig,
                                   loading, erreur, onDetect, onReset }) {
  const set = (k, v) => setConfig(c => ({ ...c, [k]: v }))

  return (
    <aside className="w-56 shrink-0 flex flex-col bg-gray-50 border-r border-gray-200 overflow-hidden">

      {/* ── Logo ── */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-emerald-600 flex items-center justify-center shadow-sm">
            <Droplets size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-gray-900 leading-none">HydroMap SN</p>
            <p className="text-[10px] text-gray-400 mt-0.5">Sentinel-2 · GEE · RF v2</p>
          </div>
        </div>
      </div>

      {/* ── Navigation ── */}
      <nav className="p-2 border-b border-gray-200">
        {NAV.map(({ id, label, Icon }) => (
          <button key={id} onClick={() => setPage(id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm mb-0.5 transition-all
              ${page === id
                ? "bg-white text-emerald-700 font-semibold shadow-sm border border-gray-200"
                : "text-gray-500 hover:bg-gray-100 hover:text-gray-800"}`}>
            <Icon size={14} />{label}
          </button>
        ))}
      </nav>

      {/* ── Paramètres ── */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">

        {/* Zone */}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-1.5">
            Zone d'étude
          </p>
          <select value={zone} onChange={e => setZone(e.target.value)}
            className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white
              text-gray-800 focus:outline-none focus:ring-1 focus:ring-emerald-500">
            {Object.entries(ZONES).map(([id,z]) => (
              <option key={id} value={id}>{z.label}</option>
            ))}
          </select>
        </div>

        {/* Période */}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-1.5">
            Période
          </p>
          <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg mb-2">
            <p className="text-[10px] text-emerald-700 leading-relaxed">
              💡 <strong>Recommandé :</strong> Août–Septembre pour les mares du Ferlo (pic hivernage)
            </p>
          </div>
          {[["date_debut","Début"],["date_fin","Fin"]].map(([k,lbl]) => (
            <div key={k} className="mb-1.5">
              <p className="text-[10px] text-gray-400 mb-0.5">{lbl}</p>
              <input type="date" value={config[k]} onChange={e => set(k, e.target.value)}
                className="w-full text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-white
                  text-gray-800 focus:outline-none focus:ring-1 focus:ring-emerald-500" />
            </div>
          ))}
        </div>

        {/* Méthode */}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-1.5">
            Méthode de détection
          </p>
          <select value={config.methode} onChange={e => set("methode", e.target.value)}
            className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white
              text-gray-800 focus:outline-none focus:ring-1 focus:ring-emerald-500">
            <option value="awei">💧 AWEI (recommandé)</option>
            <option value="random_forest">🌲 Random Forest</option>
            <option value="seuillage">📊 Seuillage NDWI/MNDWI</option>
            <option value="les_deux">🔀 RF + Seuillage</option>
          </select>
          {/* Explication méthode choisie */}
          <div className="mt-1.5 p-2 bg-gray-100 rounded-lg">
            <p className="text-[10px] text-gray-500 leading-relaxed">
              {config.methode === "awei"          && "AWEI est le plus sensible aux petites mares sahéliennes. Idéal pour débuter."}
              {config.methode === "random_forest" && "RF classe chaque pixel avec 12 features spectrales. Plus précis mais plus lent."}
              {config.methode === "seuillage"     && "Seuillage simple et rapide. Bon pour comparer avec RF dans le mémoire."}
              {config.methode === "les_deux"      && "Combine RF et seuillage (union). Détecte le maximum de points d'eau."}
            </p>
          </div>
        </div>

        {/* Paramètres RF */}
        {(config.methode === "random_forest" || config.methode === "les_deux") && (
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-2">
              Random Forest
            </p>
            <div className="space-y-3">
              <Slider label="Arbres" value={config.n_arbres}
                min={10} max={200} step={10} color="emerald"
                onChange={v => set("n_arbres", v)}
                hint="50 = rapide, 100 = précis" />
              <Slider label="Points entraîn." value={config.n_points_train}
                min={50} max={300} step={50} color="emerald"
                onChange={v => set("n_points_train", v)} />
            </div>
          </div>
        )}

        {/* Seuils */}
        {(config.methode === "seuillage" || config.methode === "les_deux") && (
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-2">
              Seuils spectraux
            </p>
            <div className="space-y-3">
              <Slider label="Seuil NDWI" value={config.seuil_ndwi}
                min={-0.5} max={0.5} step={0.05} color="blue"
                onChange={v => set("seuil_ndwi", v)}
                hint="0.0 = recommandé zones semi-arides" />
              <Slider label="Seuil MNDWI" value={config.seuil_mndwi}
                min={-0.5} max={0.5} step={0.05} color="teal"
                onChange={v => set("seuil_mndwi", v)} />
            </div>
          </div>
        )}

        {/* Surface minimale */}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-1">
            Surface minimale
          </p>
          <div className="space-y-2">
            {[
              [400,  "400 m² — 1 pixel (très sensible)"],
              [2000, "2 000 m² — 5 pixels (recommandé)"],
              [5000, "5 000 m² — filtre le bruit"],
            ].map(([v, lbl]) => (
              <label key={v}
                className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors
                  ${config.surface_min_m2===v
                    ?"bg-emerald-50 border-emerald-400 text-emerald-700 font-medium"
                    :"border-gray-200 text-gray-500 hover:border-gray-300"}`}>
                <input type="radio" name="surface_min"
                  checked={config.surface_min_m2===v}
                  onChange={() => set("surface_min_m2", v)}
                  className="accent-emerald-600" />
                <span className="text-[11px]">{lbl}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Nuages */}
        <div>
          <Slider label="Nuages max" value={config.nuage_max}
            min={10} max={50} step={5} color="sky" unit="%"
            onChange={v => set("nuage_max", v)}
            hint="30% = bon compromis saison des pluies" />
        </div>

      </div>

      {/* ── Boutons ── */}
      <div className="p-3 border-t border-gray-200 space-y-2">
        {erreur && (
          <p className="text-[10px] text-red-500 bg-red-50 rounded-lg p-2 leading-tight">{erreur}</p>
        )}
        <button onClick={onDetect} disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm
            font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition-all
            shadow-sm active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed">
          {loading
            ? <><Loader size={14} className="anim-spin" /> Analyse…</>
            : <><Play  size={14} /> Lancer la détection</>}
        </button>
        {erreur && (
          <button onClick={onReset}
            className="w-full flex items-center justify-center gap-1 py-1 text-xs
              text-gray-400 hover:text-gray-600 transition-colors">
            <RotateCcw size={10} /> Réinitialiser
          </button>
        )}
      </div>
    </aside>
  )
}
