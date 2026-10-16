# Offline system-boundary tests. All Firewall/service/application inventory calls are mocked.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$guardPath = Join-Path $PSScriptRoot '..\scripts\windows-guard.ps1'
$tokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($guardPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw 'PowerShell syntax errors.' }
$source = Get-Content -LiteralPath $guardPath -Raw -Encoding UTF8
# Replace only the OS administrator boundary in memory; never edit the shipped script.
$admin = $ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq 'Assert-Administrator'}, $true)
$source = $source.Replace($admin.Extent.Text, 'function Assert-Administrator {}')
$underTest = [scriptblock]::Create($source)
$script:rules = @{}
$script:enabled = $true
$script:failOn = 0
$script:createdCount = 0
$script:localRules = 'True'
$script:serviceStatus = 'Running'
$script:profileNames = @('Domain','Public','Private')
$script:effectiveDrift = $false

function Assert($condition, $message) { if (-not $condition) { throw $message } }
function Get-Item { param($LiteralPath)
    [pscustomobject]@{PSIsContainer=$false; Extension='.exe';
        FullName=$LiteralPath; Name=[IO.Path]::GetFileName($LiteralPath)}
}
function Get-NetFirewallProfile { param($PolicyStore)
    foreach ($name in $script:profileNames) {
        [pscustomobject]@{Name=$name; Enabled=$script:enabled; AllowLocalFirewallRules=$script:localRules}
    }
}
function Get-Service { param($Name) [pscustomobject]@{Status=$script:serviceStatus} }
function New-NetFirewallRule {
    param($PolicyStore,$Name,$DisplayName,$Group,$Direction,$Action,$Enabled,$Profile,
          $Program,$Protocol,$RemoteAddress)
    $script:createdCount++
    if ($script:failOn -eq $script:createdCount) { throw 'Injected create failure' }
    Assert ($Action -eq 'Block' -and $Direction -eq 'Outbound' -and $Protocol -eq 'Any') 'Wrong scope.'
    Assert (($RemoteAddress -join ',') -eq '0.0.0.0-126.255.255.255,128.0.0.0-255.255.255.255,::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff') 'Wrong blocked ranges.'
    $script:rules[$Name] = [pscustomobject]@{Name=$Name; Group=$Group; Direction=$Direction;
        Action=$Action; Enabled='True'; Program=$Program; Profile=$Profile; Protocol=$Protocol;
        RemoteAddress=$RemoteAddress; LocalPort='Any'; RemotePort='Any'}
    $script:rules[$Name]
}
function Get-NetFirewallRule { param($PolicyStore,$Name,$ErrorAction)
    if ($script:rules.ContainsKey($Name)) {
        $result = $script:rules[$Name]
        if ($PolicyStore -eq 'ActiveStore' -and $script:effectiveDrift) {
            $result = $result.PSObject.Copy()
            $result.RemoteAddress = @('0.0.0.0-1.1.1.1')
        }
        $result
    }
}
function Get-NetFirewallApplicationFilter {
    param([Parameter(ValueFromPipeline=$true)]$InputObject)
    process { [pscustomobject]@{Program=$InputObject.Program} }
}
function Get-NetFirewallAddressFilter {
    param([Parameter(ValueFromPipeline=$true)]$InputObject)
    process { [pscustomobject]@{RemoteAddress=$InputObject.RemoteAddress} }
}
function Get-NetFirewallPortFilter {
    param([Parameter(ValueFromPipeline=$true)]$InputObject)
    process { [pscustomobject]@{Protocol=$InputObject.Protocol;
        LocalPort=$InputObject.LocalPort; RemotePort=$InputObject.RemotePort} }
}
function Remove-NetFirewallRule {
    param([Parameter(ValueFromPipeline=$true)]$InputObject)
    process { $script:rules.Remove($InputObject.Name) }
}

$work = Join-Path ([IO.Path]::GetTempPath()) ('claude-isolation-test-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($work) | Out-Null
try {
    $programs = @('C:\Fixture\Claude.exe', 'C:\Fixture\ClaudeHelper.exe')
    $script:rules['Unrelated'] = [pscustomobject]@{Name='Unrelated'; Group='Unrelated'}
    $plan = & $underTest -Mode Plan -Program $programs | ConvertFrom-Json
    Assert ($plan.status -eq 'planned_not_applied' -and $script:rules.Count -eq 1) 'Plan mutated rules.'
    $sharedRefused = $false
    try { & $underTest -Mode Plan -Program 'C:\Fixture\node.exe' | Out-Null } catch { $sharedRefused = $true }
    Assert $sharedRefused 'Shared runtime was accepted.'

    $receipt = Join-Path $work 'success.json'
    & $underTest -Mode Apply -Program $programs -Receipt $receipt | Out-Null
    $saved = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    Assert ($saved.status -eq 'applied_fault_tests_pending' -and $script:rules.Count -eq 3) 'Apply failed.'
    $overwriteRefused = $false
    try { & $underTest -Mode Apply -Program $programs -Receipt $receipt | Out-Null } catch { $overwriteRefused=$true }
    Assert $overwriteRefused 'Existing receipt overwritten.'

    $ownName = $saved.rules[0].name
    $script:rules[$ownName].Program = 'C:\Fixture\Other.exe'
    $mismatchRefused = $false
    try { & $underTest -Mode Rollback -Receipt $receipt | Out-Null } catch { $mismatchRefused=$true }
    Assert ($mismatchRefused -and $script:rules.Count -eq 3) 'Rollback ignored changed ownership.'
    $script:rules[$ownName].Program = $saved.rules[0].program
    & $underTest -Mode Rollback -Receipt $receipt | Out-Null
    Assert ($script:rules.Count -eq 1 -and $script:rules.ContainsKey('Unrelated')) 'Unrelated rule removed.'
    & $underTest -Mode Rollback -Receipt $receipt | Out-Null
    Assert ($script:rules.Count -eq 1) 'Second rollback was not safe.'

    $script:enabled = $false
    $disabledRefused = $false
    $disabledReceipt = Join-Path $work 'disabled.json'
    try { & $underTest -Mode Apply -Program $programs -Receipt $disabledReceipt | Out-Null } catch { $disabledRefused=$true }
    Assert ($disabledRefused -and -not (Test-Path -LiteralPath $disabledReceipt)) 'Disabled Firewall accepted.'
    $script:enabled = $true
    $script:localRules = 'False'
    $managedRefused = $false
    try { & $underTest -Mode Apply -Program $programs -Receipt $disabledReceipt | Out-Null } catch { $managedRefused=$true }
    Assert ($managedRefused -and -not (Test-Path -LiteralPath $disabledReceipt)) 'Managed local-rule restriction ignored.'
    $script:localRules = 'True'
    $script:serviceStatus = 'Stopped'
    $serviceRefused = $false
    try { & $underTest -Mode Apply -Program $programs -Receipt $disabledReceipt | Out-Null } catch { $serviceRefused=$true }
    Assert ($serviceRefused -and -not (Test-Path -LiteralPath $disabledReceipt)) 'Stopped services accepted.'
    $script:serviceStatus = 'Running'
    $script:profileNames = @('Public')
    $profileRefused = $false
    try { & $underTest -Mode Apply -Program $programs -Receipt $disabledReceipt | Out-Null } catch { $profileRefused=$true }
    Assert ($profileRefused -and -not (Test-Path -LiteralPath $disabledReceipt)) 'Incomplete profiles accepted.'
    $script:profileNames = @('Domain','Public','Private')
    $script:effectiveDrift = $true
    $driftRefused = $false
    $driftReceipt = Join-Path $work 'drift.json'
    try { & $underTest -Mode Apply -Program $programs -Receipt $driftReceipt | Out-Null } catch { $driftRefused=$true }
    Assert ($driftRefused -and $script:rules.Count -eq 1) 'Effective filter drift was accepted or cleanup failed.'
    $script:effectiveDrift = $false
    $script:createdCount = 0
    $script:failOn = 2
    $failedReceipt = Join-Path $work 'failed.json'
    $partialFailed = $false
    try { & $underTest -Mode Apply -Program $programs -Receipt $failedReceipt | Out-Null } catch { $partialFailed=$true }
    Assert ($partialFailed -and $script:rules.Count -eq 1) 'Partial failure did not clean up its rules.'
    $failed = Get-Content -LiteralPath $failedReceipt -Raw | ConvertFrom-Json
    Assert ($failed.status -eq 'apply_failed_check_partial_cleanup') 'Failure receipt missing.'
    Write-Output 'PASS: syntax, plan, shared-runtime refusal, apply, receipt collision, ownership, rollback, disabled/managed/incomplete profiles, stopped services, effective filter drift, partial failure (mocked OS only).'
} finally {
    # Delete only explicit files created by this test; never recurse over a computed root.
    foreach ($name in @('success.json','failed.json','disabled.json','drift.json')) {
        $path = Join-Path $work $name
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
    }
    [IO.Directory]::Delete($work, $false)
}
