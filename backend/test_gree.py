"""
test_gee.py
Script de test rapide de la connexion Google Earth Engine.
Exécuter : python test_gee.py
"""

import ee
import os
from dotenv import load_dotenv

load_dotenv()

def tester_connexion():
    print("=" * 50)
    print("  TEST CONNEXION GOOGLE EARTH ENGINE")
    print("=" * 50)

    # 1. Initialisation
    try:
        project_id = os.getenv("GEE_PROJECT_ID", "burnished-ray-498510-h2")
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
        print("\n✓ GEE connecté avec succès")
    except Exception as e:
        print(f"\n✗ Erreur connexion : {e}")
        print("  → Lancez d'abord : earthengine authenticate")
        return

    # 2. Test collection Sentinel-2 sur le Ferlo
    try:
        zone_ferlo = ee.Geometry.Rectangle([-15.5, 14.5, -13.5, 16.0])
        collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterBounds(zone_ferlo)
                      .filterDate("2023-07-01", "2023-10-31")
                      .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20)))
        n_images = collection.size().getInfo()
        print(f"✓ Sentinel-2 : {n_images} images disponibles (Ferlo, hivernage 2023)")
    except Exception as e:
        print(f"✗ Erreur Sentinel-2 : {e}")
        return

    # 3. Test calcul NDWI
    try:
        image = collection.median().divide(10000)
        ndwi  = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
        stats = ndwi.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=zone_ferlo,
            scale=100, maxPixels=1e8
        )
        valeur = stats.get("NDWI").getInfo()
        print(f"✓ NDWI calculé : moyenne = {valeur:.4f}")
    except Exception as e:
        print(f"✗ Erreur NDWI : {e}")
        return

    # 4. Test Random Forest
    try:
        pts = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([-14.5, 15.0]), {"eau": 1}),
            ee.Feature(ee.Geometry.Point([-14.0, 15.5]), {"eau": 0}),
            ee.Feature(ee.Geometry.Point([-14.2, 15.2]), {"eau": 1}),
            ee.Feature(ee.Geometry.Point([-14.8, 15.8]), {"eau": 0}),
        ])
        classifier = (ee.Classifier.smileRandomForest(10)
                      .train(features=pts, classProperty="eau",
                             inputProperties=["NDWI"]))
        print("✓ Random Forest GEE : initialisable")
    except Exception as e:
        print(f"✗ Erreur Random Forest : {e}")
        return

    print("\n" + "=" * 50)
    print("  TOUT EST OK — Passez à l'Étape 3 ✅")
    print("=" * 50)


if __name__ == "__main__":
    tester_connexion()