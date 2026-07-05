"""
main.py — HydroMap Sénégal v11
Cache double : détection + temporel (par période individuelle)
"""

import os, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

# ── État global ──────────────────────────────
_gee_ok           = False
_cache_detection: dict = {}   # clé = params complets
_cache_temporel:  dict = {}   # clé = zone_annee_saison_methode (par période)


# ── Lifespan ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _gee_ok
    print("\n" + "="*50)
    print("  HYDROMAP v11 — Démarrage")
    print("="*50)
    try:
        import ee
        import json
        
        # 1. Vérification si on est sur Render avec un Compte de Service
        gee_creds = os.getenv("GEE_SERVICE_ACCOUNT_CREDENTIALS")
        pid = os.getenv("GEE_PROJECT_ID", "")
        
        if gee_creds:
            print("Authentification GEE via Compte de Service...")
            creds_dict = json.loads(gee_creds)
            # Utilisation des identifiants du compte de service
            credentials = ee.ServiceAccountCredentials(creds_dict["client_email"], key_data=gee_creds)
            ee.Initialize(credentials=credentials, project=pid if pid else None)
        else:
            # 2. Authentification locale classique
            print("Authentification GEE locale...")
            ee.Initialize(project=pid) if pid else ee.Initialize()
            
        _gee_ok = True
        print("✓ GEE connecté avec succès !")
    except Exception as e:
        print(f"⚠ GEE non connecté : {e}")
    print("✓ API prête : http://localhost:8000/api/docs")
    print("="*50 + "\n")
    yield
    print("Arrêt de l'API...")


# ── App ──────────────────────────────────────
app = FastAPI(
    title="HydroMap Sénégal API",
    version="11.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:3000","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schémas ──────────────────────────────────
class RequeteDetection(BaseModel):
    zone:           Literal["ferlo_nord","ferlo_sud","sine_saloum","bassin_arachidier","senegal_nord"] = "ferlo_nord"
    date_debut:     str   = "2023-07-01"
    date_fin:       str   = "2023-10-31"
    methode:        Literal["awei","random_forest","seuillage","les_deux"] = "awei"
    n_arbres:       int   = Field(default=100, ge=10, le=300)
    n_points_train: int   = Field(default=100, ge=20, le=300)
    seuil_ndwi:     float = Field(default=0.0, ge=-1.0, le=1.0)
    seuil_mndwi:    float = Field(default=0.0, ge=-1.0, le=1.0)
    nuage_max:      int   = Field(default=50, ge=5, le=90)
    surface_min_m2: int   = Field(default=2000, ge=400, le=50000)


class RequeteTemporelle(BaseModel):
    zone:    str       = "ferlo_nord"
    annees:  list[int] = [2021, 2022, 2023]
    methode: str       = "awei"


# ── Routes de base ────────────────────────────
@app.get("/")
def racine():
    return {"app":"HydroMap Sénégal","version":"11.0.0","docs":"/api/docs"}


@app.get("/api/health")
def sante():
    return {
        "status":               "ok",
        "gee_connecte":         _gee_ok,
        "cache_detection":      len(_cache_detection),
        "cache_temporel":       len(_cache_temporel),
    }


@app.get("/api/zones")
def zones():
    return {
        "ferlo_nord":        {"label":"Ferlo Nord",        "centre":[15.25,-14.5]},
        "ferlo_sud":         {"label":"Ferlo Sud",          "centre":[14.0,-13.5]},
        "sine_saloum":       {"label":"Sine-Saloum",        "centre":[14.0,-15.5]},
        "bassin_arachidier": {"label":"Bassin Arachidier",  "centre":[14.5,-15.0]},
        "senegal_nord":      {"label":"Sénégal Nord",       "centre":[15.75,-14.75]},
    }


# ── Détection ─────────────────────────────────
@app.post("/api/detection")
async def detection(req: RequeteDetection):
    if not _gee_ok:
        raise HTTPException(503, "GEE non connecté. Lancez 'earthengine authenticate'.")

    cle = (f"{req.zone}_{req.date_debut}_{req.date_fin}_"
           f"{req.methode}_{req.n_arbres}_{req.surface_min_m2}_{req.nuage_max}")

    if cle in _cache_detection:
        print(f"  → Cache hit détection")
        return _cache_detection[cle]

    try:
        from gee.gee_processor import pipeline_detection
        res = pipeline_detection(
            zone_nom       = req.zone,
            date_debut     = req.date_debut,
            date_fin       = req.date_fin,
            methode        = req.methode,
            n_arbres       = req.n_arbres,
            n_points_train = req.n_points_train,
            seuil_ndwi     = req.seuil_ndwi,
            seuil_mndwi    = req.seuil_mndwi,
            nuage_max      = req.nuage_max,
            surface_min_m2 = req.surface_min_m2,
        )
        _cache_detection[cle] = res
        return res
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Erreur pipeline : {e}")


# ── Analyse temporelle OPTIMISÉE ──────────────
@app.post("/api/temporel")
async def temporel(req: RequeteTemporelle):
    """
    Cache par période individuelle :
      - "ferlo_nord_2021_hivernage_awei" mis en cache séparément
      - Relancer avec les mêmes années = instantané
      - Ajouter une année = seule cette année est recalculée
    """
    if not _gee_ok:
        raise HTTPException(503, "GEE non connecté.")

    resultats = []

    for annee in sorted(set(req.annees)):
        for saison, debut, fin in [
            ("hivernage",    f"{annee}-07-01",   f"{annee}-10-31"),
            ("saison_seche", f"{annee+1}-01-01", f"{annee+1}-03-31"),
        ]:
            cle = f"{req.zone}_{annee}_{saison}_{req.methode}"

            # Cache hit → résultat instantané
            if cle in _cache_temporel:
                print(f"  → Cache : {cle}")
                resultats.append(_cache_temporel[cle])
                continue

            # Calcul GEE
            try:
                from gee.gee_processor import pipeline_detection
                t = time.time()
                res = pipeline_detection(
                    zone_nom=req.zone,
                    date_debut=debut,
                    date_fin=fin,
                    methode=req.methode,
                    nuage_max=50,
                    surface_min_m2=2000,
                )
                point = {
                    "annee":        annee,
                    "saison":       saison,
                    "n_points":     res["n_points_detectes"],
                    "superficie_ha":res["statistiques"]["superficie_totale_ha"],
                    "n_permanents": res["statistiques"]["n_permanents"],
                    "n_temporaires":res["statistiques"]["n_temporaires"],
                }
                _cache_temporel[cle] = point
                resultats.append(point)
                print(f"  ✓ {saison} {annee} → {res['n_points_detectes']} pts ({time.time()-t:.1f}s)")

            except Exception as e:
                print(f"  ⚠ {saison} {annee} : {e}")
                resultats.append({
                    "annee":annee, "saison":saison,
                    "n_points":0, "superficie_ha":0.0,
                    "n_permanents":0, "n_temporaires":0,
                })

    return {"zone":req.zone, "annees":req.annees,
            "methode":req.methode, "resume":resultats}


# ── Export ────────────────────────────────────
@app.get("/api/export/geojson/{zone}/{date_debut}/{date_fin}")
async def export_geojson(zone:str, date_debut:str, date_fin:str):
    import io, json
    from fastapi.responses import StreamingResponse
    res = next((v for k,v in _cache_detection.items()
                if k.startswith(f"{zone}_{date_debut}_{date_fin}_")), None)
    if not res:
        raise HTTPException(404, "Lancez d'abord une détection.")
    contenu = json.dumps(res["geojson"], indent=2, ensure_ascii=False)
    return StreamingResponse(
        io.BytesIO(contenu.encode()),
        media_type="application/geo+json",
        headers={"Content-Disposition":f"attachment; filename=hydromap_{zone}_{date_debut}.geojson"}
    )


@app.get("/api/export/csv/{zone}/{date_debut}/{date_fin}")
async def export_csv(zone:str, date_debut:str, date_fin:str):
    import io
    from fastapi.responses import StreamingResponse
    res = next((v for k,v in _cache_detection.items()
                if k.startswith(f"{zone}_{date_debut}_{date_fin}_")), None)
    if not res:
        raise HTTPException(404, "Lancez d'abord une détection.")
    features = res["geojson"].get("features", [])
    head = "id,latitude,longitude,superficie_m2,superficie_ha,type_permanence,zone,date"
    rows = [",".join([
        str(i+1),
        str(round(f["properties"].get("latitude",0),6)),
        str(round(f["properties"].get("longitude",0),6)),
        str(round(f["properties"].get("superficie_m2",0),1)),
        str(round(f["properties"].get("superficie_ha",0),4)),
        str(f["properties"].get("type_permanence","")),
        str(f["properties"].get("zone","")),
        str(f["properties"].get("date_detection","")),
    ]) for i,f in enumerate(features)]
    return StreamingResponse(
        io.BytesIO("\n".join([head]+rows).encode()),
        media_type="text/csv",
        headers={"Content-Disposition":f"attachment; filename=hydromap_{zone}_{date_debut}.csv"}
    )


# ── Cache management ──────────────────────────
@app.delete("/api/cache")
def vider_cache():
    n1, n2 = len(_cache_detection), len(_cache_temporel)
    _cache_detection.clear()
    _cache_temporel.clear()
    return {"message": f"Caches vidés ({n1} détection + {n2} temporel)"}


@app.delete("/api/cache/temporel")
def vider_cache_temporel():
    n = len(_cache_temporel)
    _cache_temporel.clear()
    return {"message": f"Cache temporel vidé ({n} périodes)"}
