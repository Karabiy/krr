# Detect Kubernetes Node Instance Types
# PowerShell script for Windows users

Write-Host "=== Kubernetes Node Instance Types ===" -ForegroundColor Cyan
Write-Host ""

# Check if kubectl is available
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "Error: kubectl is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Function to get instance type from various labels
function Get-InstanceType {
    param($labels)
    
    # Try different label patterns
    $instanceType = $labels."node.kubernetes.io/instance-type"
    if (-not $instanceType) {
        $instanceType = $labels."beta.kubernetes.io/instance-type"
    }
    if (-not $instanceType) {
        $instanceType = "not found"
    }
    
    return $instanceType
}

# Get all nodes
try {
    $nodes = kubectl get nodes -o json | ConvertFrom-Json
    
    if ($nodes.items.Count -eq 0) {
        Write-Host "No nodes found in the cluster" -ForegroundColor Yellow
        exit 0
    }
    
    # Summary table
    $nodeInfo = @()
    
    foreach ($node in $nodes.items) {
        $name = $node.metadata.name
        $labels = $node.metadata.labels
        $instanceType = Get-InstanceType -labels $labels
        $region = $labels."topology.kubernetes.io/region"
        $zone = $labels."topology.kubernetes.io/zone"
        $providerID = $node.spec.providerID
        
        # Cloud-specific labels
        $eksNodegroup = $labels."eks.amazonaws.com/nodegroup"
        $aksAgentpool = $labels."agentpool"
        $gkeNodepool = $labels."cloud.google.com/gke-nodepool"
        
        # Determine cloud provider
        $cloudProvider = "Unknown"
        if ($providerID -like "aws:*") {
            $cloudProvider = "AWS"
        } elseif ($providerID -like "azure:*") {
            $cloudProvider = "Azure"
        } elseif ($providerID -like "gce:*") {
            $cloudProvider = "GCP"
        }
        
        $nodeInfo += [PSCustomObject]@{
            Name = $name
            InstanceType = $instanceType
            CloudProvider = $cloudProvider
            Region = if ($region) { $region } else { "N/A" }
            Zone = if ($zone) { $zone } else { "N/A" }
        }
        
        # Detailed output
        Write-Host "Node: $name" -ForegroundColor Green
        Write-Host "  Instance Type: " -NoNewline
        if ($instanceType -eq "not found") {
            Write-Host $instanceType -ForegroundColor Red
        } else {
            Write-Host $instanceType -ForegroundColor Yellow
        }
        Write-Host "  Cloud Provider: $cloudProvider"
        Write-Host "  Region/Zone: $region/$zone"
        
        if ($eksNodegroup) {
            Write-Host "  EKS Node Group: $eksNodegroup" -ForegroundColor Cyan
        }
        if ($aksAgentpool) {
            Write-Host "  AKS Agent Pool: $aksAgentpool" -ForegroundColor Cyan
        }
        if ($gkeNodepool) {
            Write-Host "  GKE Node Pool: $gkeNodepool" -ForegroundColor Cyan
        }
        
        Write-Host ""
    }
    
    # Summary
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    $nodeInfo | Format-Table -AutoSize
    
    # Check for missing instance types
    $missingCount = ($nodeInfo | Where-Object { $_.InstanceType -eq "not found" }).Count
    if ($missingCount -gt 0) {
        Write-Host ""
        Write-Host "WARNING: $missingCount node(s) missing instance type labels!" -ForegroundColor Yellow
        Write-Host "To fix, run:" -ForegroundColor Yellow
        Write-Host 'kubectl label nodes <node-name> node.kubernetes.io/instance-type=<instance-type>' -ForegroundColor Gray
    }
    
} catch {
    Write-Host "Error: Failed to get node information" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Export to CSV option
Write-Host ""
$export = Read-Host "Export to CSV? (y/N)"
if ($export -eq 'y' -or $export -eq 'Y') {
    $filename = "node-instance-types-$(Get-Date -Format 'yyyyMMdd-HHmmss').csv"
    $nodeInfo | Export-Csv -Path $filename -NoTypeInformation
    Write-Host "Exported to: $filename" -ForegroundColor Green
} 