$ErrorActionPreference = "Stop"
$renderer = Join-Path $PSScriptRoot "render_cards.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $renderer @args
} else {
    & python $renderer @args
}
exit $LASTEXITCODE
