# 🃏 Wizard GUI – Punkte-Tracker

Ein professioneller, objektorientierter Punkte-Tracker für das Kartenspiel **Wizard**.

---

## Starten

```bash
cd wizard_gui
python main.py
```

**Abhängigkeiten:**
```bash
pip install PyQt6 matplotlib numpy
```

---

## Architektur

```
wizard_gui/
├── main.py               # Einstiegspunkt
├── game_control.py       # Datenmodell (Model)
├── save_manager.py       # JSON-Persistenz
├── style.py              # Zentrales Design-System
└── views/
    ├── main_window.py    # Haupt-Fenster (Controller)
    ├── setup_view.py     # Spieler-Setup-Bildschirm
    ├── game_view.py      # Spielbildschirm mit Plot
    └── dialogs.py        # Alle Dialog-Klassen
```

### Klassen-Übersicht

| Klasse | Datei | Verantwortung |
|---|---|---|
| `RoundResult` | game_control.py | Runden-Eingabe (angesagt / gemacht) + Punkte-Delta |
| `Player` | game_control.py | Spieler-Zustand (Name, Punkteverlauf, Runden-Historie) |
| `GameControl` | game_control.py | Zentrales Spielmodell, Undo, Serialisierung |
| `RoundEvents` | game_control.py | Ereignisse nach einer Runde (für Animationen) |
| `SaveManager` | save_manager.py | Speichern/Laden als JSON, Plot-Export |
| `MainWindow` | views/main_window.py | Fenster, State-Übergänge, Celebrations |
| `SetupView` | views/setup_view.py | Spieler hinzufügen, gespeicherte Spiele laden |
| `GameView` | views/game_view.py | Spielbildschirm, Punkte-Eingabe, Matplotlib-Plot |
| `PlayerCard` | views/game_view.py | Widget pro Spieler (Eingabe + Anzeige) |
| `MplCanvas` | views/game_view.py | Matplotlib in Qt eingebettet |
| `CelebrationOverlay` | views/dialogs.py | Animiertes Overlay für besondere Momente |
| `WarningDialog` | views/dialogs.py | Bestätigungs-Dialog |
| `SaveGameDialog` | views/dialogs.py | Dialog zum Benennen und Speichern |
| `LoadGameDialog` | views/dialogs.py | Dialog zum Auswählen gespeicherter Spiele |

---

## Features

### ✅ Implementiert
- **Zwei Spielzustände:** Setup-Bildschirm → Spielbildschirm
- **Spieler-Chips:** Spieler interaktiv hinzufügen/entfernen
- **Spinboxen** statt freier Texteingabe (verhindert ungültige Eingaben)
- **Undo:** Letzte Runde rückgängig machen (mit Bestätigung)
- **Celebrations:** Animiertes Overlay bei:
  - Neuer Anführer 👑
  - Meisterschuss ≥ 50 Punkte 🎯
  - 3× perfekte Runden in Folge 🔥
- **Plot-Export:** Als PNG, JPEG oder SVG speichern
- **Spielstand speichern:** JSON mit Metadaten
- **Spielstand laden:** Liste aller gespeicherten Spiele mit Details
- **Dark-Theme:** Konsistentes Midnight-Navy/Gold-Design
- **Anführer-Anzeige:** Hervorhebung in der Spieler-Karte + Plot-Annotation

### Speicherformat (JSON)
```json
{
  "schema_version": "1.1",
  "meta": {
    "name": "Spieleabend_Freitag",
    "saved_at": "2025-04-12T20:15:30"
  },
  "game": {
    "round_number": 5,
    "players": [
      {
        "name": "Alice",
        "rounds": [
          { "said": 2, "achieved": 2 },
          { "said": 1, "achieved": 0 }
        ]
      }
    ]
  }
}
```

Gespeichert unter: `~/.wizard_gui/games/`

---

## Erweiterungsideen
- Statistik-Ansicht (Siegrate, Durchschnitt pro Spieler)
- Mehrsprachigkeit (DE/EN)
- Anpassbare Celebration-Schwellwerte
- Kartenanzahl pro Runde konfigurierbar
- CSV-Export der Punkte-Tabelle
