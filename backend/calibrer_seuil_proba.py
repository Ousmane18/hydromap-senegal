"""
calibrer_seuil_proba.py — choisir le seuil de probabilité du Random Forest.

Usage (dossier backend, venv activé) :
    python calibrer_seuil_proba.py sine_saloum 2023-08-01 2023-09-30

Pour chaque seuil, affiche la superficie d'eau détectée et les métriques vs JRC GSW
(jeu FACILE : surtout le rappel ; jeu DIFFICILE : révèle les faux positifs).
Les lignes AWEI et Seuillage servent de repères sur la MÊME zone et la MÊME période.
"""
import sys
import ee
from gee.gee_processor import (
    initialiser_gee, charger_s2, calculer_indices, generer_points_train,
    entrainer_rf, get_zone, detection_awei, detection_seuillage, FEATURES_RF,
)
from gee.metriques import evaluer_methode

zone  = sys.argv[1] if len(sys.argv) > 1 else "sine_saloum"
debut = sys.argv[2] if len(sys.argv) > 2 else "2023-08-01"
fin   = sys.argv[3] if len(sys.argv) > 3 else "2023-09-30"
SEUILS = [0.5, 0.7, 0.8, 0.9, 0.95]

initialiser_gee()
print(f"\n=== Calibration seuil RF : {zone} | {debut} -> {fin} ===")
img = calculer_indices(charger_s2(zone, debut, fin, 50).median())
zg  = get_zone(zone)

pts   = generer_points_train(img, zone)
clf   = entrainer_rf(pts, 100)
proba = img.select(FEATURES_RF).classify(clf.setOutputMode("PROBABILITY"))


def surface_ha(carte, nom):
    r = (carte.multiply(ee.Image.pixelArea()).divide(10000)
         .reduceRegion(ee.Reducer.sum(), zg, 100, maxPixels=1e10, bestEffort=True)
         .getInfo())
    return list(r.values())[0] if r else None


def ligne(nom, carte):
    ha = surface_ha(carte, nom)
    m  = evaluer_methode(carte, zg)
    if m is None:
        return f"{nom:<14}{ha or 0:>12,.0f}   (métriques non calculables)"
    d = m.get("difficile")
    fp_dur = d["matrice"]["fp"] if d else None
    prec_dur = f"{d['precision']}%" if d else "n/a"
    return (f"{nom:<14}{ha or 0:>12,.0f}   {m['rappel']:>6}%  {m['kappa']:>6}   "
            f"{prec_dur:>9}  {str(fp_dur):>8}")


print(f"\n{'Méthode':<14}{'Eau (ha)':>12}   {'Rappel':>7}  {'Kappa':>6}   "
      f"{'Préc.diff':>9}  {'FP diff.':>8}")
print("-" * 66)
print(ligne("AWEI", detection_awei(img)))
print(ligne("Seuillage", detection_seuillage(img)))
for s in SEUILS:
    print(ligne(f"RF p>={s}", proba.gte(s).rename("eau_rf")))

print("\nChoix : cherchez le seuil où 'Préc.diff' monte (moins de faux positifs) sans que "
      "'Rappel' s'effondre,\net où 'Eau (ha)' devient comparable à l'AWEI / seuillage.")
print("Calibrez sur UNE zone, puis vérifiez sur une AUTRE zone avant de publier.")