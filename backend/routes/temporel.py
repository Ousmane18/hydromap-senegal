"""
routes/temporel.py
Endpoint : POST /api/temporel
Analyse la dynamique temporelle des points d'eau sur plusieurs années.
"""

from fastapi import APIRouter, HTTPException
from schemas import RequeteTemporelle, ReponseTemporelle
from gee.gee_processor import analyse_temporelle

router = APIRouter(prefix="/api", tags=["Analyse temporelle"])


@router.post("/temporel", response_model=ReponseTemporelle, summary="Analyse temporelle")
async def lancer_analyse_temporelle(requete: RequeteTemporelle):
    """
    ## Analyse de la dynamique temporelle des points d'eau

    Compare la présence et la superficie des points d'eau entre
    **hivernage** (juillet–octobre) et **saison sèche** (janvier–mars)
    sur plusieurs années consécutives.

    Très utile pour le mémoire : visualise l'impact de la pluviométrie
    sur la disponibilité en eau dans les zones semi-arides.

    ### Retour
    Liste de résultats par période (annee + saison) avec nombre de points
    et superficie totale en hectares.
    """
    try:
        resultats_bruts = analyse_temporelle(
            zone_nom=requete.zone,
            annees=requete.annees,
            methode=requete.methode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    resume = [
        {
            "annee":         r["annee"],
            "saison":        r["saison"],
            "n_points":      r["n_points"],
            "superficie_ha": r["superficie_ha"],
            "n_permanents":  r.get("n_permanents", 0),
            "n_temporaires": r.get("n_temporaires", 0),
        }
        for r in resultats_bruts
    ]

    return {
        "zone":    requete.zone,
        "annees":  requete.annees,
        "methode": requete.methode,
        "resume":  resume,
    }