"""
gee/metriques.py — Métriques de validation RÉELLES (matrice de confusion calculée sur GEE)

Référence indépendante : JRC Global Surface Water (Pekel et al. 2016, Landsat 30 m)
  - eau            : occurrence >= 50 %
  - non-eau facile : jamais en eau (occurrence = 0 ET max_extent = 0), loin de l'eau
  - non-eau DIFFICILE : jamais en eau MAIS à moins de ~300 m d'un plan d'eau
                        (berges, sols humides) -> c'est là que les faux positifs apparaissent
Les pixels d'eau saisonnière (occurrence 1-49 %) sont exclus (référence ambiguë).

Deux jeux de métriques :
  - "facile"    : eau vs non-eau facile  (mesure surtout le RAPPEL)
  - "difficile" : eau vs non-eau difficile (mesure aussi la PRÉCISION / sur-détection)

Limites (à écrire dans le mémoire) :
  - Échantillonnage stratifié équilibré : OA et précision calculées sur un échantillon
    équilibré, pas sur la prévalence réelle.
  - GSW (Landsat 30 m, 1984-2021) rate les petites mares sahéliennes.
  - Référence indicative, pas un relevé terrain.
"""
import ee

N_MIN = 30          # minimum de pixels par classe pour publier des métriques
RAYON_PROCHE = 10   # en pixels de 30 m  => ~300 m autour de l'eau JRC


def _calc(cm):
    (tn, fp), (fn, tp) = cm
    tn, fp, fn, tp = int(tn), int(fp), int(fn), int(tp)
    n = tn + fp + fn + tp
    if (tp + fn) < N_MIN or (tn + fp) < N_MIN:
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
    }


def evaluer_methode(carte_eau, zone_geom, n_par_classe=200, seed=7):
    gsw = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    occ = gsw.select("occurrence").unmask(0)
    mx  = gsw.select("max_extent").unmask(0)

    ref_eau = occ.gte(50)
    ref_non = occ.eq(0).And(mx.eq(0))
    proche  = mx.gt(0).focalMax(RAYON_PROCHE, "circle", "pixels")   # à ~300 m d'eau JRC
    dur     = ref_non.And(proche)                 # non-eau difficile
    facile  = ref_non.And(dur.Not())              # non-eau facile

    # classes : 0 = non-eau facile, 1 = eau, 2 = non-eau difficile
    ref = (ee.Image(0).where(ref_eau, 1).where(dur, 2)
           .updateMask(ref_eau.Or(facile).Or(dur))
           .rename("ref").toInt())
    pred = carte_eau.unmask(0).rename("pred").toInt()

    pts = ref.addBands(pred).stratifiedSample(
        numPoints=0, classBand="ref",
        classValues=[0, 1, 2],
        classPoints=[n_par_classe, n_par_classe, n_par_classe],
        region=zone_geom, scale=30, seed=seed,
        geometries=False, tileScale=4)

    # Jeu FACILE : eau (1) vs non-eau facile (0)
    p_fac = pts.filter(ee.Filter.inList("ref", [0, 1]))
    cm_fac = p_fac.errorMatrix("ref", "pred", [0, 1]).getInfo()

    # Jeu DIFFICILE : eau (1) vs non-eau difficile (2 -> 0)
    p_dur = (pts.filter(ee.Filter.inList("ref", [1, 2]))
             .map(lambda f: f.set("ref2", ee.Number(f.get("ref")).eq(1))))
    cm_dur = p_dur.errorMatrix("ref2", "pred", [0, 1]).getInfo()

    res = _calc(cm_fac)
    if res is None:
        print("  ⚠ Métriques non publiées : trop peu de pixels de référence (facile)")
        return None
    res["reference"] = "JRC Global Surface Water (occurrence ≥ 50 %)"
    res["echantillon"] = "équilibré (eau = non-eau)"
    res["difficile"] = _calc(cm_dur)   # None si trop peu de non-eau proches de l'eau
    return res