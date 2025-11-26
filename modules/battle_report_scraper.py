"""
Battle Report Scraper Module
Módulo para automatizar la captura de asistencia en reportes de batalla.
Detecta héroes, capitanes prohibidos y genera reporte de participantes.

Tracker core (persistencia por héroe + gametag)
----------------------------------------------
Implementa la persistencia de instancias por héroe + gametag.
Evita marcar un héroe como "ya procesado" solo por coincidencia de nombre:
se requiere que el gametag haya sido capturado para bloquear un nuevo click.
Las detecciones sin gametag (UNKNOWN) no bloquean y se fusionan con la entrada
hero+gametag al momento de capturar el gametag real.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple
import time


@dataclass
class SeenCard:
    """Representa una card detectada en la cuadrícula."""

    hero_name: str
    gametag: Optional[str]
    last_seen: float
    y_center: int
    processed: bool = False


class InstanceTracker:
    """
    Persiste instancias por (héroe + gametag), no solo por héroe.

    Reglas clave:
    - Una detección sin gametag se registra como hero+UNKNOWN y *no* bloquea
      otros intentos del mismo héroe.
    - Cuando se captura el gametag, la entrada hero+UNKNOWN se fusiona en la
      clave hero+gametag y se marca como procesada.
    - Se evita re-clickear el mismo gametag ya procesado; nuevas detecciones
      del mismo héroe con gametag distinto siguen siendo válidas.
    """

    UNKNOWN = None

    def __init__(self) -> None:
        # Llave: (hero_key, gametag_key)
        self.seen: Dict[Tuple[str, Optional[str]], SeenCard] = {}
        self.gametags: Set[str] = set()
        self.max_y_processed: int = 0
        self.min_y_seen: int = 99999

    def _hero_key(self, hero_name: str) -> str:
        return hero_name.strip().lower()

    def _gametag_key(self, gametag: Optional[str]) -> Optional[str]:
        return gametag.strip().lower() if gametag else self.UNKNOWN

    def _key(self, hero_name: str, gametag: Optional[str]) -> Tuple[str, Optional[str]]:
        return (self._hero_key(hero_name), self._gametag_key(gametag))

    # --- Registro de detecciones ---
    def add_detection(self, hero_name: str, y_center: int) -> None:
        """Registra una card vista sin gametag (hero+UNKNOWN).

        - Actualiza el "min_y_seen" para saber desde dónde empezamos a ver cards.
        - Si la card ya existía, solo refresca la última vez y su Y.
        """

        now = time.time()
        self.min_y_seen = min(self.min_y_seen, y_center)

        key = self._key(hero_name, None)
        card = self.seen.get(key)
        if not card:
            self.seen[key] = SeenCard(hero_name=hero_name, gametag=None, last_seen=now, y_center=y_center)
        else:
            card.last_seen = now
            card.y_center = y_center

    # --- Lógica de skip ---
    def should_process(self, hero_name: str, y_center: int) -> bool:
        """
        Devuelve True solo si debemos abrir la card.

        - Solo bloquea cuando ya hay *un gametag procesado* para ese héroe en
          la misma zona Y (misma card).
        - Las entradas hero+UNKNOWN nunca bloquean; sirven solo para mergear
          al capturar el gametag.
        """

        hero_key = self._hero_key(hero_name)
        for (stored_hero, stored_tag), card in self.seen.items():
            if stored_hero != hero_key:
                continue

            # Bloquea únicamente la misma card (mismo héroe + gametag ya
            # capturado) en un rango cercano de Y. Si el héroe aparece de
            # nuevo más lejos en la cuadrícula, permitimos procesarlo para
            # capturar un gametag distinto.
            if (
                card.processed
                and stored_tag is not self.UNKNOWN
                and abs(y_center - card.y_center) < 160
            ):
                return False

        return True

    # --- Confirmación de procesado ---
    def mark_processed(self, hero_name: str, y_center: int, gametag: Optional[str]) -> None:
        """
        Marca la card como procesada y persiste por hero+gametag.

        - Si existía hero+UNKNOWN, se fusiona con la nueva clave hero+gametag.
        - El gametag se normaliza en minúsculas para deduplicar.
        - Guarda el Y máximo procesado para ayudar al scroll.
        """

        now = time.time()
        hero_key = self._hero_key(hero_name)
        normalized_tag = gametag.strip() if gametag else None

        # Eliminar/recuperar la entrada hero+UNKNOWN para este héroe
        unknown_key = (hero_key, self.UNKNOWN)
        unknown_card = self.seen.pop(unknown_key, None)

        # Guardar/actualizar la entrada definitiva hero+gametag
        key = self._key(hero_name, normalized_tag)
        card = self.seen.get(key)

        if not card:
            base = unknown_card or SeenCard(hero_name=hero_name, gametag=None, last_seen=now, y_center=y_center)
            card = SeenCard(
                hero_name=base.hero_name,
                gametag=normalized_tag,
                last_seen=now,
                y_center=y_center,
                processed=True,
            )
            self.seen[key] = card
        else:
            card.gametag = normalized_tag
            card.last_seen = now
            card.y_center = y_center
            card.processed = True

        self.max_y_processed = max(self.max_y_processed, y_center)

        if normalized_tag:
            self.gametags.add(normalized_tag.lower())

    def needs_scroll(self) -> bool:
        """Indica si debemos forzar scroll agresivo.

        Se activa cuando ya procesamos por debajo del primer Y visto, lo que
        sugiere que ya no hay cards nuevas en pantalla actual.
        """

        return self.max_y_processed > self.min_y_seen + 250


class ImprovedInstanceTracker(InstanceTracker):
    """
    Alias para compatibilidad hacia atrás.

    El repositorio previo exponía ``ImprovedInstanceTracker``; este alias
    permite resolver conflictos de merge manteniendo la API esperada, pero la
    lógica principal vive en ``InstanceTracker``.
    """

    pass


# Punto de entrada seguro para que "python modules/battle_report_scraper.py"
# no falle aunque el módulo completo no esté implementado aún.
if __name__ == "__main__":
    print(
        "Este módulo contiene la lógica de persistencia por héroe+gametag. "
        "Integra InstanceTracker con tu flujo de detección/OCR para evitar "
        "falsos 'ya procesado' cuando solo hay coincidencia de héroe."
    )
