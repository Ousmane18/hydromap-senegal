"""
gee/gee_processor.py
═══════════════════════════════════════════════════════════
Pipeline complet de détection des points d'eau - HydroMap Sénégal
Données  : Sentinel-2 L2A (COPERNICUS/S2_SR_HARMONIZED)
Indices  : NDWI · MNDWI · AWEI_nsh · AWEI_sh · NDVI · NDBI
Méthodes : Seuillage classique + Random Forest (GEE smileRF)
Zone     : Zones semi-arides du Sénégal | Résolution : 20 m
═══════════════════════════════════════════════════════════
"""

import ee
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════
# 1. INITIALISATION GEE
# ══════════════════════════════════════════════

def initialiser_gee():
    """Initialise GEE en mode dev (token local) ou prod (compte de service)."""
    service_account = os.getenv("GEE_SERVICE_ACCOUNT", "")
    key_file        = os.getenv("GEE_KEY_FILE", "gee-key.json")
    project_id      = os.getenv("GEE_PROJECT_ID", "burnished-ray-498510-h2")

    try:
        if service_account and os.path.exists(key_file):
            credentials = ee.ServiceAccountCredentials(service_account, key_file)
            ee.Initialize(credentials, project=project_id)
            print("✓ GEE initialisé — compte de service")
        else:
            ee.Initialize(project=project_id)
            print("✓ GEE initialisé — token local")
    except Exception as e:
        raise RuntimeError(
            f"Impossible d'initialiser GEE : {e}\n"
            f"→ Lancez : earthengine authenticate --project={project_id}"
        )


# ══════════════════════════════════════════════
# 2. ZONES D'ÉTUDE
# ══════════════════════════════════════════════

ZONES = {
    "ferlo_nord":        {"geom": ee.Geometry.Rectangle([-15.5, 14.5, -13.5, 16.0]), "label": "Ferlo Nord"},
    "ferlo_sud":         {"geom": ee.Geometry.Rectangle([-14.5, 13.5, -12.5, 14.5]), "label": "Ferlo Sud"},
    "sine_saloum":       {"geom": ee.Geometry.Rectangle([-16.5, 13.5, -14.5, 14.5]), "label": "Sine-Saloum"},
    "bassin_arachidier": {"geom": ee.Geometry.Rectangle([-16.0, 14.0, -14.0, 15.0]), "label": "Bassin Arachidier"},
    "senegal_nord":      {"geom": ee.Geometry.Rectangle([-16.5, 15.0, -13.0, 16.5]), "label": "Sénégal Nord"},
}

def get_zone(nom: str) -> ee.Geometry:
    if nom not in ZONES:
        raise ValueError(f"Zone inconnue : '{nom}'. Choisir parmi : {list(ZONES.keys())}")
    return ZONES[nom]["geom"]


# ══════════════════════════════════════════════
# 3. PRÉTRAITEMENT SENTINEL-2
# ══════════════════════════════════════════════

def masquer_nuages_s2(image: ee.Image) -> ee.Image:
    """Masque nuages (bit10) et cirrus (bit11) via QA60. Normalise par 10000."""
    qa     = image.select("QA60")
    masque = (qa.bitwiseAnd(1 << 10).eq(0)
                .And(qa.bitwiseAnd(1 << 11).eq(0)))
    return (image.updateMask(masque)
                 .divide(10000)
                 .copyProperties(image, ["system:time_start"]))


def charger_collection_s2(zone_nom: str, date_debut: str,
                           date_fin: str, nuage_max: int = 20) -> ee.ImageCollection:
    """Charge et filtre la collection Sentinel-2 SR sur la zone et la période."""
    zone = get_zone(zone_nom)
    collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterBounds(zone)
                  .filterDate(date_debut, date_fin)
                  .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", nuage_max))
                  .map(masquer_nuages_s2))
    n = collection.size().getInfo()
    print(f"  → {n} images Sentinel-2 | {zone_nom} | {date_debut}→{date_fin}")
    if n == 0:
        raise ValueError("Aucune image disponible. Élargissez la période ou augmentez nuage_max.")
    return collection


# ══════════════════════════════════════════════
# 4. INDICES SPECTRAUX
# ══════════════════════════════════════════════

def calculer_tous_indices(image: ee.Image) -> ee.Image:
    """
    Calcule les 6 indices spectraux (features du Random Forest).

    NDWI    (McFeeters 1996) : (B3−B8)/(B3+B8)
    MNDWI   (Xu 2006)        : (B3−B11)/(B3+B11)
    AWEI_nsh(Feyisa 2014)    : 4(B3−B11) − (0.25·B8 + 2.75·B12)
    AWEI_sh (Feyisa 2014)    : B2+2.5·B3−1.5(B8+B11)−0.25·B12
    NDVI                     : (B8−B4)/(B8+B4)
    NDBI                     : (B11−B8)/(B11+B8)
    """
    B2  = image.select("B2")
    B3  = image.select("B3")
    B4  = image.select("B4")
    B8  = image.select("B8")
    B11 = image.select("B11")
    B12 = image.select("B12")

    ndwi     = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
    mndwi    = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
    awei_nsh = (B3.multiply(4).subtract(B11.multiply(0.25).add(B12.multiply(2.75)))).rename("AWEI_nsh")
    awei_sh  = (B2.add(B3.multiply(2.5)).subtract(B8.multiply(1.5).add(B11.multiply(0.25))).subtract(B12)).rename("AWEI_sh")
    ndvi     = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndbi     = image.normalizedDifference(["B11", "B8"]).rename("NDBI")

    return image.addBands([ndwi, mndwi, awei_nsh, awei_sh, ndvi, ndbi])


# ══════════════════════════════════════════════
# 5. SEUILLAGE CLASSIQUE
# ══════════════════════════════════════════════

def detection_par_seuillage(image: ee.Image,
                              seuil_ndwi: float = 0.0,
                              seuil_mndwi: float = 0.0) -> ee.Image:
    """
    Détection eau par double seuillage NDWI + MNDWI.
    Pixel = eau si NDWI > seuil OU MNDWI > seuil.
    Méthode de référence pour comparaison avec RF.
    """
    eau_ndwi  = image.select("NDWI").gt(seuil_ndwi)
    eau_mndwi = image.select("MNDWI").gt(seuil_mndwi)
    return eau_ndwi.Or(eau_mndwi).rename("eau_seuillage")


# ══════════════════════════════════════════════
# 6. RANDOM FOREST
# ══════════════════════════════════════════════

FEATURES_RF = [
    "NDWI", "MNDWI", "AWEI_nsh", "AWEI_sh",
    "NDVI", "NDBI",
    "B2", "B3", "B4", "B8", "B11", "B12"
]
LABEL_RF = "eau"


def generer_points_entrainement(image: ee.Image, zone_nom: str,
                                 n_points: int = 300) -> ee.FeatureCollection:
    """
    Génère des points d'entraînement automatiques par seuillage de confiance haute.
    EAU     : MNDWI > 0.2 ET NDWI > 0.1
    NON-EAU : MNDWI < -0.3 ET NDVI < 0.1
    ⚠ En production : remplacer par des points GPS terrain.
    """
    zone = get_zone(zone_nom)

    masque_eau     = image.select("MNDWI").gt(0.2).And(image.select("NDWI").gt(0.1))
    masque_non_eau = image.select("MNDWI").lt(-0.3).And(image.select("NDVI").lt(0.1))

    pts_eau = (image.updateMask(masque_eau)
               .sample(region=zone, scale=20, numPixels=n_points, seed=42, geometries=True)
               .map(lambda f: f.set(LABEL_RF, 1)))

    pts_non_eau = (image.updateMask(masque_non_eau)
                   .sample(region=zone, scale=20, numPixels=n_points, seed=42, geometries=True)
                   .map(lambda f: f.set(LABEL_RF, 0)))

    merged  = pts_eau.merge(pts_non_eau)
    n_total = merged.size().getInfo()
    print(f"  → {n_total} points d'entraînement (eau + non-eau)")
    return merged


def entrainer_random_forest(points_train: ee.FeatureCollection,
                             n_arbres: int = 100,
                             min_leaf: int = 5,
                             bag_fraction: float = 0.7) -> ee.Classifier:
    """
    Entraîne le Random Forest sur GEE.
    n_arbres=100, min_leaf=5, bag_fraction=0.7 → bons hyperparamètres par défaut.
    """
    classifier = (ee.Classifier.smileRandomForest(
        numberOfTrees=n_arbres,
        minLeafPopulation=min_leaf,
        bagFraction=bag_fraction,
        seed=42
    ).train(
        features=points_train,
        classProperty=LABEL_RF,
        inputProperties=FEATURES_RF
    ))
    print(f"  → RF entraîné : {n_arbres} arbres | {len(FEATURES_RF)} features")
    return classifier


def classifier_avec_rf(image: ee.Image, classifier: ee.Classifier) -> ee.Image:
    """Applique le RF → carte binaire eau (1) / non-eau (0)."""
    return image.select(FEATURES_RF).classify(classifier).rename("eau_rf")


def obtenir_importance_features(classifier: ee.Classifier) -> dict:
    """Retourne l'importance de chaque feature, triée par ordre décroissant."""
    try:
        raw = classifier.explain().get("importance").getInfo()
        return {k: round(v, 2) for k, v in sorted(raw.items(), key=lambda x: x[1], reverse=True)}
    except Exception as e:
        print(f"  ⚠ Importance non disponible : {e}")
        return {}


# ══════════════════════════════════════════════
# 7. COMBINAISON RF + SEUILLAGE
# ══════════════════════════════════════════════

def combiner_methodes(carte_rf: ee.Image, carte_seuil: ee.Image,
                       mode: str = "intersection") -> ee.Image:
    """
    union        → eau si RF OU seuillage  (maximise détection)
    intersection → eau si RF ET seuillage  (maximise précision)
    """
    if mode == "union":
        return carte_rf.Or(carte_seuil).rename("eau_combinee")
    return carte_rf.And(carte_seuil).rename("eau_combinee")


# ══════════════════════════════════════════════
# 8. VECTORISATION
# ══════════════════════════════════════════════

def vectoriser_points_eau(carte_eau: ee.Image, zone_nom: str,
                           surface_min_pixels: int = 3) -> ee.FeatureCollection:
    """
    Convertit la carte binaire en polygones vecteurs avec attributs enrichis.
    Filtre les objets < surface_min_pixels pour éliminer le bruit.
    """
    zone     = get_zone(zone_nom)
    vecteurs = (carte_eau.selfMask().reduceToVectors(
        geometry=zone, scale=20, geometryType="polygon",
        labelProperty="eau", maxPixels=1e10, bestEffort=True
    ))
    vecteurs_filtres = vecteurs.filter(ee.Filter.gte("count", surface_min_pixels))

    def enrichir(feature):
        sup_m2  = feature.area(maxError=1)
        sup_ha  = sup_m2.divide(10000)
        coords  = feature.centroid(maxError=1).geometry().coordinates()
        type_p  = ee.Algorithms.If(
            sup_ha.gt(50), "permanent",
            ee.Algorithms.If(sup_ha.gt(5), "temporaire", "secondaire")
        )
        return feature.set({
            "superficie_m2":   sup_m2,
            "superficie_ha":   sup_ha,
            "longitude":       coords.get(0),
            "latitude":        coords.get(1),
            "type_permanence": type_p,
            "zone":            zone_nom,
            "date_detection":  datetime.now().strftime("%Y-%m-%d"),
        })

    return vecteurs_filtres.map(enrichir)


# ══════════════════════════════════════════════
# 9. PIPELINE PRINCIPAL
# ══════════════════════════════════════════════

def pipeline_detection(zone_nom="ferlo_nord", date_debut="2023-07-01",
                        date_fin="2023-10-31", methode="random_forest",
                        n_arbres=100, n_points_train=300,
                        seuil_ndwi=0.0, seuil_mndwi=0.0, nuage_max=20) -> dict:
    """
    Pipeline complet : Sentinel-2 → Indices → RF/Seuillage → Vecteurs → Stats.
    methode : "random_forest" | "seuillage" | "les_deux"
    """
    print(f"\n{'═'*50}")
    print(f"  PIPELINE — {zone_nom.upper()} | {methode}")
    print(f"  {date_debut} → {date_fin}")
    print(f"{'═'*50}")

    # 1. Chargement
    print("\n[1/5] Chargement Sentinel-2...")
    collection = charger_collection_s2(zone_nom, date_debut, date_fin, nuage_max)
    mosaique   = collection.median()

    # 2. Indices
    print("[2/5] Calcul des indices spectraux...")
    image = calculer_tous_indices(mosaique)

    # 3. Classification
    print(f"[3/5] Classification ({methode})...")
    importance = {}
    carte_rf = carte_seuil = None

    if methode in ("random_forest", "les_deux"):
        pts_train  = generer_points_entrainement(image, zone_nom, n_points_train)
        classifier = entrainer_random_forest(pts_train, n_arbres)
        carte_rf   = classifier_avec_rf(image, classifier)
        importance = obtenir_importance_features(classifier)
        carte_finale = carte_rf

    if methode in ("seuillage", "les_deux"):
        carte_seuil  = detection_par_seuillage(image, seuil_ndwi, seuil_mndwi)
        carte_finale = (combiner_methodes(carte_rf, carte_seuil)
                        if methode == "les_deux" else carte_seuil)

    # 4. Vectorisation
    print("[4/5] Vectorisation...")
    points_eau = vectoriser_points_eau(carte_finale, zone_nom)
    n_points   = points_eau.size().getInfo()

    # 5. Statistiques
    print("[5/5] Statistiques...")
    geojson = points_eau.getInfo()
    n_perm  = points_eau.filter(ee.Filter.eq("type_permanence", "permanent")).size().getInfo()
    n_temp  = points_eau.filter(ee.Filter.eq("type_permanence", "temporaire")).size().getInfo()
    n_sec   = points_eau.filter(ee.Filter.eq("type_permanence", "secondaire")).size().getInfo()

    print(f"\n✅ {n_points} points détectés | {n_perm} perm. | {n_temp} temp. | {n_sec} sec.")

    return {
        "zone": zone_nom, "periode": f"{date_debut}/{date_fin}",
        "methode": methode, "n_points_detectes": n_points,
        "geojson": geojson, "importance_variables": importance,
        "statistiques": {
            "superficie_totale_ha":  round(points_eau.aggregate_sum("superficie_ha").getInfo() or 0, 2),
            "superficie_moyenne_ha": round(points_eau.aggregate_mean("superficie_ha").getInfo() or 0, 4),
            "superficie_max_ha":     round(points_eau.aggregate_max("superficie_ha").getInfo() or 0, 2),
            "n_permanents":  n_perm,
            "n_temporaires": n_temp,
            "n_secondaires": n_sec,
        }
    }


# ══════════════════════════════════════════════
# 10. ANALYSE TEMPORELLE
# ══════════════════════════════════════════════

def analyse_temporelle(zone_nom: str, annees: list,
                        methode: str = "random_forest") -> list:
    """
    Lance le pipeline sur hivernage + saison sèche pour chaque année.
    Permet de visualiser la dynamique inter-saisonnière des points d'eau.
    """
    resultats = []
    for annee in annees:
        for saison, debut, fin in [
            ("hivernage",   f"{annee}-07-01",   f"{annee}-10-31"),
            ("saison_seche",f"{annee+1}-01-01", f"{annee+1}-03-31"),
        ]:
            try:
                res = pipeline_detection(zone_nom=zone_nom, date_debut=debut,
                                         date_fin=fin, methode=methode)
                resultats.append({
                    "annee": annee, "saison": saison,
                    "n_points":     res["n_points_detectes"],
                    "superficie_ha":res["statistiques"]["superficie_totale_ha"],
                    "n_permanents": res["statistiques"]["n_permanents"],
                    "n_temporaires":res["statistiques"]["n_temporaires"],
                })
            except Exception as e:
                print(f"  ⚠ Ignoré ({saison} {annee}) : {e}")
    return resultats


# ══════════════════════════════════════════════
# TEST LOCAL
# ══════════════════════════════════════════════

if __name__ == "__main__":
    initialiser_gee()

    res = pipeline_detection(
        zone_nom="ferlo_nord",
        date_debut="2023-07-01",
        date_fin="2023-10-31",
        methode="les_deux",
        n_arbres=100,
    )

    # Affichage importance RF
    if res["importance_variables"]:
        print("\n📊 Importance des features RF :")
        for var, imp in res["importance_variables"].items():
            barre = "█" * int(imp / 4)
            print(f"  {var:<12} {barre:<25} {imp:.1f}%")

    # Export GeoJSON
    with open("test_ferlo_nord.geojson", "w", encoding="utf-8") as f:
        json.dump(res["geojson"], f, indent=2, ensure_ascii=False)
    print("\n✓ GeoJSON exporté → test_ferlo_nord.geojson")