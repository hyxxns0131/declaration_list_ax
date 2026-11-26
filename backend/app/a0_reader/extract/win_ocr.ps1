# Windows 기본 OCR(Windows.Media.Ocr)로 이미지의 글자 줄·낱말 위치를 JSON으로 출력한다.
# 새 라이브러리 없이 스캔본의 화주명 위치를 찾기 위함(HS 결정 11/26: 화주명을 가린 PNG만 OpenAI로). 담당: KHS
# 사용: powershell -NoProfile -ExecutionPolicy Bypass -File win_ocr.ps1 -Path <png>
# 출력: {"lines":[{"text":"...","words":[{"text":"..","x":0,"y":0,"w":0,"h":0}]}]}  (글자는 표준 출력으로만, 파일·로그에 남기지 않는다)
param([Parameter(Mandatory = $true)][string]$Path)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType = WindowsRuntime]

$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    })[0]
function Wait-Op($op, [Type]$type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}

$file = Wait-Op ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)) ([Windows.Storage.StorageFile])
$stream = Wait-Op ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Wait-Op ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Wait-Op ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $engine) { throw "OCR 엔진 없음" }
$result = Wait-Op ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$stream.Dispose()

$lines = @()
foreach ($line in $result.Lines) {
    $words = @()
    foreach ($w in $line.Words) {
        $r = $w.BoundingRect
        $words += [ordered]@{ text = $w.Text; x = [int]$r.X; y = [int]$r.Y; w = [int]$r.Width; h = [int]$r.Height }
    }
    $lines += [ordered]@{ text = $line.Text; words = $words }
}
[ordered]@{ lines = $lines } | ConvertTo-Json -Depth 6 -Compress
