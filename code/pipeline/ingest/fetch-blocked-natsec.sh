#!/usr/bin/env bash
# Fetch the W8b natsec sources the EC2 box could not get (results/SOURCES-BLOCKED-2026-10-28.md).
# Run on your own laptop (macOS or Linux; needs bash + curl). The blocks are bot protection on the hosts
# (Cloudflare 402 at globalsecurity, Akamai 403 at centcom/dtic, dfat timing out from AWS), which typically
# rejects datacenter IPs. From a home connection a plain request usually goes through.
#
# Access rule (W8b): no user-agent spoofing, no workarounds. This script sends the same honest User-Agent the
# box uses. If a host still refuses it, the script opens that URL in your normal browser so you can save
# the file by hand (File > Save / the PDF download button) into the output folder under the name it prints.
#
#   bash fetch-blocked-natsec.sh            # writes ./benchbook-manual/ + manifest.tsv
#   bash fetch-blocked-natsec.sh --no-open  # don't open a browser for failures, just list them
#
# Then copy the folder to the box and register it:
#   scp -r benchbook-manual/* ubuntu@<box>:benchbook-labs/data/raw/manual/
#   (on the box) PYTHONPATH=code .venv/bin/python -m pipeline.ingest.natsec ingest-manual
set -u

OUT="benchbook-manual"
OPEN=1
[ "${1:-}" = "--no-open" ] && OPEN=0
UA="benchbook-labs-research/0.1 (academic research on public decision records)"
mkdir -p "$OUT"
MANIFEST="$OUT/manifest.tsv"
[ -f "$MANIFEST" ] || printf 'source_id\turl\tfile\n' > "$MANIFEST"
FAILED=""

open_url() {
  [ "$OPEN" = 1 ] || return 0
  if command -v open >/dev/null 2>&1; then open "$1"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1
  fi
}

# looks_ok FILE KIND: KIND=pdf needs the %PDF magic; KIND=html must not be a bot-challenge/denied page.
looks_ok() {
  [ -s "$1" ] || return 1
  if [ "$2" = pdf ]; then
    [ "$(head -c 4 "$1")" = "%PDF" ]
  else
    ! grep -qiE 'just a moment|cf-chl|challenge-platform|access denied|request rejected' "$1"
  fi
}

# get ID URL FILE KIND
get() {
  local id="$1" url="$2" file="$3" kind="$4" code
  if [ -f "$OUT/$file" ] && looks_ok "$OUT/$file" "$kind"; then
    echo "have    $id  $file"; return 0
  fi
  code=$(curl -sS -L --max-time 300 --retry 2 -A "$UA" -o "$OUT/$file" -w '%{http_code}' "$url" 2>/dev/null)
  if [ "$code" = 200 ] && looks_ok "$OUT/$file" "$kind"; then
    echo "ok      $id  $file ($(wc -c < "$OUT/$file" | tr -d ' ') bytes)"
    grep -qF "	$file" "$MANIFEST" || printf '%s\t%s\t%s\n' "$id" "$url" "$file" >> "$MANIFEST"
    return 0
  fi
  rm -f "$OUT/$file"
  echo "BLOCKED $id  HTTP ${code:-none}  -> save by hand as $OUT/$file"
  FAILED="$FAILED
  $id  $url  ->  $OUT/$file"
  open_url "$url"
  return 1
}

# 1. Bucknam, Responsibility of Command (DTIC)
get BUCKNAM-2003 "https://apps.dtic.mil/sti/pdfs/ADA415991.pdf" "BUCKNAM-2003_ADA415991.pdf" pdf

# 2. Mosul al-Jadida AR 15-6 executive summary (CENTCOM news page)
get MOSUL-2017 "https://www.centcom.mil/MEDIA/NEWS-ARTICLES/News-Article-View/Article/1193707/executive-summary-of-the-investigation-of-the-alleged-civilian-casualty-inciden/" \
  "MOSUL-2017_centcom-1193707.html" html

# 3. WCK convoy strike, Binskin public report (DFAT); large and slow
get WCK-2024 "https://www.dfat.gov.au/sites/default/files/special-advisers-public-report-israels-response-wck-strikes-august-2024.pdf" \
  "WCK-2024_binskin-public-report.pdf" pdf

# 4. Tarnak Farm Board of Inquiry (globalsecurity, multi-page: contents page + tarmak_fr-N_e.htm parts)
BASE="https://www.globalsecurity.org/military/library/report/2002"
if get TARNAK-2002 "$BASE/tarmak_content_e.htm" "TARNAK-2002_tarmak_content_e.htm" html; then
  for page in $(grep -oE 'tarmak_fr-[0-9]+_e\.htm' "$OUT/TARNAK-2002_tarmak_content_e.htm" | sort -u -t- -k2,2n); do
    sleep 1.5
    get TARNAK-2002 "$BASE/$page" "TARNAK-2002_$page" html || break   # one challenge = the rest will be too
  done
fi

echo
if [ -n "$FAILED" ]; then
  echo "Still missing (save these from the browser windows that opened, using exactly these names):$FAILED"
  echo "For hand-saved files, add a line to $MANIFEST:  <source_id><TAB><url><TAB><file>"
  echo "Tarnak: if the contents page saved but the parts did not, save each tarmak_fr-N_e.htm as TARNAK-2002_tarmak_fr-N_e.htm."
else
  echo "All fetched. Copy $OUT/ to the box (see the header of this script)."
fi
