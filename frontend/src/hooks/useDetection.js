/**
 * hooks/useDetection.js
 * Gère l'état complet de la détection : chargement, erreur, progression, résultats.
 */
import { useState, useCallback } from "react"
import { lancerDetection } from "../utils/api"

const MESSAGES = [
  "Chargement des images Sentinel-2…",
  "Masquage des nuages (QA60)…",
  "Calcul NDWI · MNDWI · AWEI · NDVI · NDBI…",
  "Génération des points d'entraînement…",
  "Entraînement du Random Forest…",
  "Vectorisation des points d'eau…",
  "Calcul des statistiques…",
]

export function useDetection() {
  const [resultats,  setResultats]  = useState(null)
  const [loading,    setLoading]    = useState(false)
  const [erreur,     setErreur]     = useState(null)
  const [msg,        setMsg]        = useState("")

  const detecter = useCallback(async (params) => {
    setLoading(true); setErreur(null); setResultats(null)
    let idx = 0
    setMsg(MESSAGES[0])
    const timer = setInterval(() => {
      idx = Math.min(idx + 1, MESSAGES.length - 1)
      setMsg(MESSAGES[idx])
    }, 7000)
    try {
      const res = await lancerDetection(params)
      setResultats(res)
    } catch (e) {
      setErreur(e.message)
    } finally {
      clearInterval(timer); setLoading(false); setMsg("")
    }
  }, [])

  const reset = useCallback(() => {
    setResultats(null); setErreur(null); setMsg("")
  }, [])

  return { resultats, loading, erreur, msg, detecter, reset }
}
