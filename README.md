# le-dv-channel

Inoffizieller Update-Kanal für den LibreELEC-Updater, der auf die Releases von
[CroqueMr/libreelec-x86-DV](https://github.com/CroqueMr/libreelec-x86-DV) zeigt
(LibreELEC 13 / Kodi 22 mit Dolby-Vision-Unterstützung, Generic x86_64).

> **Inoffiziell.** Es handelt sich um Beta-Builds. Dieses Repo steht in keiner
> Verbindung zu CroqueMr oder zum LibreELEC-Projekt. Nutzung auf eigenes Risiko.

## Einrichten in LibreELEC

1. *Einstellungen → LibreELEC → Updates*
2. *Benutzerdefinierte Kanäle anzeigen* aktivieren
3. Bei *Benutzerdefinierter Kanal 1* folgende URL eintragen:

   ```
   https://raw.githubusercontent.com/815rx1/le-dv-channel/main/releases.json
   ```

4. Als *Update-Kanal* **`LibreELEC_DV-13.0`** auswählen
5. *Manuelles Update* → gewünschten Build wählen (der oberste ist der neueste)

Die Build-Namen enden auf `.tar`; das ist Absicht (siehe unten).

## Wie es funktioniert

- `releases.json` folgt dem Format von <https://releases.libreelec.tv/releases.json>.
- Die Dateien werden **nicht** kopiert. Der Updater setzt die Download-URL aus
  `url` + `subpath` + `/` + `name` zusammen, also direkt
  `https://github.com/CroqueMr/libreelec-x86-DV/releases/download/<tag>/<datei>.tar`.
  Den Redirect auf `release-assets.githubusercontent.com` folgt der Updater (Python `urllib`) automatisch.
- Verwendet werden nur die Update-Tarballs `LibreELEC-<Projekt>-<Version>-….tar`;
  `*-sources.tar.zst`, `*-vendor-inputs.tar.zst`, `*.tar.part-NN` und `.img.gz` werden ignoriert,
  ebenso die `-debug`-Builds (mit `--include-debug` aufnehmbar).
- Neueste Version = höchster Index, sortiert nach Veröffentlichungsdatum.
- `prettyname_regex` fängt den Namen inklusive `.tar` ein, weil der Updater den Build per
  Teilstring sucht – sonst würde z. B. `…-0.1.0-rc1` auch auf `…-0.1.0-rc1-opt1-diag1.tar` passen.
- Die GitHub Action [`update-releases.yml`](.github/workflows/update-releases.yml) erzeugt
  die Datei täglich und per *Run workflow* neu und committet nur bei Änderungen.

## Lokal ausführen

```bash
python3 generate_releases.py --output releases.json
```

Nur Python-Standardbibliothek; optional `GITHUB_TOKEN` für ein höheres API-Limit.
