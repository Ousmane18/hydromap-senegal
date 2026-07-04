"""
routes/export.py
Endpoints d'export : GeoJSON et CSV téléchargeables.
GET /api/export/geojson/{zone}/{date_debut}/{date_fin}
GET /api/export/csv/{zone}/{date_debut}/{date_fin}
"""

import json
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/export", tags=["Export"])

# Référence vers le cache de la route détection
_cache_ref: dict = {}


def set_cache_ref(cache: dict):
    """Lie ce module au cache de la route détection."""
    global _cache_ref
    _cache_ref = cache


def _trouver_dans_cache(zone: str, date_debut: str, date_fin: str) -> dict | None:
    """Cherche un résultat dans le cache correspondant à zone + dates."""
    for cle, valeur in _cache_ref.items():
        if cle.startswith(f"{zone}_{date_debut}_{date_fin}_"):
            return valeur
    return None


@router.get("/geojson/{zone}/{date_debut}/{date_fin}",
            summary="Télécharger en GeoJSON")
async def exporter_geojson(zone: str, date_debut: str, date_fin: str):
    """
    ## Export GeoJSON

    Télécharge les points d'eau détectés au format GeoJSON (EPSG:4326).
    Compatible avec QGIS, ArcGIS, Mapbox, GeoPandas.

    Le fichier contient une FeatureCollection avec pour chaque point d'eau :
    superficie_m2, superficie_ha, latitude, longitude, type_permanence, zone, date_detection.
    """
    resultats = _trouver_dans_cache(zone, date_debut, date_fin)
    if not resultats:
        raise HTTPException(
            status_code=404,
            detail="Aucun résultat trouvé. Lancez d'abord une détection via POST /api/detection."
        )

    geojson_str = json.dumps(resultats["geojson"], indent=2, ensure_ascii=False)
    nom_fichier = f"hydromap_{zone}_{date_debut}_{date_fin}.geojson"

    return StreamingResponse(
        io.BytesIO(geojson_str.encode("utf-8")),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"}
    )


@router.get("/csv/{zone}/{date_debut}/{date_fin}",
            summary="Télécharger en CSV")
async def exporter_csv(zone: str, date_debut: str, date_fin: str):
    """
    ## Export CSV

    Télécharge les points d'eau au format CSV tabulaire.
    Compatible avec Excel, Python/Pandas, R.

    Colonnes : id, latitude, longitude, superficie_m2, superficie_ha,
               type_permanence, zone, date_detection.
    """
    resultats = _trouver_dans_cache(zone, date_debut, date_fin)
    if not resultats:
        raise HTTPException(
            status_code=404,
            detail="Aucun résultat trouvé. Lancez d'abord une détection via POST /api/detection."
        )

    features = resultats["geojson"].get("features", [])

    # Construction du CSV
    entete  = "id,latitude,longitude,superficie_m2,superficie_ha,type_permanence,zone,date_detection"
    lignes  = [entete]

    for i, f in enumerate(features, start=1):
        p = f.get("properties", {})
        ligne = ",".join([
            str(i),
            str(round(p.get("latitude", ""), 6)),
            str(round(p.get("longitude", ""), 6)),
            str(round(p.get("superficie_m2", 0), 1)),
            str(round(p.get("superficie_ha", 0), 4)),
            str(p.get("type_permanence", "")),
            str(p.get("zone", "")),
            str(p.get("date_detection", "")),
        ])
        lignes.append(ligne)

    csv_str     = "\n".join(lignes)
    nom_fichier = f"hydromap_{zone}_{date_debut}_{date_fin}.csv"

    return StreamingResponse(
        io.BytesIO(csv_str.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nom_fichier}"}
    )


@router.get("/shapefile/{zone}/{date_debut}/{date_fin}",
            summary="Télécharger en Shapefile (ZIP)")
async def exporter_shapefile(zone: str, date_debut: str, date_fin: str):
    """
    ## Export Shapefile

    Génère un fichier ZIP contenant le shapefile (.shp, .dbf, .shx, .prj)
    compatible avec QGIS et ArcGIS.
    """
    resultats = _trouver_dans_cache(zone, date_debut, date_fin)
    if not resultats:
        raise HTTPException(status_code=404, detail="Aucun résultat. Lancez une détection d'abord.")

    try:
        import geopandas as gpd
        import zipfile
        import tempfile
        import os

        # GeoJSON → GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(
            resultats["geojson"]["features"],
            crs="EPSG:4326"
        )

        # Export shapefile dans dossier temporaire
        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, f"hydromap_{zone}")
            gdf.to_file(shp_path, driver="ESRI Shapefile")

            # Zipper les fichiers
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for fichier in os.listdir(tmpdir):
                    zf.write(os.path.join(tmpdir, fichier), fichier)

            zip_buffer.seek(0)

        nom_fichier = f"hydromap_{zone}_{date_debut}_{date_fin}_shp.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={nom_fichier}"}
        )

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="GeoPandas non installé. Utilisez l'export GeoJSON à la place."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))