---
name: PartFocus
description: Übe-Tracks pro Stimme aus MuseScore-Partituren, als Stimmenhefte auf dem Kartontisch
colors:
  kartontisch: "#E7DFC9"
  papierfeld: "#F4EFE0"
  kopfband: "#7A1F2B"
  kopfband-aufgehellt: "#8F2D3A"
  kopfband-schrift: "#FFFFFF"
  kopfband-gedaempft: "#E2C4C4"
  falzlinie: "#CFC5AC"
  pappkante: "#B8AD92"
  griffelgrau: "#756B58"
  tinte: "#26211A"
  bleistift: "#5A5142"
  ochsenblut: "#7A1F2B"
  ochsenblut-hover: "#641722"
  ochsenblut-hauch: "#EFD9D0"
  auf-ochsenblut: "#FFFFFF"
  warnocker: "#7A5608"
  siegelrot: "#9B2C22"
  titelschild: "#F4EFE0"
  titelschild-schrift: "#26211A"
  einband-tinte: "#26211A"
  einband-ochsenblut: "#7A1F2B"
  einband-tannengruen: "#2F6B4F"
  einband-verlagsblau: "#1F4E79"
  einband-indigo: "#463A73"
  einband-ocker: "#94671C"
  kartontisch-dunkel: "#231F1A"
  papierfeld-dunkel: "#2E2922"
  kopfband-dunkel: "#5E1722"
  kopfband-aufgehellt-dunkel: "#74232F"
  kopfband-schrift-dunkel: "#FFFFFF"
  kopfband-gedaempft-dunkel: "#D9BDBD"
  falzlinie-dunkel: "#453E33"
  pappkante-dunkel: "#5C5345"
  griffelgrau-dunkel: "#83796A"
  tinte-dunkel: "#EFE8D8"
  bleistift-dunkel: "#B5AB99"
  ochsenblut-dunkel: "#D06A74"
  ochsenblut-hover-dunkel: "#DC858D"
  ochsenblut-hauch-dunkel: "#4A2A2C"
  auf-ochsenblut-dunkel: "#231F1A"
  warnocker-dunkel: "#E0B861"
  siegelrot-dunkel: "#E08376"
  titelschild-dunkel: "#F4EFE0"
  titelschild-schrift-dunkel: "#26211A"
  einband-tinte-dunkel: "#8F8572"
  einband-ochsenblut-dunkel: "#B4505C"
  einband-tannengruen-dunkel: "#44916F"
  einband-verlagsblau-dunkel: "#4A86BC"
  einband-indigo-dunkel: "#7C70B8"
  einband-ocker-dunkel: "#A87B2A"
typography:
  display:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "22px"
    fontWeight: 600
  headline:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "20px"
    fontWeight: 600
  title:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "19px"
    fontWeight: 600
  action:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 600
  plate:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 600
  chip:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  group:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 700
  body:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 400
rounded:
  none: "0px"
  xs: "2px"
  sm: "4px"
  bar: "6px"
  knob: "7px"
spacing:
  label: "3px"
  chip: "4px"
  action: "6px"
  group: "8px"
  book: "10px"
  pair: "12px"
  row: "14px"
  edge: "18px"
  column: "28px"
components:
  button-primary:
    backgroundColor: "{colors.ochsenblut}"
    textColor: "{colors.auf-ochsenblut}"
    typography: "{typography.action}"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
  button-primary-hover:
    backgroundColor: "{colors.ochsenblut-hover}"
  button-primary-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.bleistift}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.tinte}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
  button-quiet-hover:
    backgroundColor: "{colors.ochsenblut-hauch}"
  button-head:
    backgroundColor: "transparent"
    textColor: "{colors.kopfband-schrift}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "6px 10px"
  button-head-hover:
    backgroundColor: "{colors.kopfband-aufgehellt}"
  chip:
    backgroundColor: "{colors.papierfeld}"
    textColor: "{colors.tinte}"
    typography: "{typography.chip}"
    rounded: "{rounded.sm}"
    padding: "4px 0"
  chip-hover:
    backgroundColor: "{colors.ochsenblut-hauch}"
  chip-checked:
    backgroundColor: "{colors.ochsenblut}"
    textColor: "{colors.auf-ochsenblut}"
  input:
    backgroundColor: "{colors.papierfeld}"
    textColor: "{colors.tinte}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "4px 8px"
  shelf-row-selected:
    backgroundColor: "{colors.ochsenblut-hauch}"
    textColor: "{colors.tinte}"
  stimmenheft:
    rounded: "{rounded.xs}"
    width: "104px"
    height: "128px"
  titelschild:
    backgroundColor: "{colors.titelschild}"
    textColor: "{colors.titelschild-schrift}"
    typography: "{typography.plate}"
    rounded: "{rounded.none}"
    width: "80px"
    height: "60px"
---

# Design System: PartFocus

## Overview

**Creative North Star: "Die Stimmenhefte"**

Die Hauptfläche zeigt das Ergebnis, nicht die Eingabe. Jeder Track, der entstehen wird, liegt als Stimmenheft im Einband seiner Stimmlage auf einem Kartontisch: das Bild, das eine Chorleitung vom Notenschrank kennt. Ein Stück ist eine Regalreihe aus Titel, Trackzahl und Heften, die Zahl auf dem Hauptknopf sagt, was entsteht, und beim Erstellen füllen sich die Hefte der Reihe nach mit ihrem Einband.

Das Papierfeld darunter trägt die Einstellungen, immer offen und in Windows-vertrauten Bedienelementen. Oben schließt ein Kopfband in Ochsenblut das Fenster ab, wie der Rücken eines Notenbands. Farbe bedeutet hier etwas: Die Einbände sagen, welche Stimme ein Heft ist, Ochsenblut sagt, was als Nächstes zu tun ist, alles andere bleibt Karton, Papier und Tinte. Die Oberfläche ist flach und folgt dem hellen oder dunklen Modus von Windows, auch im laufenden Betrieb.

PartFocus soll weder wie eine bunte Consumer-App wirken noch wie ein altes Vereins-Tool aus den 90ern.

**Key Characteristics:**
- sechs feste Einbandfarben als Code für die Stimmlagen, nie als Schmuck
- Ochsenblut für Kopfband und Hauptaktion, warme Kartontöne für alles andere
- Bahnschrift für das, was benennt oder auslöst, Segoe UI für den Rest
- gezeichnete Hefte mit Falz, zwei Heftklammern und hellem Titelschild
- flach, ohne Schatten und Verläufe
- alle Einstellungen immer sichtbar, höchstens ein Hauptknopf

## Colors

Warme Karton- und Papiertöne mit tintenfarbener Schrift, darauf sechs gedeckte Einbände und ein Ochsenblut als Handlungsfarbe. Jedes Paar unten steht in der Reihenfolge hell / dunkel. Das Suffix `-dunkel` im Tokennamen meint immer den Dunkelmodus, nicht einen dunkleren Ton: `ochsenblut-dunkel` ist heller als `ochsenblut`. In Klammern steht jeweils das Feld aus `partfocus/theme.py`.

### Primary
- **Ochsenblut** (`accent`, #7A1F2B / #D06A74): Hauptknopf, gewählter Chip, gewählte Checkbox, Griff des Schiebereglers, Fortschrittsbalken, Fokusrahmen auf neutralem Grund, Rahmen beim Hineinziehen, Links in Dialogen. Im Dunkelmodus ist es ein aufgehelltes Altrosa, weil es sonst auf dem dunklen Karton nicht bestehen würde.
- **Ochsenblut Hover** (`accent_hover`, #641722 / #DC858D): Hover des Hauptknopfs, hell tiefer, dunkel heller.
- **Ochsenblut-Hauch** (`accent_soft`, #EFD9D0 / #4A2A2C): Hover von Knöpfen und Chips, ausgewählte Regalreihe, Auswahl in Aufklapplisten.
- **Auf Ochsenblut** (`on_accent`, #FFFFFF / #231F1A): Schrift und Häkchen auf Ochsenblut. Hell weiß, dunkel fast schwarz.

### Secondary
Die Einbände sind der Stimmcode. Sie erscheinen nur auf Heften.
- **Einband Tinte** (`gesamt`, #26211A / #8F8572): Gesamt. Im Dunkelmodus ein warmes Steingrau, weil Tinte auf dem dunklen Tisch verschwände.
- **Einband Ochsenblut** (`sopran`, #7A1F2B / #B4505C): Sopran, Mezzo, Treble, Diskant.
- **Einband Tannengrün** (`alt`, #2F6B4F / #44916F): Alt, Contralto.
- **Einband Verlagsblau** (`tenor`, #1F4E79 / #4A86BC): Tenor.
- **Einband Indigo** (`bass`, #463A73 / #7C70B8): Bass, Bariton.
- **Einband Ocker** (`solo`, #94671C / #A87B2A): Solo und alles Sonstige.

### Tertiary
- **Kopfband** (`head`, #7A1F2B / #5E1722): Fläche der Werkzeugleiste und des Update-Bands. Im Dunkelmodus bewusst tiefer als Ochsenblut.
- **Kopfband aufgehellt** (`head_hover`, #8F2D3A / #74232F): Hover im Kopfband, obere Linie des Update-Bands, Rahmen deaktivierter Knöpfe im Kopfband.
- **Kopfband-Schrift** (`head_text`, #FFFFFF / #FFFFFF): Titel, Knopfschrift und Fokusrahmen im Kopfband.
- **Kopfband gedämpft** (`head_muted`, #E2C4C4 / #D9BDBD): Knopfrahmen im Kopfband, Schrift deaktivierter Knöpfe dort.
- **Titelschild** (`label`, #F4EFE0 / #F4EFE0): Schild, Heftklammern, Falzlinie (mit Alpha 70 von 255) und Häkchen auf dem Heft. In beiden Modi hell.
- **Titelschild-Schrift** (`label_text`, #26211A / #26211A): Stimmname auf dem Schild, in beiden Modi dunkel.

### Neutral
- **Kartontisch** (`app`, #E7DFC9 / #231F1A): Grund des Regals und des leeren Zustands, die Fläche, auf der die Hefte liegen.
- **Papierfeld** (`panel`, #F4EFE0 / #2E2922): Band der Einstellungen, Füllung von Eingabefeldern, Chips, Checkboxen, Tooltips und Aufklapplisten.
- **Tinte** (`text`, #26211A / #EFE8D8): Text, Stücktitel, Fokusrahmen auf ochsenblutgefüllten Elementen.
- **Bleistift** (`text_muted`, #5A5142 / #B5AB99): Trackzeile, Statuszeile, Wert des Schiebereglers, deaktivierte Texte, Stimmnamen auf leeren Heften.
- **Griffelgrau** (`control`, #756B58 / #83796A): Umriss von Bedienelementen, Reglerbahn, Griff der Bildlaufleiste; auf beiden Flächen mindestens 3:1.
- **Pappkante** (`border_strong`, #B8AD92 / #5C5345): Trennlinie der Regalreihen, obere Linie des Papierfelds, alle deaktivierten Rahmen, Füllung gewählter deaktivierter Chips und Checkboxen.
- **Falzlinie** (`border`, #CFC5AC / #453E33): nur die Bahn des Fortschrittsbalkens.

### Status
- **Warnocker** (`warn`, #7A5608 / #E0B861): wird verwendet, genau einmal: die Zeile unter dem Titel einer unlesbaren Partitur.
- **Siegelrot** (`danger`, #9B2C22 / #E08376): ist in `theme.py` angelegt, aber weder im Stylesheet noch in `gui.py` verwendet. Fehler laufen über Dialoge von Windows und über die Statuszeile in Bleistift.

### Named Rules
**The Fixed Cover Rule.** Jede Stimme hat ihren festen Einband, und allein `gui.cover()` vergibt ihn: zuerst Gesamt, dann schlägt das Wort „solo“ jede Stimmlage, dann die Stimmlagen, sonst Ocker. Neue Oberflächen rufen `cover()` auf und treffen die Zuordnung nie selbst. Einbandfarben stehen nur auf Heften, nie auf Knöpfen, Flächen oder Text.

**The Three To One Rule.** Jeder Einband hält in beiden Modi mindestens 3:1 gegen den Kartontisch und gegen das Titelschild, das auch Klammern, Falz und Häkchen färbt. `tests/test_gui.py` prüft das. Wer eine Farbe ändert, lässt den Test laufen und passt nicht den Test an.

**The Both Modes Rule.** Jede Farbe entsteht als Feld in `Palette`, mit Wert für hell und dunkel. Im Code stehen keine freien Farbwerte; die einzige Ausnahme ist der Pfeil der Auswahlfelder (#8A7F6C in `tools/make_controls.py`), den ein Stylesheet nicht einfärben kann. Häkchen und Pfeil entstehen aus diesem Skript und liegen als PNG in `assets/controls`.

## Typography

**Display Font:** Bahnschrift (mit Segoe UI, sans-serif)
**Body Font:** Segoe UI Variable Text (mit Segoe UI, sans-serif)

**Character:** Bahnschrift hat die nüchterne Beschriftungsqualität von Schildern und Etiketten und gehört damit auf Hefte und Titel. Segoe UI hält alles andere bei Windows. Keine Schrift wird mitgeliefert, beide kommen vom System.

### Hierarchy
- **Display** (Bahnschrift 600, 22 px): Aufforderung im leeren Zustand.
- **Headline** (Bahnschrift 600, 20 px): „PartFocus“ im Kopfband.
- **Title** (Bahnschrift 600, 19 px): Stücktitel im Regal, einzeilig, zu lange Titel werden in der Mitte gekürzt.
- **Action** (Bahnschrift 600, 16 px): Hauptknopf.
- **Plate** (Bahnschrift 600, 13 px): Stimmname auf dem Titelschild, zentriert, höchstens drei Zeilen.
- **Chip** (Bahnschrift 400, 13 px): Tempo-Chips.
- **Group** (Segoe UI 700, 13 px): Spaltenköpfe Stimmen, Tempo, Dateien.
- **Body** (Segoe UI 400, 13 px): Beschriftungen, Felder, Knöpfe außer dem Hauptknopf, Statuszeile, Texte des leeren Zustands.

### Named Rules
**The Label Face Rule.** Bahnschrift steht auf Titeln, Titelschildern, Tempo-Chips und dem Hauptknopf, Segoe UI überall sonst. Die Spaltenköpfe im Papierfeld bleiben Segoe UI: Sie gliedern und benennen nichts, was entsteht. Ein Hauptknopf, der zu Quiet wird, verliert die Bahnschrift mit.

## Layout

Ein Fenster aus übereinanderliegenden Bändern, randlos, ohne Seitenleiste: Kopfband, bei Bedarf das Update-Band, Regal, Papierfeld. Nur das Regal wächst, es scrollt senkrecht und nie waagerecht. Das Fenster öffnet mit 1120 × 700 px; eine Mindestgröße ergibt sich aus den Inhalten.

Das Papierfeld hat Innenabstände von 18 px seitlich, 12 px oben und 14 px unten und vier Spalten mit 28 px Abstand: Stimmen, Tempo und Dateien im Verhältnis 5:4:4, rechts die 180 px breite Aktionsspalte. Sie ist mindestens 127 px hoch, damit das Papierfeld nicht springt, wenn Balken oder Status erscheinen. Innerhalb einer Spalte stehen Zeilen 8 px auseinander, Beschriftung und Feld 3 px, Feldpaare 12 px, Checkboxen 16 px, die Reglerzeile 10 px, Chips 4 px, die Teile der Aktionsspalte 6 px.

Eine Regalreihe hat 18 px seitlichen und 14 px vertikalen Innenabstand. Die Kopfzone mit Titel und Trackzeile ist 54 px hoch, darunter stehen die Hefte in 104 × 128 px mit 10 px Abstand und brechen in so viele Zeilen um, wie die Breite verlangt. Der leere Zustand zentriert Aufforderung, Erklärung und eine Beispielreihe aus fünf leeren Heften. Einen Umbruch nach Fensterbreite gibt es sonst nicht.

### Named Rules
**The Always Visible Rule.** Alle Einstellungen bleiben ohne Klick sichtbar, das ist eine Entscheidung des Nutzers. Keine Akkordeons, Tabs oder „Erweitert“-Dialoge. Was gerade nicht gilt, wird deaktiviert und bleibt stehen, so wie Klang und Qualität bei reinem MIDI.

## Elevation & Depth

Die Oberfläche ist flach. Tiefe entsteht nur aus Flächentönen, Tisch gegen Papierfeld gegen Kopfband, und aus 1-px-Linien. Die Hefte liegen ohne Schatten auf dem Tisch, ihre Plastizität kommt allein aus gezeichnetem Falz, Klammern und Schild.

### Named Rules
**The Flat Table Rule.** Keine Schatten und keine Verläufe, weder an Heften noch an Dialogen oder Aufklapplisten. Was sich abheben soll, bekommt einen anderen Flächenton oder eine Linie.

## Shapes

Die Formensprache ist die von Papier und Pappe: fast rechtwinklig. Hefte haben 2 px Rundung, das Titelschild ist scharfkantig, Bänder laufen ohne Rundung bis zum Fensterrand. Knöpfe, Chips und Felder haben 4 px, Checkboxen, Fortschrittsbalken und Reglerbahn 2 px. Rund sind nur der Griff des Schiebereglers (7 px Radius) und die Griffe der Bildlaufleiste (6 px). Linien sind 1 px, Fokusrahmen 2 px; das Innenmaß sinkt beim Fokus um 1 px, damit nichts springt. Gestrichelt ist nur der Umriss eines leeren Hefts.

## Components

### Buttons
Windows-vertraut, mit einem einzigen lauten Knopf.
- **Shape:** kleine Rundung (4 px).
- **Primary:** gefüllt mit Ochsenblut, Schrift Auf Ochsenblut in Action, Innenabstand 12 × 16 px. Die Beschriftung nennt die Zahl: „8 Tracks erstellen“.
- **Quiet:** ohne Füllung, 1 px Griffelgrau, Innenabstand 6 × 10 px, Body. Auch die Knöpfe der Dialoge sehen so aus; ihr Standardknopf trägt 2 px Ochsenblut und Gewicht 600.
- **Kopfband:** ohne Füllung, Rahmen Kopfband gedämpft, Schrift weiß; Hover Kopfband aufgehellt.
- **Hover / Focus:** Hover füllt Quiet mit Ochsenblut-Hauch und Primary mit Ochsenblut Hover. Fokus ist ein 2-px-Rahmen: Ochsenblut auf neutralem Grund, Tinte auf gefülltem Ochsenblut, weiß im Kopfband.
- **Disabled:** Bleistift, Rahmen Pappkante, Primary verliert die Füllung. Im Kopfband Schrift gedämpft, Rahmen aufgehellt.

**The One Next Step Rule.** Es gibt höchstens einen Primary, und er sitzt auf dem nächsten sinnvollen Schritt: „Tracks erstellen“, nach einem Lauf „Ordner öffnen“, bis sich etwas ändert. Dann wandert er zurück. Während des Laufs gibt es keinen, „Abbrechen“ ist Quiet. Die Art wechselt nur über `set_kind()`, weil Qt sonst nicht neu poliert.

**The Keyboard Focus Rule.** Knöpfe, Chips, Checkboxen und der Schieberegler stehen auf `Qt.TabFocus`. Ein Fokusrahmen erscheint dort nur bei Tastaturbedienung, sonst sähe ein angeklickter Chip wie ein gewählter aus.

### Chips
- **Style:** Papierfeld, 1 px Griffelgrau, Chip-Schrift, 4 px senkrechter Innenabstand. Die sechs Tempo-Werte teilen sich die Spaltenbreite.
- **State:** Gewählt in Ochsenblut mit Schrift Auf Ochsenblut. Mehrfachauswahl, mindestens einer bleibt gewählt. Während des Laufs gewählt in Pappkante mit Tinte.

### Inputs / Fields
- **Style:** Papierfeld, 1 px Griffelgrau, 4 px Rundung, 4 × 8 px Innenabstand. Gilt für Auswahl- und Textfelder. Der Pfeil ist ein PNG aus `assets/controls`.
- **Focus:** 2 px Ochsenblut.
- **Disabled:** ohne Füllung, Bleistift, Rahmen Pappkante; die Beschriftung wird mit gedämpft.
- **Checkbox:** 14 px, 1 px Griffelgrau, 2 px Rundung; gewählt Ochsenblut mit Häkchen aus `assets/controls`. Fokus: 2 px am Kästchen, gewählt in Tinte.
- **Slider:** Bahn 3 px in Griffelgrau, runder Griff 14 px in Ochsenblut, daneben der Wert in Worten in Bleistift. Den dB-Wert zeigt nur der Tooltip.

### Stimmenheft
Das Signaturelement. Ein Heft ist 104 × 128 px groß und wird in `gui.py` gezeichnet, nicht gestylt.
- **Aufbau:** Einbandfläche mit 2 px Rundung; Falz 1 px, 8 px vom linken Rand; zwei Heftklammern, 2 × 10 px, auf dem Falz in den Viertelpunkten der Höhe; Titelschild 34 px unter der Oberkante, 14 px vom linken und 10 px vom rechten Rand, 60 px hoch.
- **Titelschild:** Stimmname in Plate, zentriert. Lange zusammengesetzte Wörter brechen an beliebiger Stelle um, damit nichts abgeschnitten wird, ab der dritten Zeile wird gekürzt.
- **Ruhe:** volle Einbandfläche. Das heißt „dieser Track wird entstehen“, nicht „er liegt schon im Ordner“.
- **Leer:** gestrichelter Umriss, 1,5 px im Einbandton, Stimmname in Bleistift, kein Schild. So stehen die Hefte zu Beginn eines Laufs und in der Beispielreihe des leeren Zustands.
- **Fertig:** gezeichnetes Häkchen unten rechts in Titelschild-Farbe, 2 px mit runden Enden.

**The Filling Book Rule.** Während eines Laufs stehen alle Hefte als Umrisse und füllen sich der Reihe nach von unten mit ihrem vollständigen Einband, proportional zum Gesamtfortschritt des Laufs. Dieser zählt fertige Ausgaben: Hat ein Lauf so viele Ausgaben wie Hefte, springt jedes Heft in einem Schritt auf voll, Teilfüllungen zeigen sich erst bei mehreren Tempi, MP3 plus MIDI oder einem Messdurchlauf. Das Regal scrollt dem Stück nach, das gerade entsteht, und bleibt dabei selbst scrollbar.

**The Earned Tick Rule.** Das Häkchen steht nur nach einem vollständig erfolgreichen Lauf, auf allen Heften, und verschwindet bei jeder Änderung an Liste oder Einstellungen. Nach Abbruch, Fehler oder einem Lauf mit zu prüfenden Tracks gibt es keins. Volle Einbände allein belegen nichts.

### Regalreihe
- **Style:** Stücktitel in Title, darunter die Trackzeile in Bleistift, „26 Tracks in 2 Tempi“, darunter die Heftreihe. Reihen trennt 1 px Pappkante.
- **Selected:** Ochsenblut-Hauch, die Schrift bleibt Tinte. Mehrfachauswahl; während eines Laufs ist nichts wählbar.
- **Unlesbar:** statt Heften eine Zeile in Warnocker. Die Datei zählt nicht mit.
- **Drop:** Beim Darüberziehen rahmt 2 px Ochsenblut die Fläche.

**The Unknown Length Rule.** Trackdauern zeigt PartFocus nirgends, weil sie vor dem Rendern unbekannt sind. Das Regal zählt Tracks und Tempi, die Abschlusszeile nennt Anzahl und Größe. Die MB/min in der Qualitätswahl sind eine Rate und keine Dauer.

### Kopfband
- **Style:** Fläche Kopfband, 12 × 8 px Innenabstand, links „PartFocus“ in Headline, rechts die Dateiaktionen als Kopfband-Knöpfe. Das Update-Band ist dieselbe Fläche direkt darunter, 18 × 6 px, und erscheint nur, wenn ein Update bereitliegt.

### Fortschritt und Status
Dünner Balken (4 px) in Ochsenblut auf Falzlinie, oben in der Aktionsspalte und nur im Lauf sichtbar, darunter die Statuszeile in Bleistift. Die eigentliche Fortschrittsanzeige sind die Hefte.

## Do's and Don'ts

### Do:
- **Do** Farben aus `partfocus/theme.py` beziehen und jede neue Farbe für beide Modi anlegen.
- **Do** Einbände nur über `gui.cover()` vergeben und die 3:1 gegen Tisch und Schild mit `tests/test_gui.py` absichern.
- **Do** Bahnschrift nur auf Titeln, Titelschildern, Tempo-Chips und dem Hauptknopf setzen, Segoe UI überall sonst.
- **Do** neue Bedienelemente als Quiet bauen und `Qt.TabFocus` setzen, wenn es Knöpfe, Chips oder Checkboxen sind.
- **Do** Fortschritt auf den Heften zeigen und das Häkchen an einen vollständig erfolgreichen Lauf binden.
- **Do** Häkchen und Pfeil mit `tools/make_controls.py` neu erzeugen, wenn sich ihre Farben ändern.

### Don't:
- **Don't** Einbandfarben als Akzent, Fläche oder Textfarbe außerhalb der Hefte verwenden.
- **Don't** Stimmen abweichend von `gui.cover()` einfärben oder dieselbe Stimme je nach Ort anders zeigen.
- **Don't** Schatten oder Verläufe einsetzen, auch nicht an Dialogen oder Aufklapplisten.
- **Don't** Einstellungen hinter Klicks verstecken.
- **Don't** einen zweiten Primary zeigen.
- **Don't** Trackdauern anzeigen oder schätzen.
- **Don't** Fokusrahmen per Mausklick auf Knöpfen, Chips oder Checkboxen erscheinen lassen.
- **Don't** die Oberfläche zur bunten Consumer-App machen; die Farbe bleibt bei den Heften und einer Handlung.
- **Don't** in das alte Vereins-Tool der 90er zurückfallen; das Regal zeigt Hefte, keine graue Dateiliste.
