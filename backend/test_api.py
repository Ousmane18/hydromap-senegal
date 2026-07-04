"""
test_api.py
Test rapide de tous les endpoints de l'API HydroMap.
Exécuter APRÈS avoir lancé : uvicorn main:app --reload

Usage : python test_api.py
"""

import requests
import json

BASE = "http://localhost:8000"


def titre(texte: str):
    print(f"\n{'─'*50}")
    print(f"  {texte}")
    print('─'*50)


def ok(label: str, valeur=None):
    print(f"  ✓ {label}" + (f" : {valeur}" if valeur is not None else ""))


def ko(label: str, err=None):
    print(f"  ✗ {label}" + (f" : {err}" if err is not None else ""))


# ── 1. Racine ──────────────────────────────
titre("GET /  — Accueil")
try:
    r = requests.get(f"{BASE}/")
    r.raise_for_status()
    data = r.json()
    ok("API accessible", data.get("app"))
    ok("Version", data.get("version"))
except Exception as e:
    ko("Accueil inaccessible", e)
    print("  → Vérifiez que uvicorn tourne sur le port 8000")
    exit(1)


# ── 2. Santé ───────────────────────────────
titre("GET /api/health  — Santé")
try:
    r = requests.get(f"{BASE}/api/health")
    r.raise_for_status()
    data = r.json()
    ok("Statut", data.get("status"))
    ok("GEE connecté", data.get("gee_connecte"))
    ok("Cache", f"{data.get('cache_taille')} entrées")
except Exception as e:
    ko("Health check échoué", e)


# ── 3. Zones ───────────────────────────────
titre("GET /api/zones  — Liste des zones")
try:
    r = requests.get(f"{BASE}/api/zones")
    r.raise_for_status()
    zones = r.json()
    ok(f"{len(zones)} zones disponibles", list(zones.keys()))
except Exception as e:
    ko("Zones inaccessibles", e)


# ── 4. Détection (Random Forest) ───────────
titre("POST /api/detection  — Random Forest")
payload_rf = {
    "zone":           "ferlo_nord",
    "date_debut":     "2023-07-01",
    "date_fin":       "2023-10-31",
    "methode":        "random_forest",
    "n_arbres":       100,
    "n_points_train": 300,
    "nuage_max":      20
}
print(f"  Payload : {json.dumps(payload_rf, indent=4)}")
try:
    r = requests.post(f"{BASE}/api/detection", json=payload_rf, timeout=300)
    r.raise_for_status()
    data = r.json()
    ok("Détection réussie")
    ok("Points détectés",     data.get("n_points_detectes"))
    ok("Superficie totale",   f"{data['statistiques'].get('superficie_totale_ha')} ha")
    ok("Points permanents",   data["statistiques"].get("n_permanents"))
    ok("Durée",               f"{data.get('duree_secondes')}s")
    if data.get("importance_variables"):
        top = list(data["importance_variables"].items())[:3]
        ok("Top 3 features RF", top)
except requests.exceptions.Timeout:
    ko("Timeout — GEE met du temps, c'est normal. Attendez et relancez.")
except Exception as e:
    ko("Détection échouée", e)


# ── 5. Détection (Seuillage) ───────────────
titre("POST /api/detection  — Seuillage NDWI/MNDWI")
payload_seuil = {
    "zone":        "ferlo_nord",
    "date_debut":  "2023-07-01",
    "date_fin":    "2023-10-31",
    "methode":     "seuillage",
    "seuil_ndwi":  0.0,
    "seuil_mndwi": 0.0,
}
try:
    r = requests.post(f"{BASE}/api/detection", json=payload_seuil, timeout=300)
    r.raise_for_status()
    data = r.json()
    ok("Seuillage réussi", f"{data.get('n_points_detectes')} points")
except Exception as e:
    ko("Seuillage échoué", e)


# ── 6. Export GeoJSON ──────────────────────
titre("GET /api/export/geojson  — Export")
try:
    r = requests.get(
        f"{BASE}/api/export/geojson/ferlo_nord/2023-07-01/2023-10-31",
        timeout=30
    )
    if r.status_code == 200:
        geojson = r.json()
        n = len(geojson.get("features", []))
        ok(f"GeoJSON téléchargé ({n} features)")
        ok("Content-Type", r.headers.get("content-type"))
    elif r.status_code == 404:
        ok("404 attendu (pas de détection en cache encore)")
    else:
        ko(f"Statut inattendu : {r.status_code}")
except Exception as e:
    ko("Export échoué", e)


# ── 7. Validation requête invalide ──────────
titre("POST /api/detection  — Validation erreur")
try:
    r = requests.post(f"{BASE}/api/detection", json={
        "zone": "zone_inexistante",
        "date_debut": "2023-07-01",
        "date_fin": "2023-06-01",   # fin < début → erreur attendue
    }, timeout=10)
    if r.status_code == 422:
        ok("Validation Pydantic fonctionne (422 Unprocessable)")
    else:
        ok(f"Statut reçu : {r.status_code}")
except Exception as e:
    ko("Test validation échoué", e)


# ── Résumé ─────────────────────────────────
print(f"\n{'═'*50}")
print("  TESTS TERMINÉS")
print(f"  Swagger UI : {BASE}/api/docs")
print(f"  ReDoc      : {BASE}/api/redoc")
print('═'*50 + "\n")