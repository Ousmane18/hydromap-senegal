import time
import json
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from schemas import RequeteDetection, ReponseDetection
from gee.gee_processor import pipeline_detection

router = APIRouter(prefix="/api", tags=["Détection"])

# Cache simple en mémoire (clé → résultat JSON textuel)
_cache: dict = {}

def _cle_cache(req: RequeteDetection) -> str:
    """Génère une clé unique pour le cache selon les paramètres."""
    return (f"{req.zone}_{req.date_debut}_{req.date_fin}_"
            f"{req.methode}_{req.n_arbres}_{req.seuil_ndwi}_{req.seuil_mndwi}")

@router.post("/detection", response_model=ReponseDetection, summary="Lancer une détection")
async def lancer_detection(requete: RequeteDetection):
    """
    ## Détection automatique des points d'eau

    Lance le pipeline complet Sentinel-2 + indices spectraux + Random Forest
    sur la zone et la période sélectionnées.
    """
    cle = _cle_cache(requete)

    if cle in _cache:
        print(f"  → Cache hit : {cle[:40]}...")
        return Response(content=_cache[cle], media_type="application/json")

    t_debut = time.time()

    try:
        resultats = pipeline_detection(
            zone_nom=       requete.zone,
            date_debut=     requete.date_debut,
            date_fin=       requete.date_fin,
            methode=        requete.methode,
            n_arbres=       requete.n_arbres,
            n_points_train= requete.n_points_train,
            seuil_ndwi=     requete.seuil_ndwi,
            seuil_mndwi=    requete.seuil_mndwi,
            nuage_max=      requete.nuage_max,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("\n❌ CRASH DANS LE PIPELINE GEE :")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne du pipeline : {str(e)}"
        )

    resultats["duree_secondes"] = round(time.time() - t_debut, 1)

    try:
        json_texte = json.dumps(resultats, default=str, ensure_ascii=False)

# cache = objet Python
        _cache[cle] = resultats

        print(f"  → Résultat mis en cache ({len(_cache)} entrées)")
        return Response(content=json_texte, media_type="application/json")
    except Exception as e:
        print("\n❌ CRASH SÉRIALISATION :")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur sérialisation : {str(e)}")


@router.delete("/cache", summary="Vider le cache")
async def vider_cache():
    """Vide le cache des résultats GEE."""
    n = len(_cache)
    _cache.clear()
    return {"message": f"Cache vidé ({n} entrées supprimées)"}


# ─── LA LIGNE MANQUANTE ICI ───
def get_cache() -> dict:
    """Expose le cache aux autres routes (notamment pour l'export GeoJSON)."""
    return _cache