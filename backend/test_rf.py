"""
test_rf.py — Diagnostic : pourquoi le Random Forest bascule sur l'AWEI ?

Usage (depuis le dossier backend, venv activé) :
    python test_rf.py sine_saloum 2023-08-01 2023-09-30

Il affiche :
  1. Le nombre d'images et les valeurs des bandes sur la zone d'entraînement (buffer 30 km)
  2. Pour chaque niveau de seuils : pixels eau / non-eau disponibles ET réellement échantillonnés
"""
import sys
import ee
from gee.gee_processor import (
    initialiser_gee, charger_s2, calculer_indices,
    get_zone_train, NIVEAUX,
)

zone  = sys.argv[1] if len(sys.argv) > 1 else "sine_saloum"
debut = sys.argv[2] if len(sys.argv) > 2 else "2023-08-01"
fin   = sys.argv[3] if len(sys.argv) > 3 else "2023-09-30"

initialiser_gee()
print(f"\n=== Diagnostic RF : {zone} | {debut} -> {fin} ===")

col = charger_s2(zone, debut, fin, 50)
img = calculer_indices(col.median())
zt  = get_zone_train(zone, 30)

# ── 1. La mosaïque contient-elle des données sur la zone d'entraînement ? ──
bandes = ["B3", "B8", "B11", "NDWI", "MNDWI", "NDVI", "AWEI_nsh"]
red = (ee.Reducer.min().combine(ee.Reducer.mean(), sharedInputs=True)
       .combine(ee.Reducer.max(), sharedInputs=True)
       .combine(ee.Reducer.count(), sharedInputs=True))
st = img.select(bandes).reduceRegion(red, zt, 100, maxPixels=1e9).getInfo()
print("\n[1] Valeurs sur la zone d'entraînement (échelle 100 m) :")
for b in bandes:
    print(f"   {b:9s} min={st.get(b+'_min')}  moy={st.get(b+'_mean')}  "
          f"max={st.get(b+'_max')}  n={st.get(b+'_count')}")
if not st.get("B3_count"):
    print("\n>>> PROBLÈME : la mosaïque est VIDE sur la zone d'entraînement "
          "(tous les pixels masqués). Cause probable : masque nuages / période.")

# ── 2. Pixels disponibles et réellement échantillonnés par niveau ──
print("\n[2] Par niveau (compte à 100 m | échantillon réel à 30 m, 100 demandés) :")
for niv in NIVEAUX:
    ligne = f"   {niv['label']:28s}"
    for nom in ("eau", "sol"):
        m = niv[nom](img)
        n = (img.select("B3").updateMask(m)
             .reduceRegion(ee.Reducer.count(), zt, 100, maxPixels=1e9)
             .get("B3").getInfo())
        s = (img.updateMask(m)
             .sample(region=zt, scale=30, numPixels=100, seed=42, geometries=True)
             .size().getInfo())
        ligne += f" {nom}: {n} px / {s} éch. |"
    print(ligne)

print("\nLecture : si 'px' est grand mais 'éch.' vaut 0 -> problème de sample().")
print("          si 'px' vaut 0 pour l'eau à tous les niveaux -> pas d'eau détectable.")
print("          si [1] est vide -> problème de mosaïque (nuages / dates).")