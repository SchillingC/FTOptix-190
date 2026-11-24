# HMI-Schnittstellen- und Seitendokumentation

## 1. Dokumentationsumfang

Dieses Dokument beschreibt ausschließlich die Schnittstelle zwischen FactoryTalk-HMI und dem Controller-Tag `HMI`.

Andere Controller-Tags, direkte I/O-Aliase, Feldgeräte, Kommunikations- und SPS-Programmtags werden bewusst nicht ausgewertet.

Ausgangsbasis sind:

- Controller-Tag-Export `CPX190V06_001_Controller_Tags.CSV`
- FactoryTalk-Display-Exporte der Seiten 0020 bis 0085
- die globalen Exporte `[ALARM].xml`, `[DIAGNOSTICS].xml` und `[INFORMATION].xml`

Die Dokumentation beschreibt die im Export erkennbaren HMI-Verbindungen. Die interne Bedeutung der UDT-Mitglieder und die SPS-Folgelogik können nur dann verbindlich bestätigt werden, wenn die Definition des UDT `UDT_HMI` und die zugehörige SPS-Logik vorliegen.

## 2. Schnittstelle zum Controller

### 2.1 Controller-Tag

Der Controller-Tag-Export enthält:

| Eigenschaft | Wert |
|---|---|
| Tag-Name | `HMI` |
| Datentyp | `UDT_HMI` |
| Tag-Typ | Controller Tag |
| Constant | `false` |
| External Access | `Read/Write` |

Die FactoryTalk-Seiten adressieren den Tag über den PLC-Kurzverweis:

```text
[PLC1]HMI
```

Die vollständigen Adressen folgen daher dem Muster:

```text
[PLC1]HMI.<UDT-Mitglied>.<weiteres Mitglied>
```

`ExternalAccess := Read/Write` erlaubt externes Lesen und Schreiben auf Controller-Ebene. Eine fachliche Schreibfreigabe ergibt sich daraus nicht.

### 2.2 Wiederkehrendes Bedienmuster

Viele HMI-Bedienelemente verwenden dieselben UDT-Elemente:

| Mitglied | Erkennbare Verwendung in der HMI |
|---|---|
| `.Msi` | Anzeige- oder Rückmeldestatus des Bedienelements |
| `.Enable` | Freigabe beziehungsweise Aktivierbarkeit des Bedienelements |
| `.On` | Wert beziehungsweise Stellbit, das über das Bedienelement beschrieben wird |
| `.Visible` | Sichtbarkeit des Bedienelements |
| `.Handshake` | Bestätigung für einen Datenaustausch, insbesondere Uhrzeitübernahme |

Die konkrete HMI-Bedeutung ist für die exportierten Objekte erkennbar. Die Schreibdauer, Impulsbildung und Verarbeitung in der SPS müssen anhand des UDTs und der SPS-Logik geprüft werden.

### 2.3 Hauptelemente des HMI-Tags

| HMI-Unterstruktur | Zweck |
|---|---|
| `HMI.General` | Allgemeine Bedienung, Betriebsarten, Reset, Vakuum, manueller Spleiß, Uhrzeit und Bildanwahl |
| `HMI.PreparationLeft` | Vorbereitung und Bereitschaft der linken Rolle |
| `HMI.PreparationRight` | Vorbereitung und Bereitschaft der rechten Rolle |
| `HMI.ReelSelectionLeft` | Auswahl der linken Rolle |
| `HMI.ReelSelectionRight` | Auswahl der rechten Rolle |
| `HMI.ManualLeft` | Handbedienung der linken Rolle |
| `HMI.ManualRight` | Handbedienung der rechten Rolle |
| `HMI.CylFixingLeft` | Zylinder „Fixieren“, linke Seite |
| `HMI.CylFixingRight` | Zylinder „Fixieren“, rechte Seite |
| `HMI.CylGluingLeft` | Zylinder „Kleben“, linke Seite |
| `HMI.CylGluingRight` | Zylinder „Kleben“, rechte Seite |
| `HMI.CylSeperatingKnife` | Trennmesser-Zylinder |
| `HMI.InformationLeft` | Prozess- und Rolleninformation links |
| `HMI.InformationRight` | Prozess- und Rolleninformation rechts |
| `HMI.PLCStatus` | SPS-Laufzeit- und Fehlerstatus |
| `HMI.Enable` | Stations- und Funktionsfreigaben beziehungsweise Stationsmerker |

## 3. Schnittstellen nach HMI-Seite

### 3.1 Seite 0020 — Produktion

#### Rollenwahl

| Funktion | Schnittstelle |
|---|---|
| Linke Rolle | `[PLC1]HMI.ReelSelectionLeft.Selection` |
| Rechte Rolle | `[PLC1]HMI.ReelSelectionRight.Selection` |

Für beide Funktionen werden `.Msi`, `.Enable`, `.On` und `.Visible` verwendet.

#### Vorbereitung und Spleißbereitschaft

| Funktion | Schnittstelle |
|---|---|
| Rollenbremse links | `[PLC1]HMI.PreparationLeft.ReelBrake` |
| Spleißbereitschaft links | `[PLC1]HMI.PreparationLeft.ReadyForSplice` |
| Rollenbremse rechts | `[PLC1]HMI.PreparationRight.ReelBrake` |
| Spleißbereitschaft rechts | `[PLC1]HMI.PreparationRight.ReadyForSplice` |

Die vier Funktionen verwenden `.Msi`, `.Enable`, `.On` und `.Visible`.

#### Allgemeine Funktionen

| Funktion | Schnittstelle |
|---|---|
| Vakuum | `[PLC1]HMI.General.Vacuum` |
| Reset | `[PLC1]HMI.General.Reset` |
| Manueller Spleiß | `[PLC1]HMI.General.SpliceManual` |
| Handbetrieb wählen | `[PLC1]HMI.General.Manual` |

Diese Bedienelemente verwenden `.Msi`, `.Enable`, `.On` und `.Visible`. Die Handbetriebsbedienung ist zusätzlich mit `CurrentUserHasCode(B)` abgesichert.

#### Prozessinformationen

| Anzeige | Schnittstelle |
|---|---|
| Durchmesser Folienrolle links | `[PLC1]HMI.InformationLeft.DiameterFoilRoll` |
| Durchmesser Folienrolle rechts | `[PLC1]HMI.InformationRight.DiameterFoilRoll` |

Die Sichtbarkeit der Rollendurchmesser orientiert sich an der entsprechenden Rollenwahl.

### 3.2 Seite 0021 — Handbetrieb

Die Seite stellt ausschließlich Elemente der Struktur `HMI` dar und verwendet wiederkehrend `.Msi`, `.Enable`, `.On` und `.Visible`.

| Handfunktion | HMI-Schnittstelle |
|---|---|
| Reset | `[PLC1]HMI.General.Reset` |
| Trennmesser | `[PLC1]HMI.CylSeperatingKnife.WorkingPosition` |
| Automatik wählen | `[PLC1]HMI.General.Automatic` |
| Rollenbremse automatisch links | `[PLC1]HMI.ManualLeft.ReelBrakeAutomatic` |
| Zylinder Kleben links | `[PLC1]HMI.CylGluingLeft.WorkingPosition` |
| Vakuum links | `[PLC1]HMI.ManualLeft.Vacuum` |
| Rollenbremse links | `[PLC1]HMI.ManualLeft.ReelBrake` |
| Zylinder Fixieren links | `[PLC1]HMI.CylFixingLeft.WorkingPosition` |
| Zylinder Kleben rechts | `[PLC1]HMI.CylGluingRight.WorkingPosition` |
| Vakuum rechts | `[PLC1]HMI.ManualRight.Vacuum` |
| Rollenbremse rechts | `[PLC1]HMI.ManualRight.ReelBrake` |
| Zylinder Fixieren rechts | `[PLC1]HMI.CylFixingRight.WorkingPosition` |
| Rollenbremse automatisch rechts | `[PLC1]HMI.ManualRight.ReelBrakeAutomatic` |

Die SPS-Kommentare im Controller-Export bestätigen, dass verschiedene `.Visible`-Elemente die HMI-Schaltflächen des Handbetriebs abhängig vom Anlagenzustand ein- oder ausblenden.

### 3.3 Seite 0060 — Diagnose

Die Diagnose besteht aus einer Alarmstatusliste und HMI-Bedienobjekten:

| Funktion | HMI-Schnittstelle |
|---|---|
| Reset | `[PLC1]HMI.General.Reset` |
| Automatik wählen | `[PLC1]HMI.General.Automatic` |
| Handbetrieb wählen | `[PLC1]HMI.General.Manual` |

Verwendet werden `.Msi`, `.Enable`, `.On` und `.Visible`. Die Handbetriebsanzeige und -bedienung sind zusätzlich mit `CurrentUserHasCode(B)` verknüpft.

Konkrete Alarmtag-Adressen sind in diesem Display-Export nicht angegeben. Die Alarmstatusliste selbst gehört daher nicht zur dokumentierten Datenzuordnung des Tags `HMI`.

### 3.4 Seite 0061 — Historie

Die Historienseite verwendet keine Referenzen auf `HMI` oder `[PLC1]HMI`. Sie stellt die konfigurierte Alarmhistorie dar. Innerhalb der ausschließlich betrachteten Schnittstelle zum Controller-Tag `HMI` bestehen daher keine Schnittstellendaten.

### 3.5 Seite 0080 — Einstellungen Allgemeines

#### Lampentest und Betriebsarten

| Funktion | HMI-Schnittstelle |
|---|---|
| Lampentest | `[PLC1]HMI.General.BtnLamptest.On` |
| Automatik wählen | `[PLC1]HMI.General.Automatic` |
| Handbetrieb wählen | `[PLC1]HMI.General.Manual` |
| Long-Dancer-Freigabe/-Status | `[PLC1]HMI.Enable.Long_Dancer` |

Bei Automatik und Handbetrieb werden die Elemente `.Msi`, `.Enable`, `.On` und `.Visible` genutzt. Der Handbetrieb ist zusätzlich mit `CurrentUserHasCode(B)` verbunden.

#### Uhrzeitübernahme

Die HMI bearbeitet folgende Zeitbestandteile:

- `[PLC1]HMI.General.RemoteDateTime.Day`
- `[PLC1]HMI.General.RemoteDateTime.Month`
- `[PLC1]HMI.General.RemoteDateTime.Year`
- `[PLC1]HMI.General.RemoteDateTime.Hour`
- `[PLC1]HMI.General.RemoteDateTime.Minute`

Für die Übernahme werden außerdem verwendet:

- `[PLC1]HMI.General.BtnClockEnter.On`
- `[PLC1]HMI.General.BtnClockEnter.Handshake`

Der Export belegt einen Enter-/Handshake-Ablauf. Die genaue Erkennung, Reihenfolge und zeitliche Behandlung der Übernahme muss aus dem SPS-Programm übernommen werden.

### 3.6 Seite 0081 — Information

Die Seite enthält Navigation und Informationen. Im bereitgestellten Export gibt es keine Referenz auf `HMI` beziehungsweise `[PLC1]HMI`; andere Informationsquellen liegen außerhalb des angeforderten Schnittstellenumfangs.

### 3.7 Seite 0084 — SPS-Fehler

Diese Seite verwendet ausschließlich Mitglieder von `[PLC1]HMI.PLCStatus`:

| HMI-Anzeige | Schnittstelle |
|---|---|
| Maximale Scan-Zeit | `[PLC1]HMI.PLCStatus.MaxScanTime` |
| Letzte Scan-Zeit | `[PLC1]HMI.PLCStatus.LastScanTime` |
| Fehlerart | `[PLC1]HMI.PLCStatus.Type` |
| Minor-Fault-Bit 1 | `[PLC1]HMI.PLCStatus.MinorFault.1` |
| Minor-Fault-Bit 3 | `[PLC1]HMI.PLCStatus.MinorFault.3` |
| Minor-Fault-Bit 4 | `[PLC1]HMI.PLCStatus.MinorFault.4` |
| Minor-Fault-Bit 6 | `[PLC1]HMI.PLCStatus.MinorFault.6` |
| Minor-Fault-Bit 7 | `[PLC1]HMI.PLCStatus.MinorFault.7` |
| Minor-Fault-Bit 9 | `[PLC1]HMI.PLCStatus.MinorFault.9` |
| Minor-Fault-Bit 10 | `[PLC1]HMI.PLCStatus.MinorFault.10` |

`MaxScanTime` und `LastScanTime` werden in der HMI durch 1000 geteilt.

`PLCStatus.Type` wird zu diesen Texten ausgewertet:

| Wert | Anzeige |
|---|---|
| 1 | Power Loss |
| 3 | I/O Fault |
| 4 | Instruction execution |
| 5 | Fault Handler |
| 6 | Watchdog |
| 7 | Stack |
| 8 | Mode Change |
| 11 | Motion |
| sonst | no Fault present |

Weitere Bedeutungen der Minor-Fault-Bits sind aus den Display-Exporten nicht erkennbar.

### 3.8 Seite 0085 — Stationsmerker

| Funktion | HMI-Schnittstelle |
|---|---|
| Short-Dancer-Anzeige | `[PLC1]HMI.Enable.Short_Dancer` |
| Long-Dancer-Anzeige/-Bedienung | `[PLC1]HMI.Enable.Long_Dancer` |
| Vakuumversorgung | `[PLC1]HMI.Enable.Vacuum_Supply` |

`Long_Dancer` wird auf dieser Seite sowohl als Anzeige als auch als beschreibbarer Wert verwendet. Der Export belegt nicht allein, wann ein Wechsel gültig ist oder welche SPS-Verriegelungen ihn zulassen.

## 4. Globale Anzeigen

### 4.1 Alarmbanner

`[ALARM].xml` enthält Quittierung, Alarmton-Aus, Leeren und Schließen. Es ist jedoch keine direkte Referenz auf den Controller-Tag `HMI` vorhanden. Die konkreten Alarmquellen gehören nicht zur dokumentierten `HMI`-Schnittstelle.

### 4.2 Diagnosefenster

`[DIAGNOSTICS].xml` enthält eine Diagnose- beziehungsweise Meldungsliste mit Lösch- und Navigationsfunktionen. Direkte Referenzen auf `HMI` sind nicht vorhanden.

### 4.3 Informationsfenster

`[INFORMATION].xml` enthält Quittier- und Schließfunktionen. Eine direkte Referenz auf `HMI` ist nicht vorhanden.

## 5. Abgenommene Sicht der Datenrichtungen

| Funktion | Richtung zur HMI |
|---|---|
| `.Msi` | Controller → HMI als Status-/Rückmeldung |
| `.Enable` | Controller → HMI als Bedienfreigabe |
| `.Visible` | Controller → HMI als Sichtbarkeitsvorgabe |
| `.On` bei Button-/Bedienobjekten | HMI → Controller als Bedienwert |
| Prozesswert, beispielsweise `DiameterFoilRoll` | Controller → HMI |
| Uhrzeitkomponenten | HMI ↔ Controller, mit Enter/Handshake |
| `PLCStatus` | Controller → HMI |
| `Enable.Short_Dancer`, `Enable.Long_Dancer`, `Enable.Vacuum_Supply` | Controller → HMI; `Long_Dancer` und `Vacuum_Supply` werden auf der Stationsseite auch durch HMI-Werte beschrieben |

Diese Richtungen beschreiben die im Display-Export konfigurierte Verwendung. Eine Änderung des SPS-Betriebs darf nicht ausschließlich aus dieser Darstellung abgeleitet werden.

## 6. Offene Punkte für die verbindliche Schnittstellendokumentation

Für eine vollständige und verbindliche Beschreibung des UDT `UDT_HMI` sind noch erforderlich:

1. Definition aller Mitglieder und Datentypen von `UDT_HMI`
2. Beschreibung der Datenrichtung und Rechte pro Mitglied
3. Schreibdauer beziehungsweise Momentary-Logik der `.On`-Signale
4. Freigabe- und Verriegelungslogik zu `.Enable` und `.Visible`
5. Bedeutung und Zuordnung der `MinorFault`-Bits
6. Einheit und Format der Rollendurchmesser
7. Zeitablauf des Handshakes für `BtnClockEnter`
8. Bedeutung des Security-Codes `B`
9. Beschreibung der `Enable`-Signale Short Dancer, Long Dancer und Vacuum Supply
10. Vorgaben zur Rollen- und Spleißlogik hinter den HMI-Bedienbefehlen

## 7. Ergebnis

Die HMI-Schnittstelle ist im Controller zentral im Tag `HMI` vom Datentyp `UDT_HMI` gebündelt. In den bereitgestellten Seiten werden ausschließlich Mitglieder dieses Tags für Produktionsbedienung, Handbetrieb, Diagnose, Einstellungen, SPS-Status, Rolleninformationen, Uhrzeit und Stationsmerker verwendet.

Andere Controller-Tags sind für die Beschreibung dieser HMI-Schnittstelle nicht erforderlich und werden in diesem Dokument nicht betrachtet.
