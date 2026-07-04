import { useState } from "react"
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts"
import { getAnalyseTemp } from "../utils/api"
import { fmtHa, labelSaison } from "../utils/helpers"
import { RefreshCw, AlertCircle, Clock } from "lucide-react"

const DEMO = [
  { periode:"Hivern. 2021", n_points:38, superficie_ha:1420, saison:"hivernage"    },
  { periode:"S.sèche 2022", n_points:14, superficie_ha:380,  saison:"saison_seche" },
  { periode:"Hivern. 2022", n_points:52, superficie_ha:1980, saison:"hivernage"    },
  { periode:"S.sèche 2023", n_points:11, superficie_ha:290,  saison:"saison_seche" },
  { periode:"Hivern. 2023", n_points:61, superficie_ha:2340, saison:"hivernage"    },
  { periode:"S.sèche 2024", n_points:18, superficie_ha:510,  saison:"saison_seche" },
]

const COL = s => s === "hivernage" ? "#0D9E74" : "#EF9F27"

const Tip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 text-white text-xs rounded-xl px-3 py-2 shadow-xl">
      <p className="font-bold mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name} : <strong>{p.value}{p.dataKey === "superficie_ha" ? " ha" : ""}</strong>
        </p>
      ))}
    </div>
  )
}

function StatCard({ label, value, color = "text-emerald-600" }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-[11px] text-gray-400 mt-1 leading-tight">{label}</p>
    </div>
  )
}

export default function TemporelPage({ zone }) {
  const [data,       setData]       = useState(DEMO)
  const [loading,    setLoading]    = useState(false)
  const [erreur,     setErreur]     = useState(null)
  const [annees,     setAnnees]     = useState([2021, 2022, 2023])
  const [isDemo,     setIsDemo]     = useState(true)
  const [progression,setProgression]= useState("")  // message de progression

  const toggleAnnee = a =>
    setAnnees(prev => prev.includes(a) ? prev.filter(x => x !== a) : [...prev, a].sort())

  const charger = async () => {
    setLoading(true)
    setErreur(null)
    setProgression(`Calcul de ${annees.length * 2} périodes en cours...`)

    // Messages de progression animés
    const msgs = [
      `Chargement hivernage ${annees[0]}...`,
      `Calcul saison sèche ${annees[0]+1}...`,
      annees[1] ? `Chargement hivernage ${annees[1]}...` : "Finalisation...",
      annees[2] ? `Calcul saison sèche ${annees[2]+1}...` : "Calcul des statistiques...",
      "Compilation des résultats...",
    ]
    let idx = 0
    const timer = setInterval(() => {
      idx = Math.min(idx + 1, msgs.length - 1)
      setProgression(msgs[idx])
    }, 25000) // ~25s par période

    try {
      const res = await getAnalyseTemp(zone, annees)
      const formatted = res.resume.map(r => ({
        periode:      labelSaison(r.saison, r.annee),
        n_points:     r.n_points,
        superficie_ha:r.superficie_ha,
        saison:       r.saison,
      }))
      setData(formatted)
      setIsDemo(false)
    } catch (e) {
      setErreur(e.message)
    } finally {
      clearInterval(timer)
      setLoading(false)
      setProgression("")
    }
  }

  const hiv = data.filter(d => d.saison === "hivernage")
  const sec = data.filter(d => d.saison === "saison_seche")
  const moy = (arr, k) => arr.length ? +(arr.reduce((s, d) => s + d[k], 0) / arr.length).toFixed(1) : 0

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-5">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* En-tête */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm
          flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Dynamique temporelle des points d'eau</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              Hivernage vs saison sèche · {zone.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {[2020, 2021, 2022, 2023].map(a => (
              <button key={a} onClick={() => toggleAnnee(a)}
                disabled={loading}
                className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium
                  transition-colors disabled:opacity-50
                  ${annees.includes(a)
                    ? "bg-emerald-600 text-white border-emerald-600"
                    : "bg-white text-gray-500 border-gray-200 hover:border-emerald-400"}`}>
                {a}
              </button>
            ))}
            <button onClick={charger} disabled={loading}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg
                bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-60
                transition-colors font-medium">
              <RefreshCw size={12} className={loading ? "anim-spin" : ""} />
              {loading ? "En cours..." : "Actualiser GEE"}
            </button>
          </div>
        </div>

        {/* Barre de progression */}
        {loading && (
          <div className="bg-white border border-emerald-200 rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent
                rounded-full anim-spin flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-gray-800">
                  Analyse GEE en cours
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{progression}</p>
              </div>
            </div>
            {/* Barre de périodes */}
            <div className="flex gap-1.5 flex-wrap">
              {annees.flatMap(a => [
                { label:`Hivern. ${a}`,    key:`h${a}` },
                { label:`S.sèche ${a+1}`,  key:`s${a}` },
              ]).map(({ label, key }, i) => (
                <div key={key}
                  className={`text-[10px] px-2 py-1 rounded-md font-medium
                    transition-all duration-500
                    ${i < 1 ? "bg-emerald-100 text-emerald-700"
                             : "bg-gray-100 text-gray-400"}`}>
                  {label}
                </div>
              ))}
            </div>
            <p className="text-[10px] text-gray-400 mt-2">
              ⏱ ~25-35s par période · {annees.length * 2} périodes au total
              · La 2ème relance sera instantanée (cache)
            </p>
          </div>
        )}

        {/* Avertissement démo */}
        {isDemo && !loading && (
          <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200
            rounded-xl text-xs text-amber-700">
            <AlertCircle size={14} className="flex-shrink-0" />
            Données de démonstration. Cliquez <strong className="mx-1">Actualiser GEE</strong>
            pour charger les vraies données (patience : ~{annees.length * 2 * 30}s la première fois).
          </div>
        )}

        {/* Info cache */}
        {!isDemo && !loading && (
          <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200
            rounded-xl text-xs text-blue-700">
            <Clock size={14} className="flex-shrink-0" />
            Données GEE réelles affichées. La prochaine relance sera
            <strong className="mx-1">instantanée</strong> (résultats en cache).
          </div>
        )}

        {/* Erreur */}
        {erreur && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200
            rounded-xl text-xs text-red-600">
            <AlertCircle size={14} />{erreur}
          </div>
        )}

        {/* Statistiques de synthèse */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Moy. points — hivernage"
            value={moy(hiv,"n_points")} color="text-emerald-600" />
          <StatCard label="Moy. points — saison sèche"
            value={moy(sec,"n_points")} color="text-orange-500" />
          <StatCard label="Superficie moy. — hivernage"
            value={fmtHa(moy(hiv,"superficie_ha"))} color="text-emerald-600" />
          <StatCard label="Superficie moy. — s. sèche"
            value={fmtHa(moy(sec,"superficie_ha"))} color="text-orange-500" />
        </div>

        {/* Graphique 1 : nombre de points */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-800">Nombre de points d'eau détectés</h2>
          <p className="text-xs text-gray-400 mt-0.5 mb-4">
            Les pics correspondent à l'hivernage (juillet–octobre).
          </p>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={data} margin={{ top:4, right:4, left:-20, bottom:0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="periode" tick={{ fontSize:10, fill:"#9ca3af" }} />
              <YAxis tick={{ fontSize:11, fill:"#9ca3af" }} />
              <Tooltip content={<Tip />} />
              <Bar dataKey="n_points" name="Points d'eau" radius={[4,4,0,0]}>
                {data.map((d,i) => <Cell key={i} fill={COL(d.saison)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 justify-center">
            {[["#0D9E74","Hivernage"],["#EF9F27","Saison sèche"]].map(([c,l])=>(
              <div key={l} className="flex items-center gap-1.5 text-xs text-gray-500">
                <div className="w-3 h-3 rounded-sm" style={{background:c}}/>{l}
              </div>
            ))}
          </div>
        </div>

        {/* Graphique 2 : superficie */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-800">Superficie totale en eau (ha)</h2>
          <p className="text-xs text-gray-400 mt-0.5 mb-4">
            Indicateur de disponibilité en eau pour les populations et le bétail.
          </p>
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={data} margin={{ top:4, right:4, left:-20, bottom:0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="periode" tick={{ fontSize:10, fill:"#9ca3af" }} />
              <YAxis tick={{ fontSize:11, fill:"#9ca3af" }} unit=" ha" />
              <Tooltip content={<Tip />} />
              <Line type="monotone" dataKey="superficie_ha" name="Superficie"
                stroke="#378ADD" strokeWidth={2.5}
                dot={{ r:4, fill:"#378ADD", strokeWidth:0 }} activeDot={{ r:6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Note mémoire */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4
          text-xs text-blue-800 leading-relaxed">
          <strong>📝 Pour le mémoire :</strong> Ce graphique illustre la dynamique
          hydrologique saisonnière sahélienne. Le ratio hivernage/saison sèche
          quantifie la pression sur les ressources en eau permanentes.
        </div>

      </div>
    </div>
  )
}
