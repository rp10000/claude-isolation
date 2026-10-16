#requires -Version 5.1
<#
.SYNOPSIS
Create receipt-owned per-program non-loopback outbound block rules.
.DESCRIPTION
Does not enable Firewall or alter inbound rules. Loopback is excluded from these
blocks; existing policy can still deny it. Review references/windows.md first.
.EXAMPLE
./windows-guard.ps1 -Mode Plan -Program C:\Apps\Claude\claude.exe
#>
[CmdletBinding()]
param(
    [ValidateSet('Plan', 'Apply', 'Rollback')][string]$Mode = 'Plan',
    [string[]]$Program = @(),
    [string]$Receipt
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$guardGroup = 'ClaudeIsolation-v1'
$blockedRanges = @('0.0.0.0-126.255.255.255', '128.0.0.0-255.255.255.255',
                   '::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Apply/Rollback requires an administrator PowerShell.'
    }
}

function Save-Receipt($Value, [string]$Path) {
    $json = $Value | ConvertTo-Json -Depth 12
    [IO.File]::WriteAllText($Path, $json, (New-Object Text.UTF8Encoding($false)))
}

function Canonical-Addresses($Addresses) {
    $values = foreach ($address in $Addresses) {
        $parts = foreach ($part in ([string]$address -split '-')) {
            ([Net.IPAddress]::Parse($part)).ToString()
        }
        $parts -join '-'
    }
    (@($values | Sort-Object) -join ',')
}

function Assert-GuardRule($Rule, [string]$ExpectedProgram) {
    if ([string]$Rule.Enabled -ne 'True' -or [string]$Rule.Action -ne 'Block' -or
        [string]$Rule.Direction -ne 'Outbound' -or [string]$Rule.Profile -notin @('Any','0')) {
        throw 'Effective rule flags differ from the plan.'
    }
    $application = $Rule | Get-NetFirewallApplicationFilter
    $address = $Rule | Get-NetFirewallAddressFilter
    $port = $Rule | Get-NetFirewallPortFilter
    if ($application.Program -ne $ExpectedProgram -or
        (Canonical-Addresses $address.RemoteAddress) -ne (Canonical-Addresses $blockedRanges) -or
        [string]$port.Protocol -notin @('Any','256') -or
        [string]$port.LocalPort -ne 'Any' -or [string]$port.RemotePort -ne 'Any') {
        throw 'Effective program/address/protocol/port filter differs from the plan.'
    }
}

if ($Mode -eq 'Rollback') {
    Assert-Administrator
    if (-not $Receipt) { throw 'Supply the private receipt path.' }
    $saved = Get-Content -LiteralPath $Receipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($saved.schema -ne 1 -or $saved.group -ne $guardGroup -or
        $saved.id -notmatch '^ClaudeIsolation-[a-f0-9]{32}$' -or
        @($saved.rules).Count -eq 0) { throw 'Unrecognized receipt.' }
    # Validate every target before removing any rule. Never delete by group alone.
    $targets = @()
    foreach ($entry in $saved.rules) {
        if ($entry.name -notmatch ('^' + [regex]::Escape($saved.id) + '-[0-9]+$')) {
            throw 'Invalid rule identity in receipt.'
        }
        $existing = @(Get-NetFirewallRule -PolicyStore PersistentStore -Name $entry.name -ErrorAction SilentlyContinue)
        if ($existing.Count -eq 0) { continue }
        if ($existing.Count -ne 1 -or $existing[0].Group -ne $guardGroup -or
            [string]$existing[0].Direction -ne 'Outbound' -or
            [string]$existing[0].Action -ne 'Block') { throw 'Rule changed; review before rollback.' }
        $app = $existing[0] | Get-NetFirewallApplicationFilter
        if ($app.Program -ne $entry.program) { throw 'Program mismatch; review before rollback.' }
        Assert-GuardRule $existing[0] $entry.program
        $targets += $existing[0]
    }
    foreach ($target in $targets) { $target | Remove-NetFirewallRule }
    $saved.status = 'rolled_back'
    Save-Receipt $saved ([IO.Path]::GetFullPath($Receipt))
    Write-Output 'Only receipt-owned outbound rules removed. Recheck effective policy.'
    return
}

if ($Program.Count -eq 0) { throw 'Supply explicit dedicated executable paths using -Program.' }
$resolvedPrograms = @()
foreach ($candidate in $Program) {
    $item = Get-Item -LiteralPath $candidate
    if ($item.PSIsContainer -or $item.Extension -ne '.exe' -or
        $item.FullName.StartsWith('\\')) { throw 'Use a local executable file, not a folder or network path.' }
    if ($item.Name -match '^(node|python(?:w|[0-9.]*)?|powershell|pwsh|cmd|wscript|cscript|chrome|msedge|firefox|v2rayN|xray|sing-box|mihomo)\.exe$') {
        throw 'Shared runtime/browser/proxy core refused. Isolate a dedicated client instead.'
    }
    $resolvedPrograms += $item.FullName
}
$resolvedPrograms = @($resolvedPrograms | Sort-Object -Unique)
$runId = 'ClaudeIsolation-' + [guid]::NewGuid().ToString('N')
$index = 0
$rules = @($resolvedPrograms | ForEach-Object {
    $index++
    [ordered]@{name = "$runId-$index"; program = $_}
})
$plan = [ordered]@{schema = 1; id = $runId; group = $guardGroup;
    status = 'planned_not_applied'; remoteAddress = $blockedRanges; rules = $rules}
if ($Mode -eq 'Plan') {
    $plan | ConvertTo-Json -Depth 12
    return
}

Assert-Administrator
if (-not $Receipt) { throw 'Apply requires a new private -Receipt file path.' }
$receiptPath = [IO.Path]::GetFullPath($Receipt)
if (Test-Path -LiteralPath $receiptPath) { throw 'Receipt exists; never overwrite rollback evidence.' }
if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($receiptPath)) -PathType Container)) {
    throw 'Receipt parent directory must already exist.'
}
$profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore)
if ($profiles.Count -ne 3 -or @($profiles | Where-Object { -not $_.Enabled }).Count -gt 0) {
    throw 'All Firewall profiles must already be enabled. No global change has been made.'
}
if (@($profiles | Where-Object { [string]$_.AllowLocalFirewallRules -eq 'False' }).Count -gt 0) {
    throw 'Managed policy disallows local rules; use the administrator-managed policy path.'
}
if ((Get-Service -Name MpsSvc).Status -ne 'Running' -or (Get-Service -Name BFE).Status -ne 'Running') {
    throw 'Firewall/filter services are unavailable.'
}
# Reserve receipt before creating any rule, so partial application remains recoverable.
$reserve = [IO.File]::Open($receiptPath, 'CreateNew', 'Write', 'None')
$reserve.Dispose()
$created = @()
try {
    $plan.status = 'applying'
    Save-Receipt $plan $receiptPath
    foreach ($entry in $rules) {
        New-NetFirewallRule -PolicyStore PersistentStore -Name $entry.name -DisplayName $entry.name `
            -Group $guardGroup -Direction Outbound -Action Block -Enabled True -Profile Any `
            -Program $entry.program -Protocol Any -RemoteAddress $blockedRanges | Out-Null
        $created += $entry.name
    }
    foreach ($entry in $rules) {
        $active = @(Get-NetFirewallRule -PolicyStore ActiveStore -Name $entry.name)
        if ($active.Count -ne 1 -or [string]$active[0].Enabled -ne 'True' -or
            [string]$active[0].Action -ne 'Block') { throw 'Rule is not active.' }
        Assert-GuardRule $active[0] $entry.program
    }
    $plan.status = 'applied_fault_tests_pending'
    Save-Receipt $plan $receiptPath
    Write-Output 'Non-loopback guard filters verified; loopback excluded from these blocks. Fault tests pending.'
} catch {
    $failure = $_
    foreach ($name in $created) {
        Get-NetFirewallRule -PolicyStore PersistentStore -Name $name -ErrorAction SilentlyContinue |
            Remove-NetFirewallRule -ErrorAction Continue
    }
    $plan.status = 'apply_failed_check_partial_cleanup'
    Save-Receipt $plan $receiptPath
    throw $failure
}
