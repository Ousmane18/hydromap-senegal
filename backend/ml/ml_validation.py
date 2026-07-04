"""
ml/ml_validation.py
Validation du modèle Random Forest.
Métriques : Overall Accuracy · Kappa de Cohen · Précision · Rappel · F1-score
"""

import ee
from gee.gee_processor import FEATURES_RF, LABEL_RF, get_zone


def valider_random_forest(classifier: ee.Classifier,
                           image: ee.Image,
                           zone_nom: str,
                           split_test: float = 0.3) -> dict:
    """
    Validation hold-out 70/30.
    Entraînement sur 70% des points, test sur 30%.

    Returns:
        dict avec OA, Kappa, F1, matrice de confusion
    """
    zone = get_zone(zone_nom)

    # Échantillonnage global
    echantillon = (image.select(FEATURES_RF + [LABEL_RF])
                   .sample(region=zone, scale=20, numPixels=500, seed=99))

    # Split train / test
    echantillon = echantillon.randomColumn("random", seed=99)
    test_set    = echantillon.filter(ee.Filter.lt("random", split_test))

    # Classification du jeu de test
    test_classifie = test_set.classify(
        classifier.setOutputMode("CLASSIFICATION")
    )

    # Matrice de confusion GEE
    matrice = test_classifie.errorMatrix(LABEL_RF, "classification")

    oa    = matrice.accuracy().getInfo()
    kappa = matrice.kappa().getInfo()
    conf  = matrice.array().getInfo()

    tn, fp = conf[0][0], conf[0][1]
    fn, tp = conf[1][0], conf[1][1]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    rappel    = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1        = (2 * precision * rappel / (precision + rappel)
                 if (precision + rappel) > 0 else 0)

    resultats = {
        "overall_accuracy": round(oa * 100, 2),
        "kappa":            round(kappa, 4),
        "precision":        round(precision * 100, 2),
        "rappel":           round(rappel * 100, 2),
        "f1_score":         round(f1 * 100, 2),
        "matrice_confusion": {"TN": int(tn), "FP": int(fp),
                               "FN": int(fn), "TP": int(tp)},
    }

    print(f"\n📊 VALIDATION RANDOM FOREST")
    print(f"  Overall Accuracy : {resultats['overall_accuracy']}%")
    print(f"  Kappa            : {resultats['kappa']}")
    print(f"  Précision        : {resultats['precision']}%")
    print(f"  Rappel           : {resultats['rappel']}%")
    print(f"  F1-score         : {resultats['f1_score']}%")
    print(f"\n  Matrice de confusion :")
    print(f"               Prédit NON-EAU   Prédit EAU")
    print(f"  Réel NON-EAU       {tn:>6}          {fp:>6}")
    print(f"  Réel EAU           {fn:>6}          {tp:>6}")

    return resultats


def comparer_methodes(image: ee.Image, carte_rf: ee.Image,
                       carte_seuil: ee.Image, zone_nom: str) -> dict:
    """
    Compare Random Forest vs Seuillage sur des points de validation.
    Utile pour la section résultats/discussion du mémoire.
    """
    zone = get_zone(zone_nom)

    # Points de référence haute confiance
    masque_eau = image.select("MNDWI").gt(0.3).And(image.select("NDWI").gt(0.15))
    masque_sol = image.select("MNDWI").lt(-0.4)

    pts = (image.updateMask(masque_eau)
           .sample(region=zone, scale=20, numPixels=50, seed=77)
           .map(lambda f: f.set("ref", 1))
           .merge(image.updateMask(masque_sol)
                  .sample(region=zone, scale=20, numPixels=50, seed=77)
                  .map(lambda f: f.set("ref", 0))))

    def evaluer(carte, nom, bande):
        pts_class = carte.sampleRegions(collection=pts, scale=20, properties=["ref"])
        mat = pts_class.errorMatrix("ref", bande)
        return {
            "methode": nom,
            "overall_accuracy": round(mat.accuracy().getInfo() * 100, 2),
            "kappa":            round(mat.kappa().getInfo(), 4),
        }

    res_rf    = evaluer(carte_rf,    "Random Forest",        "eau_rf")
    res_seuil = evaluer(carte_seuil, "Seuillage NDWI/MNDWI", "eau_seuillage")

    print(f"\n📊 COMPARAISON DES MÉTHODES")
    print(f"  {res_rf['methode']:<28} OA={res_rf['overall_accuracy']}%  Kappa={res_rf['kappa']}")
    print(f"  {res_seuil['methode']:<28} OA={res_seuil['overall_accuracy']}%  Kappa={res_seuil['kappa']}")

    return {"random_forest": res_rf, "seuillage": res_seuil}