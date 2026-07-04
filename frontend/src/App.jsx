import { useState } from "react"
import Sidebar, { CONFIG_DEFAUT } from "./components/Sidebar"
import Topbar        from "./components/Topbar"
import MapPage       from "./pages/MapPage"
import AnalysePage   from "./pages/AnalysePage"
import TemporelPage  from "./pages/TemporelPage"
import ExportPage    from "./pages/ExportPage"
import { useDetection } from "./hooks/useDetection"

export default function App() {
  const [page,   setPage]   = useState("carte")
  const [zone,   setZone]   = useState("ferlo_nord")
  const [config, setConfig] = useState(CONFIG_DEFAUT)

  const { resultats, loading, erreur, msg, detecter, reset } = useDetection()

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar
        page={page}     setPage={setPage}
        zone={zone}     setZone={setZone}
        config={config} setConfig={setConfig}
        loading={loading} erreur={erreur}
        onDetect={() => detecter({ zone, ...config })}
        onReset={reset}
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar page={page} zone={zone} resultats={resultats} />
        <main className="flex-1 overflow-hidden">
          { page === "carte"    && <MapPage    zone={zone} resultats={resultats} loading={loading} msg={msg} /> }
          { page === "analyse"  && <AnalysePage resultats={resultats} /> }
          { page === "temporel" && <TemporelPage zone={zone} /> }
          { page === "export"   && <ExportPage resultats={resultats} zone={zone} config={config} /> }
        </main>
      </div>
    </div>
  )
}
