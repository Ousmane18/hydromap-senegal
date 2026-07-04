"""
schemas.py
Modèles Pydantic pour la validation des requêtes et réponses de l'API HydroMap.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import date


# ══════════════════════════════════════════════
# REQUÊTES (entrées)
# ══════════════════════════════════════════════

class RequeteDetection(BaseModel):
    """Paramètres pour lancer une détection de points d'eau."""

    zone: Literal[
        "ferlo_nord", "ferlo_sud", "sine_saloum",
        "bassin_arachidier", "senegal_nord"
    ] = Field(
        default="ferlo_nord",
        description="Zone géographique d'analyse"
    )

    date_debut: str = Field(
        default="2023-07-01",
        description="Date de début de la période (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )

    date_fin: str = Field(
        default="2023-10-31",
        description="Date de fin de la période (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )

    methode: Literal["random_forest", "seuillage", "les_deux"] = Field(
        default="random_forest",
        description="Méthode de classification"
    )

    n_arbres: int = Field(
        default=100, ge=10, le=500,
        description="Nombre d'arbres du Random Forest"
    )

    n_points_train: int = Field(
        default=300, ge=50, le=1000,
        description="Nombre de points d'entraînement par classe"
    )

    seuil_ndwi: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Seuil NDWI (utilisé si méthode=seuillage ou les_deux)"
    )

    seuil_mndwi: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Seuil MNDWI (utilisé si méthode=seuillage ou les_deux)"
    )

    nuage_max: int = Field(
        default=20, ge=0, le=100,
        description="Pourcentage maximum de nuages par image Sentinel-2"
    )

    @field_validator("date_fin")
    @classmethod
    def date_fin_apres_debut(cls, v, info):
        if "date_debut" in info.data and v <= info.data["date_debut"]:
            raise ValueError("date_fin doit être postérieure à date_debut")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "zone": "ferlo_nord",
                "date_debut": "2023-07-01",
                "date_fin": "2023-10-31",
                "methode": "random_forest",
                "n_arbres": 100,
                "n_points_train": 300,
                "seuil_ndwi": 0.0,
                "seuil_mndwi": 0.0,
                "nuage_max": 20
            }
        }
    }


class RequeteTemporelle(BaseModel):
    """Paramètres pour l'analyse temporelle multi-années."""

    zone: Literal[
        "ferlo_nord", "ferlo_sud", "sine_saloum",
        "bassin_arachidier", "senegal_nord"
    ] = Field(default="ferlo_nord")

    annees: list[int] = Field(
        default=[2021, 2022, 2023],
        description="Liste des années à analyser"
    )

    methode: Literal["random_forest", "seuillage"] = Field(
        default="random_forest"
    )

    @field_validator("annees")
    @classmethod
    def valider_annees(cls, v):
        for annee in v:
            if annee < 2017 or annee > 2025:
                raise ValueError(f"Année {annee} hors plage (2017-2025). "
                                  "Sentinel-2 SR disponible depuis 2017.")
        if len(v) > 5:
            raise ValueError("Maximum 5 années par requête.")
        return sorted(set(v))


# ══════════════════════════════════════════════
# RÉPONSES (sorties)
# ══════════════════════════════════════════════

class StatistiquesZone(BaseModel):
    """Statistiques agrégées sur les points d'eau détectés."""
    superficie_totale_ha:  float
    superficie_moyenne_ha: float
    superficie_max_ha:     float
    n_permanents:          int
    n_temporaires:         int
    n_secondaires:         int


class ReponseDetection(BaseModel):
    """Réponse complète d'une détection de points d'eau."""
    zone:                 str
    periode:              str
    methode:              str
    n_points_detectes:    int
    statistiques:         StatistiquesZone
    importance_variables: dict
    geojson:              dict   # FeatureCollection GeoJSON
    duree_secondes:       Optional[float] = None


class ResumeTemporel(BaseModel):
    """Résumé d'une période pour l'analyse temporelle."""
    annee:         int
    saison:        str
    n_points:      int
    superficie_ha: float
    n_permanents:  int
    n_temporaires: int


class ReponseTemporelle(BaseModel):
    """Réponse de l'analyse temporelle multi-années."""
    zone:    str
    annees:  list[int]
    methode: str
    resume:  list[ResumeTemporel]


class InfoZone(BaseModel):
    """Informations sur une zone d'étude."""
    nom:         str
    label:       str
    bbox:        list[list[float]]
    centre_lat:  float
    centre_lon:  float


class SanteAPI(BaseModel):
    """État de santé de l'API."""
    status:       str
    gee_connecte: bool
    cache_taille: int
    version:      str