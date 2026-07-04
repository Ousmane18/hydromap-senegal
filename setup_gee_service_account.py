"""
setup_gee_service_account.py
════════════════════════════════════════════════════════════
Script à exécuter UNE SEULE FOIS en local pour créer
le compte de service GEE nécessaire au déploiement Render.

Prérequis :
  - Google Cloud CLI installé (gcloud)
  - Compte GEE actif avec projet enregistré
  - Python + earthengine-api installé

Usage :
  python setup_gee_service_account.py
════════════════════════════════════════════════════════════
"""

import subprocess
import os
import json

PROJECT_ID = os.getenv("GEE_PROJECT_ID", "burnished-ray-498510-h2")

if not PROJECT_ID:
    PROJECT_ID = input("Entrez votre GEE_PROJECT_ID : ").strip()

SA_NAME    = "hydromap-gee-sa"
SA_EMAIL   = f"{SA_NAME}@{PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE   = "backend/gee-key.json"

print(f"\n{'═'*55}")
print(f"  Création du compte de service GEE")
print(f"  Projet : {PROJECT_ID}")
print(f"  Compte : {SA_EMAIL}")
print(f"{'═'*55}\n")

# 1. Créer le compte de service
print("[1/4] Création du compte de service...")
subprocess.run([
    "gcloud", "iam", "service-accounts", "create", SA_NAME,
    "--project", PROJECT_ID,
    "--display-name", "HydroMap GEE Service Account",
], check=True)

# 2. Générer la clé JSON
print("[2/4] Génération de la clé JSON...")
subprocess.run([
    "gcloud", "iam", "service-accounts", "keys", "create", KEY_FILE,
    "--iam-account", SA_EMAIL,
    "--project", PROJECT_ID,
], check=True)

# 3. Enregistrer le compte dans GEE
print("[3/4] Enregistrement dans Google Earth Engine...")
print(f"\n  → Allez sur : https://code.earthengine.google.com/register")
print(f"  → Enregistrez le compte de service : {SA_EMAIL}")
print(f"  → Rôle : 'Earth Engine Resource Viewer'\n")
input("  Appuyez sur ENTRÉE une fois le compte enregistré dans GEE...")

# 4. Test
print("[4/4] Test de connexion...")
import ee
try:
    credentials = ee.ServiceAccountCredentials(SA_EMAIL, KEY_FILE)
    ee.Initialize(credentials, project=PROJECT_ID)
    zone_test = ee.Geometry.Rectangle([-15.5, 14.5, -13.5, 16.0])
    n = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
         .filterBounds(zone_test)
         .filterDate("2023-08-01","2023-09-30")
         .size().getInfo())
    print(f"\n✅ Connexion OK ! {n} images Sentinel-2 disponibles")
    print(f"\n   Fichier clé créé : {KEY_FILE}")
    print(f"   → Ce fichier doit être uploadé comme 'Secret File' sur Render")
except Exception as e:
    print(f"\n✗ Erreur : {e}")
    print("  → Vérifiez que le compte est bien enregistré sur GEE")

print(f"\n{'═'*55}")
print("  Variables à configurer sur Render :")
print(f"  GEE_PROJECT_ID      = {PROJECT_ID}")
print(f"  GEE_SERVICE_ACCOUNT = {SA_EMAIL}")
print(f"  GEE_KEY_FILE        = gee-key.json")
print(f"{'═'*55}\n")
