from fastapi import APIRouter, HTTPException
from gee.gee_processor import ZONES

router = APIRouter(prefix="/api", tags=["Zones"])

def extraire_metadonnees_zone(nom: str, infos: dict) -> dict:
    """
    Extrait les coordonnées de la bounding box [ouest, sud, est, nord]
    et calcule son centre géographique nativement en Python.
    """
    coords = infos.get("coords")
    
    if not coords or len(coords) != 4:
        raise HTTPException(
            status_code=500,
            detail=f"La zone '{nom}' ne contient pas une bounding box valide [ouest, sud, est, nord] dans ZONES."
        )

    # Extraction des coordonnées du rectangle : [ouest, sud, est, nord]
    ouest, sud, est, nord = coords

    # Calcul simple et direct du centre du rectangle
    centre_lon = (ouest + est) / 2
    centre_lat = (sud + nord) / 2

    # Reconstruction de la structure de polygones fermés GeoJSON pour le Front-end (ex: Leaflet / Mapbox)
    # Un polygone rectangulaire standard possède 5 points (le premier et le dernier sont identiques)
    bbox_polygon = [
        [ouest, nord],  # Coin supérieur gauche
        [est, nord],    # Coin supérieur droit
        [est, sud],     # Coin inférieur droit
        [ouest, sud],   # Coin inférieur gauche
        [ouest, nord]   # Fermeture du polygone
    ]

    return {
        "nom": nom,
        "label": infos.get("label", nom.replace("_", " ").title()),
        "bbox": bbox_polygon,          # Structure de polygone attendue par les cartes web
        "bbox_brute": coords,          # [ouest, sud, est, nord] original
        "centre_lat": round(centre_lat, 4),
        "centre_lon": round(centre_lon, 4),
    }


@router.get("/zones", summary="Liste des zones d'étude")
async def liste_zones():
    """
    ## Zones d'étude disponibles

    Retourne les zones semi-arides du Sénégal disponibles pour l'analyse,
    avec leurs polygones d'affichage (bbox) et coordonnées de centre.
    """
    zones_info = {}
    for nom, infos in ZONES.items():
        zones_info[nom] = extraire_metadonnees_zone(nom, infos)
    return zones_info


@router.get("/zones/{zone_nom}", summary="Détails d'une zone")
async def detail_zone(zone_nom: str):
    """Retourne les informations détaillées d'une zone spécifique."""
    if zone_nom not in ZONES:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_nom}' inconnue. Zones disponibles : {list(ZONES.keys())}"
        )
    return extraire_metadonnees_zone(zone_nom, ZONES[zone_nom])