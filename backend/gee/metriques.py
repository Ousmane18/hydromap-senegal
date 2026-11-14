"""
gee/metriques.py — Métriques de validation RÉELLES (matrice de confusion calculée sur GEE)

Référence indépendante : JRC Global Surface Water (Pekel et al. 2016, Landsat 30 m)
  - eau     : occurrence >= 50 %
  - non-eau : occurrence = 0 ET max_extent = 0 (jamais vu en eau)
Les pixels intermédiaires (eau saisonnière, 1-49 %) sont exclus : référence ambiguë.

Limites (à écrire dans le mémoire) :
  - Échantillonnage stratifié équilibré (n eau = n non-eau) : l'OA et la précision
    sont donc calculées sur un échantillon équilibré, pas sur la prévalence réelle.
  - GSW (30 m) rate les petites mares sahéliennes : le rappel est pessimiste et
    peu de pixels eau de référence existent dans le Ferlo.
  - Pour le Random Forest, la référence est indépendante des seuils d'entraînement
    (pas de circularité), mais reste une référence Landsat, pas un relevé terrain.
"""
import ee

N_MIN_EAU = 30   # minimum de pixels eau de référence pour publier des métriques


def evaluer_methode(carte_eau, zone_geom, n_par_classe=200, seed=7):
    gsw = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    occ = gsw.select("occurrence").unmask(0)
    mx  = gsw.select("max_extent").unmask(0)

    ref_eau = occ.gte(50)
    ref_non = occ.eq(0).And(mx.eq(0))
    ref = (ee.Image(0).where(ref_eau, 1)
           .updateMask(ref_eau.Or(ref_non))
           .rename("ref").toInt())
    pred = carte_eau.unmask(0).rename("pred").toInt()

    pts = ref.addBands(pred).stratifiedSample(
        numPoints=0, classBand="ref",
        classValues=[0, 1], classPoints=[n_par_classe, n_par_classe],
        region=zone_geom, scale=30, seed=seed,
        geometries=False, tileScale=4)

    cm = pts.errorMatrix("ref", "pred", [0, 1]).getInfo()   # lignes = réel, colonnes = prédit
    (tn, fp), (fn, tp) = cm
    tn, fp, fn, tp = int(tn), int(fp), int(fn), int(tp)
    n_eau_ref = tp + fn
    n = tn + fp + fn + tp

    if n_eau_ref < N_MIN_EAU or (tn + fp) < N_MIN_EAU:
        print(f"  ⚠ Métriques non publiées : trop peu de pixels de référence "
              f"(eau={n_eau_ref}, non-eau={tn+fp})")
        return None

    oa   = (tp + tn) / n
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn)
    spec = tn / (tn + fp)
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    pe   = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (n * n)
    kappa = (oa - pe) / (1 - pe) if pe < 1 else 0.0

    return {
        "oa": round(oa * 100, 1), "kappa": round(kappa, 3),
        "precision": round(prec * 100, 1), "rappel": round(rec * 100, 1),
        "specificite": round(spec * 100, 1), "f1": round(f1 * 100, 1),
        "matrice": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "n_validation": n,
        "reference": "JRC Global Surface Water (occurrence ≥ 50 %)",
        "echantillon": "équilibré (eau = non-eau)",
    }
