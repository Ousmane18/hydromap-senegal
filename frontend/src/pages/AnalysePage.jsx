import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from "recharts"
import { PAL_RF, fmtHa, TYPES } from "../utils/helpers"

/* ─── Sous-composants ───────────────────────── */
function Card({ label, value, sub, color="text-emerald-600" }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs font-medium text-gray-700 mt-1">{label}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

const TipImportance = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 text-white text-xs rounded-xl px-3 py-2 shadow-xl">
      <p className="font-semibold">{payload[0].payload.name}</p>
      <p className="text-emerald-400">{payload[0].value}% d'importance</p>
    </div>
  )
}

const NC = "—"   // valeur affichée quand une métrique n'a pas pu être calculée

export default function AnalysePage({ resultats }) {

  /* État vide */
  if (!resultats) return (
    <div className="h-full flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <p className="text-5xl mb-4">🌲</p>
        <p className="text-base font-semibold text-gray-600">Aucun résultat</p>
        <p className="text-sm text-gray-400 mt-1">Lancez une détection depuis la sidebar</p>
      </div>
    </div>
  )

  const { n_points_detectes, statistiques, importance_variables,
          methode, periode, zone, metriques } = resultats

  /* Données graphiques */
  const dataRF = importance_variables && Object.keys(importance_variables).length
    ? Object.entries(importance_variables)
        .map(([name,value],i) => ({ name, value:+value.toFixed(1), fill:PAL_RF[i%PAL_RF.length] }))
        .sort((a,b)=>b.value-a.value)
    : []

  const dataPie = [
    { name:"Permanents",  value:statistiques.n_permanents,  fill:TYPES.permanent.fill  },
    { name:"Temporaires", value:statistiques.n_temporaires, fill:TYPES.temporaire.fill },
    { name:"Secondaires", value:statistiques.n_secondaires, fill:TYPES.secondaire.fill },
  ].filter(d=>d.value>0)

  /* Métriques RÉELLES renvoyées par le backend (null si non calculables) */
  const m  = metriques || null
  const M  = m?.matrice || null
  const fmtPct = v => (v == null ? NC : `${v}%`)

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-5">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* ── En-tête ── */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-wrap
          items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Analyse — {methode}</h1>
            <p className="text-xs text-gray-400 mt-1">
              Zone : <span className="text-gray-600 font-medium">{zone}</span> ·
              Période : <span className="text-gray-600 font-medium">{periode}</span> ·
              Méthode : <span className="text-emerald-600 font-medium">{methode}</span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-emerald-600">{n_points_detectes}</p>
            <p className="text-xs text-gray-400">points d'eau détectés</p>
          </div>
        </div>

        {/* ── Métriques validation ── */}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-2">
            Métriques de validation — référence JRC Global Surface Water
          </p>

          {m ? (
            <p className="text-[11px] text-gray-500 mb-2">
              Calculées sur {m.n_validation} pixels ({m.echantillon}) · Référence : {m.reference}.
              Indicatif : la référence est en Landsat 30 m, pas un relevé terrain.
            </p>
          ) : (
            <div className="mb-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 leading-relaxed">
              Métriques non calculables pour cette zone/période : trop peu de pixels d'eau dans la
              référence JRC (fréquent dans le Ferlo, où les mares sont petites et saisonnières).
              Essayez une zone avec plus d'eau permanente (Sine-Saloum) ou validez sur des points
              photo-interprétés.
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card label="Overall Accuracy" value={fmtPct(m?.oa)}   color="text-emerald-600" sub="Pixels bien classés" />
            <Card label="Kappa de Cohen"   value={m ? m.kappa : NC} color="text-blue-600"   sub="Accord inter-classes" />
            <Card label="F1-score (eau)"   value={fmtPct(m?.f1)}   color="text-purple-600" sub="Précision × Rappel" />
            <Card label="Rappel"           value={fmtPct(m?.rappel)} color="text-orange-500" sub="Eau bien détectée" />
          </div>
        </div>

        {/* ── Statistiques superficie ── */}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-2">
            Statistiques des points d'eau détectés
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card label="Superficie totale"  value={fmtHa(statistiques.superficie_totale_ha)}  color="text-gray-800" />
            <Card label="Superficie moyenne" value={fmtHa(statistiques.superficie_moyenne_ha)} color="text-gray-800" />
            <Card label="Plus grand point"   value={fmtHa(statistiques.superficie_max_ha)}     color="text-gray-800" />
            <Card label="Points permanents"  value={statistiques.n_permanents}                  color="text-emerald-600" />
          </div>
        </div>

        {/* ── Importance des variables (RF uniquement) ── */}
        {dataRF.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-800">
              Importance des variables — Random Forest
            </h2>
            <p className="text-xs text-gray-400 mt-0.5 mb-4">
              Contribution de chaque indice spectral et bande à la classification eau / non-eau.
            </p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={dataRF} margin={{top:4,right:4,left:-20,bottom:0}}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="name" tick={{fontSize:11,fill:"#6b7280"}} />
                <YAxis tick={{fontSize:11,fill:"#6b7280"}} unit="%" />
                <Tooltip content={<TipImportance />} />
                <Bar dataKey="value" radius={[4,4,0,0]}>
                  {dataRF.map((d,i)=><Cell key={i} fill={d.fill}/>)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* ── Pie + Matrice ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

          {/* Répartition par type */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-800 mb-4">Répartition par type</h2>
            {dataPie.length > 0
              ? (
                <ResponsiveContainer width="100%" height={190}>
                  <PieChart>
                    <Pie data={dataPie} cx="50%" cy="50%" innerRadius={45} outerRadius={78}
                      paddingAngle={3} dataKey="value"
                      label={({name,percent})=>`${name} ${(percent*100).toFixed(0)}%`}
                      labelLine={false}>
                      {dataPie.map((d,i)=><Cell key={i} fill={d.fill}/>)}
                    </Pie>
                    <Tooltip formatter={v=>[`${v} points`,""]} />
                  </PieChart>
                </ResponsiveContainer>
              )
              : <div className="h-40 flex items-center justify-center text-sm text-gray-400">Aucune donnée</div>
            }
          </div>

          {/* Matrice de confusion */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-gray-800 mb-4">Matrice de confusion</h2>
            {M ? (
              <>
                <table className="w-full text-xs">
                  <thead>
                    <tr>
                      <th className="p-2" />
                      <th className="p-2 text-center text-gray-500 font-medium bg-gray-50 rounded">Prédit Non-Eau</th>
                      <th className="p-2 text-center text-gray-500 font-medium bg-gray-50 rounded">Prédit Eau</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="p-2 font-medium text-gray-600">Réel Non-Eau</td>
                      <td className="p-2 text-center bg-emerald-50 text-emerald-800 font-bold text-base rounded">{M.tn}</td>
                      <td className="p-2 text-center bg-red-50 text-red-600 rounded">{M.fp}</td>
                    </tr>
                    <tr>
                      <td className="p-2 font-medium text-gray-600">Réel Eau</td>
                      <td className="p-2 text-center bg-red-50 text-red-600 rounded">{M.fn}</td>
                      <td className="p-2 text-center bg-emerald-50 text-emerald-800 font-bold text-base rounded">{M.tp}</td>
                    </tr>
                  </tbody>
                </table>
                <div className="grid grid-cols-2 gap-2 mt-4">
                  {[
                    ["Précision",   fmtPct(m.precision),   "text-blue-600"  ],
                    ["Spécificité", fmtPct(m.specificite), "text-purple-600"],
                  ].map(([l,v,c])=>(
                    <div key={l} className="text-center p-2 bg-gray-50 rounded-lg">
                      <p className={`text-lg font-bold ${c}`}>{v}</p>
                      <p className="text-[10px] text-gray-400 mt-0.5">{l}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-40 flex items-center justify-center text-sm text-gray-400 text-center px-4">
                Matrice non disponible (référence insuffisante)
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
