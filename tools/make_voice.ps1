# Synthesize the learner's narration (video/narration.json) with a Windows voice.
# One WAV per section in video/voice/, plus durations.json (seconds).
# Usage: powershell -ExecutionPolicy Bypass -File tools/make_voice.ps1
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$root = Split-Path -Parent $PSScriptRoot
$cfg = Get-Content -Raw -Encoding UTF8 (Join-Path $root "video/narration.json") | ConvertFrom-Json
$outDir = Join-Path $root "video/voice"
New-Item -ItemType Directory -Force $outDir | Out-Null

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($cfg.voice)
$synth.Rate = 1        # slightly brisk, friendlier pace
$synth.Volume = 100

$durations = @{}
foreach ($s in $cfg.sections) {
    $text = $s.text
    # Pronunciation only: longest keys first so "parasites/µL" wins over "µL".
    $keys = $cfg.pronunciation.PSObject.Properties.Name | Sort-Object { -$_.Length }
    foreach ($k in $keys) { $text = $text.Replace($k, $cfg.pronunciation.$k) }
    $wav = Join-Path $outDir ($s.id + ".wav")
    $synth.SetOutputToWaveFile($wav, (New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)))
    $synth.Speak($text)
    $synth.SetOutputToNull()
    $bytes = (Get-Item $wav).Length - 44
    $durations[$s.id] = [math]::Round($bytes / (44100 * 2), 2)
}
$synth.Dispose()
$durations | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $outDir "durations.json")
$durations | ConvertTo-Json
