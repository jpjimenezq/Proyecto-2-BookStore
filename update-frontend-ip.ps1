#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Actualiza la IP del Gateway en el frontend después de reiniciar AWS Academy Lab

.DESCRIPTION
    Este script:
    1. Obtiene la nueva IP del Gateway NodePort
    2. Actualiza el archivo client.js del frontend
    3. Reconstruye y sube la imagen del frontend
    4. Actualiza el deployment en EKS

.PARAMETER DockerUsername
    Tu usuario de Docker Hub (requerido)

.EXAMPLE
    .\update-frontend-ip.ps1 -DockerUsername "henao13"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$DockerUsername
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  🔄 ACTUALIZADOR DE IP DEL FRONTEND" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Obtener la nueva IP del Gateway
Write-Host "1. Obteniendo nueva IP del Gateway..." -ForegroundColor Yellow
$gatewayInfo = kubectl get service gateway -n bookstore -o json | ConvertFrom-Json

if ($gatewayInfo.spec.type -eq "NodePort") {
    $nodePort = $gatewayInfo.spec.ports[0].nodePort
    Write-Host "   NodePort detectado: $nodePort" -ForegroundColor Cyan
    
    # Obtener IP pública del nodo
    $nodeName = (kubectl get pods -n bookstore -l app=gateway -o jsonpath='{.items[0].spec.nodeName}')
    $nodeIP = (kubectl get node $nodeName -o jsonpath='{.status.addresses[?(@.type=="ExternalIP")].address}')
    
    if (-not $nodeIP) {
        Write-Host "   ⚠️  No se encontró IP externa, intentando obtener del AWS..." -ForegroundColor Yellow
        # Intentar obtener del Load Balancer de EKS
        $nodeIP = (kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
    }
    
    $newGatewayURL = "http://${nodeIP}:${nodePort}"
    Write-Host "   ✅ Nueva URL del Gateway: $newGatewayURL`n" -ForegroundColor Green
} else {
    Write-Host "   ❌ Error: Gateway no es tipo NodePort" -ForegroundColor Red
    exit 1
}

# Step 2: Actualizar client.js
Write-Host "2. Actualizando archivo client.js..." -ForegroundColor Yellow
$clientJsPath = "services/frontend/src/api/client.js"

if (-not (Test-Path $clientJsPath)) {
    Write-Host "   ❌ Error: No se encuentra $clientJsPath" -ForegroundColor Red
    exit 1
}

$content = Get-Content $clientJsPath -Raw

# Buscar y reemplazar la URL del API
if ($content -match "const API_URL = ['""]http://[^'""]+['""]") {
    $content = $content -replace "const API_URL = ['""]http://[^'""]+['""]", "const API_URL = '$newGatewayURL'"
    Set-Content -Path $clientJsPath -Value $content -NoNewline
    Write-Host "   ✅ client.js actualizado con nueva IP`n" -ForegroundColor Green
} else {
    Write-Host "   ❌ Error: No se encontró la línea API_URL en client.js" -ForegroundColor Red
    exit 1
}

# Step 3: Reconstruir imagen del frontend
Write-Host "3. Reconstruyendo imagen del frontend..." -ForegroundColor Yellow
Push-Location services/frontend
docker build -t "${DockerUsername}/bookstore-frontend:latest" . 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Imagen construida exitosamente`n" -ForegroundColor Green
} else {
    Write-Host "   ❌ Error al construir la imagen" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Step 4: Subir imagen a Docker Hub
Write-Host "4. Subiendo imagen a Docker Hub..." -ForegroundColor Yellow
docker push "${DockerUsername}/bookstore-frontend:latest" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Imagen subida exitosamente`n" -ForegroundColor Green
} else {
    Write-Host "   ❌ Error al subir la imagen" -ForegroundColor Red
    exit 1
}

# Step 5: Reiniciar deployment del frontend
Write-Host "5. Reiniciando frontend en EKS..." -ForegroundColor Yellow
kubectl rollout restart deployment/frontend -n bookstore | Out-Null
kubectl rollout status deployment/frontend -n bookstore --timeout=120s | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Frontend reiniciado exitosamente`n" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Reinicio en progreso...`n" -ForegroundColor Yellow
}

# Step 6: Obtener la nueva URL del frontend
Write-Host "6. Obteniendo URL del frontend..." -ForegroundColor Yellow
$frontendInfo = kubectl get service frontend -n bookstore -o json | ConvertFrom-Json
$frontendPort = $frontendInfo.spec.ports[0].nodePort
$frontendURL = "http://${nodeIP}:${frontendPort}"

# Resumen final
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ✅ ACTUALIZACIÓN COMPLETA" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "NUEVA CONFIGURACIÓN:" -ForegroundColor Yellow
Write-Host "  Gateway:  $newGatewayURL" -ForegroundColor Cyan
Write-Host "  Frontend: $frontendURL`n" -ForegroundColor Cyan

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ABRE EN TU NAVEGADOR:" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "  $frontendURL`n" -ForegroundColor Green

Write-Host "NOTA: Espera 1-2 minutos para que el pod se actualice completamente.`n" -ForegroundColor Yellow
Write-Host "Puedes verificar con: kubectl get pods -n bookstore -l app=frontend`n" -ForegroundColor Gray

