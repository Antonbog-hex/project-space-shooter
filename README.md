# Space shooter

Een 2D ruimteschietspel gebouwd met Pygame, waarbij je een ruimteschip bestuurt in een  gegenereerde wereld met realistische zwaartekracht, vijandelijke AI, planeten, etc.
https://github.com/Antonbog-hex/project-space-shooter 

---
**Auteurs**

- Anton Bogaerts
- Boris Peleman
---

## Vereisten

- Python 3.10+
- Pygame (`pip install pygame`)

---

## Starten

**Windows:**
```bash
python main.py
```
**MacOS:**
```bash
python3 main.py
```

---

## Besturing

| Toets | Actie |
|---|---|
| `W` / `↑` | Versnellen |
| `A` / `←` | Linksom draaien |
| `D` / `→` | Rechtsom draaien |
| `Spatie` | Schieten |
| `Enter` | Start / herstart het spel |
| `Escape` | Pauzeer / stop het spel |

---

## Gameplay

Je bestuurt een ruimteschip in een eindeloos uitbreidende wereld. Planeten oefenen echte zwaartekracht uit op je schip en op vijanden. Vijanden spawnen automatisch en zoeken je actief op.

**Overleef zo lang mogelijk en verzamel punten door vijanden te vernietigen.**

Elke 30 frames dat je overleeft krijg je automatisch 1 punt. Vijanden die je raakt geven extra punten bij vernietiging. De moeilijkheid schaalt mee met je score.

---

## Wapens

Je begint met het basiswapen. Door vijanden te verslaan kun je wapens oppikken die ze laten vallen.

| Wapen | Schade | Vuursnelheid | Beschrijving |
|---|---|---|---|
| Basic | 1 | Snel | Standaard rood projectiel |
| Sniper | 3 | Langzaam | Hoge snelheid, groot bereik |
| Shotgun | 1 | Middel | 8 kogels per schot |
| Rocket | 2 + explosie | Zeer langzaam | Zelfgeleid, explodeert bij inslag |

---

## Vijanden

| Type | HP | Score | Gedrag |
|---|---|---|---|
| SimpleEnemy | 3 | 30 | Standaard aanvaller, laat Basic-wapen vallen |
| SniperEnemy | 2 | 50 | Houdt afstand, hoog bereik, laat Sniper vallen |
| SuicideEnemy | 2 | 60 | Vliegt recht op je af en explodeert |
| ShotgunEnemy | 4 | 80 | Robuust, vuurt meerdere kogels af, laat Shotgun vallen |
| RocketEnemy | 3 | 140 | Vuurt zelfgeleide raketten af |
| HealingEnemy | 3 | 100 | Heelt nabijgelegen bondgenoten, laat Heal-item vallen |

Alle vijanden hebben een geheugen: als ze je eenmaal zien, onthouden ze je voor een bepaald aantal frames. Ze gebruiken baanvoorspelling om te mikken.

---

## Wereld

De wereld is opgedeeld in **chunks**. Wanneer je een nieuw gebied betreedt, wordt er automatisch een planetenstelsel en een groep vijanden gegenereerd.

### Planetenstelsels (prefabs)

| Naam | Beschrijving |
|---|---|
| Binary | Twee planeten die om hun gemeenschappelijk zwaartepunt draaien |
| Moon system | Een centrale planeet met 1–4 manen |
| Asteroid field | 6–12 kleine rotsblokken verspreid over een gebied |
| Black hole | Een zwart gat omringd door puin in een baan |
| Ringed planet | Grote planeet met een ring van kleine maantjes |
| Satellite network | Planeet met 3–6 satellieten in een baan |

Planeten trekken je schip aan via de zwaartekrachtswet (F = G·m₁·m₂/r²). Zwarte gaten doden je schip direct bij aanraking.

---

## Architectuur

Het project is opgesplitst in meerdere bestanden (zie `main.py`). De klassenhiërarchie werkt via meervoudige overerving:

```
BasicObject
├── VisualObject          — heeft een zichtbare afbeelding
├── MovingObject          — beweegt via kinematica
├── GravityObject         — berekent zwaartekrachten
├── RotatingObject        — kan draaien
└── Hitbox
    ├── CircularHitbox    — ronde botsingsdetectie
    └── LineHitbox        — lijnvormige botsingsdetectie

PhysicsObject (GravityObject + MovingObject + CircularHitbox)
├── Planet
├── Spaceship (+ RotatingObject + VisualObject)
│   ├── Player
│   └── BaseEnemy
│       ├── SimpleEnemy
│       ├── SniperEnemy
│       ├── SuicideEnemy
│       ├── ShotgunEnemy
│       ├── RocketEnemy
│       └── HealingEnemy
└── BaseBullet (+ VisualObject)
    ├── SniperBullet
    ├── ShotgunPellet
    └── RocketBullet (+ RotatingObject)
```
> Dit is een vereenvoudige weergave

### Belangrijke systemen

**ChunkManager** — beheert welke chunks actief zijn op basis van de spelerspositie. Objecten buiten de actieve zone worden tijdelijk opgeslagen en later herladen.

**EnemyManager** — spawnt vijanden op veilige afstand van de speler. De moeilijkheid (spawnsnelheid, agressiviteit) schaalt met de score.

**Camera** — volgt de speler vloeiend en zoomt automatisch uit om de voorspelde baan zichtbaar te houden.

**ActiveObjects** — aangepaste lijstklasse die `pre_update()` en `update()` aanroept op elk object, en objecten veilig toevoegt of verwijdert tussen frames.

---

## Debugopties

In de broncode (onderaan het bestand) staan verschillende flags die je kunt inschakelen:

| flag | Effect |
|---|---|
| `debug` | Toont snelheids- en versnellingsvectoren |
| `debug_enemy` | Toont gezichtslijn, hitbox en gewenste koers van vijanden |
| `debug_freecam` | Camera los van de speler, bestuurbaar met WASD, Q,E voor zoom (handig om world gen te inspecteren) |
| `debug_bullets` | Toont hitboxen van kogels |
| `debug_disable_world_gen` | Genereert geen nieuwe chunks |
| `debug_disable_enemy_spawn` | Spawnt geen vijanden |

---

## Grafische bestanden

Het spel verwacht de volgende mappenstructuur:

```
graphics/
├── background/
│   └── Starfield_05-1024x1024.png
├── planets/
│   ├── Ice/, Tropical/, Desert/, Ocean/, Alpine/, Moons/
│   ├── BlackHole/0.png
│   └── Satellite/0.png
├── enemies/
│   └── enemy_1.png t/m 7.png
└── player/
    └── player.png
```