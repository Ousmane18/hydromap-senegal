import { useState } from "react"
import { FileJson, FileText, Map, Download, CheckCircle, AlertCircle } from "lucide-react"
import { dlGeoJSON, dlCSV } from "../utils/api"
import { fmtHa } from "../utils/helpers"

function BtnExport({ Icon, titre, desc, couleur, onClick, disabled }) {
  const [ok, setOk] = useState(false)
  const handle = () => { onClick(); setOk(true); setTimeout(()=>setOk(false),2500) }
  const C = ok ? "emerald" : couleur
  return (
    <button onClick={handle} disabled={disabled}
      className={`flex flex-col items-center gap-3 p-6 bg-white border rounded-xl shadow-sm
        transition-all disabled:opacity-40 disabled:cursor-not-allowed
        ${!disabled?`hover:shadow-md hover:scale-[1.02] active:scale-[0.98] hover:border-${C}-400`:"border-gray-200"}`}>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-${C}-50`}>
        {ok ? <CheckCircle size={24} className="text-emerald-600" />
             : <Icon size={24} className={`text-${C}-600`} />}
      </div>
      <div className="text-center">
        <p className="text-sm font-bold text-gray-800">{ok?"Téléchargé !":titre}</p>
        <p className="text-[11px] text-gray-400 mt-0.5">{desc}</p>
      </div>
      <div className={`flex items-center gap-1 text-xs font-semibold text-${C}-600`}>
        {ok ? <CheckCircle size={12}/> : <Download size={12}/>}
        {ok ? "Enregistré" : titre}
      </div>
    </button>
  )
}

export default function ExportPage({ resultats, zone, config }) {
  if (!resultats) return (
    <div className="h-full flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <AlertCircle size={48} className="text-gray-300 mx-auto mb-4" />
        <p className="text-base font-semibold text-gray-600">Aucune donnée à exporter</p>
        <p className="text-sm text-gray-400 mt-1">Lancez d'abord une détection</p>
      </div>
    </div>
  )

  const { geojson, statistiques, n_points_detectes, methode, periode } = resultats
  const features = geojson?.features || []
  const date     = config?.date_debut || "export"
  const base     = `hydromap_${zone}_${date}`

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-5">
      <div className="max-w-3xl mx-auto space-y-5">

        {/* En-tête */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h1 className="text-lg font-bold text-gray-900">Export des données</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {n_points_detectes} points · {zone.replace(/_/g," ")} · {periode}
          </p>
        </div>

        {/* Boutons */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <BtnExport Icon={FileJson} titre="GeoJSON" couleur="emerald"
            desc="QGIS · ArcGIS · Mapbox · GeoPandas"
            onClick={()=>dlGeoJSON(geojson,`${base}.geojson`)}
            disabled={!features.length} />
          <BtnExport Icon={FileText} titre="CSV" couleur="blue"
            desc="Excel · Pandas · R · Tableur"
            onClick={()=>dlCSV(features,`${base}.csv`)}
            disabled={!features.length} />
          <div className="flex flex-col items-center gap-3 p-6 bg-white border border-gray-200
            rounded-xl shadow-sm opacity-40 cursor-not-allowed">
            <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center">
              <Map size={24} className="text-purple-600" />
            </div>
            <div className="text-center">
              <p className="text-sm font-bold text-gray-800">Shapefile</p>
              <p className="text-[11px] text-gray-400 mt-0.5">Via endpoint /api/export/shapefile</p>
            </div>
            <p className="text-xs text-gray-400">Disponible côté serveur</p>
          </div>
        </div>

        {/* Contenu */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-800 mb-4">Contenu des fichiers</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-2">Données</p>
              {[
                ["Nombre de points",   n_points_detectes],
                ["Points permanents",  statistiques.n_permanents],
                ["Points temporaires", statistiques.n_temporaires],
                ["Points secondaires", statistiques.n_secondaires],
                ["Superficie totale",  fmtHa(statistiques.superficie_totale_ha)],
                ["Superficie max",     fmtHa(statistiques.superficie_max_ha)],
              ].map(([k,v])=>(
                <div key={k} className="flex justify-between text-xs py-1.5
                  border-b border-gray-100 last:border-0">
                  <span className="text-gray-400">{k}</span>
                  <span className="font-semibold text-gray-700">{v}</span>
                </div>
              ))}
            </div>
            <div>
              <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold mb-2">Métadonnées</p>
              {[
                ["Projection",      "WGS84 · EPSG:4326"],
                ["Résolution",      "20 m (Sentinel-2)"],
                ["Méthode",         methode],
                ["Géométrie",       "Polygones"],
                ["Zone",            zone.replace(/_/g," ")],
                ["Période",         periode],
              ].map(([k,v])=>(
                <div key={k} className="flex justify-between text-xs py-1.5
                  border-b border-gray-100 last:border-0">
                  <span className="text-gray-400">{k}</span>
                  <span className="font-semibold text-gray-700 text-right">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Attributs */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
          <h2 className="text-sm font-bold text-gray-800 mb-3">Attributs de chaque polygone</h2>
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50">
                <th className="text-left p-2 font-semibold text-gray-600 rounded-l">Attribut</th>
                <th className="text-left p-2 font-semibold text-gray-600">Type</th>
                <th className="text-left p-2 font-semibold text-gray-600 rounded-r">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["superficie_m2",   "Float", "Superficie en mètres carrés"],
                ["superficie_ha",   "Float", "Superficie en hectares"],
                ["latitude",        "Float", "Latitude du centroïde"],
                ["longitude",       "Float", "Longitude du centroïde"],
                ["type_permanence", "String","permanent / temporaire / secondaire"],
                ["zone",            "String","Zone d'étude"],
                ["date_detection",  "String","Date YYYY-MM-DD"],
              ].map(([a,t,d])=>(
                <tr key={a} className="border-b border-gray-100 last:border-0">
                  <td className="p-2 font-mono text-emerald-700">{a}</td>
                  <td className="p-2 text-blue-600">{t}</td>
                  <td className="p-2 text-gray-500">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Conseil QGIS */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4
          text-xs text-blue-800 leading-relaxed">
          <strong>💡 QGIS :</strong> Fichier → Ouvrir → sélectionnez le .geojson.
          La couche s'affiche en EPSG:4326. Appliquez une symbologie graduée sur
          <code className="bg-blue-100 px-1 mx-1 rounded">superficie_ha</code>
          pour distinguer les types de points d'eau.
        </div>

      </div>
    </div>
  )
}
