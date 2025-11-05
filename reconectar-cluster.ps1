#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script de reconexión rápida al cluster EKS

.DESCRIPTION
    Este script te guía paso a paso para reconectarte al cluster de Kubernetes
    después de reiniciar el lab de AWS Academy.

.EXAMPLE
    .\reconectar-cluster.ps1
#>

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  🔄 RECONEXIÓN AL CLUSTER EKS" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar herramientas
Write-Host "0. Verificando herramientas instaladas..." -ForegroundColor Yellow
$tools = @("aws", "kubectl")
$missing = @()

foreach ($tool in $tools) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        $missing += $tool
    }
}

if ($missing.Count -gt 0) {
    Write-Host "   ❌ Faltan herramientas: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "   Instala las herramientas necesarias primero`n" -ForegroundColor Yellow
    exit 1
}
Write-Host "   ✅ Todas las herramientas instaladas`n" -ForegroundColor Green

# Paso 1: Verificar credenciales
Write-Host "1. Verificando credenciales de AWS..." -ForegroundColor Yellow

try {
    $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
    
    if ($identity) {
        Write-Host "   ✅ Credenciales válidas" -ForegroundColor Green
        Write-Host "   Usuario: $($identity.Arn)`n" -ForegroundColor Gray
    } else {
        throw "No identity"
    }
} catch {
    Write-Host "   ❌ Credenciales no válidas o expiradas`n" -ForegroundColor Red
    Write-Host "NECESITAS ACTUALIZAR LAS CREDENCIALES:" -ForegroundColor Yellow
    Write-Host "`n1. Ve a AWS Academy" -ForegroundColor White
    Write-Host "2. Inicia el Lab (Start Lab)" -ForegroundColor White
    Write-Host "3. Espera a que esté verde 🟢" -ForegroundColor White
    Write-Host "4. Click en 'AWS Details'" -ForegroundColor White
    Write-Host "5. Click en 'Show' junto a AWS CLI" -ForegroundColor White
    Write-Host "6. Copia TODO el contenido`n" -ForegroundColor White
    
    Write-Host "¿Has copiado las credenciales? (presiona Enter cuando estés listo)" -ForegroundColor Cyan
    Read-Host
    
    Write-Host "`nAbriendo archivo de credenciales..." -ForegroundColor Yellow
    $credFile = "$env:USERPROFILE\.aws\credentials"
    
    # Crear directorio si no existe
    $awsDir = Split-Path $credFile
    if (-not (Test-Path $awsDir)) {
        New-Item -ItemType Directory -Path $awsDir -Force | Out-Null
    }
    
    # Abrir en notepad
    Start-Process notepad $credFile -Wait
    
    Write-Host "Verificando nuevamente..." -ForegroundColor Yellow
    try {
        $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
        if ($identity) {
            Write-Host "   ✅ Credenciales actualizadas correctamente`n" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Las credenciales siguen sin funcionar" -ForegroundColor Red
            Write-Host "   Verifica que hayas pegado correctamente el contenido`n" -ForegroundColor Yellow
            exit 1
        }
    } catch {
        Write-Host "   ❌ Error verificando credenciales`n" -ForegroundColor Red
        exit 1
    }
}

# Paso 2: Reconectar kubectl
Write-Host "2. Reconectando kubectl al cluster..." -ForegroundColor Yellow

try {
    aws eks update-kubeconfig --name bookstore-eks --region us-east-1 2>$null | Out-Null
    Write-Host "   ✅ kubectl configurado`n" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Error configurando kubectl" -ForegroundColor Red
    Write-Host "   Verifica que el cluster 'bookstore-eks' existe`n" -ForegroundColor Yellow
    exit 1
}

# Paso 3: Verificar conexión
Write-Host "3. Verificando conexión al cluster..." -ForegroundColor Yellow

try {
    $nodes = kubectl get nodes 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Conectado al cluster`n" -ForegroundColor Green
        Write-Host "Nodos del cluster:" -ForegroundColor Cyan
        kubectl get nodes
        Write-Host ""
    } else {
        throw "Cannot connect"
    }
} catch {
    Write-Host "   ❌ No se pudo conectar al cluster" -ForegroundColor Red
    Write-Host "   Verifica que el lab esté iniciado`n" -ForegroundColor Yellow
    exit 1
}

# Paso 4: Ver estado de los pods
Write-Host "4. Verificando estado de los servicios..." -ForegroundColor Yellow

$pods = kubectl get pods -n bookstore 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Servicios accesibles`n" -ForegroundColor Green
    Write-Host "Estado de los pods:" -ForegroundColor Cyan
    kubectl get pods -n bookstore
    Write-Host ""
} else {
    Write-Host "   ⚠️  No se pudieron ver los pods" -ForegroundColor Yellow
    Write-Host "   El cluster puede estar iniciándose`n" -ForegroundColor Gray
}

# Paso 5: Preguntar si quiere actualizar IP del frontend
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ⚠️  ACTUALIZACIÓN DE IP" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "La IP pública del cluster cambia cada vez que reinicias el lab." -ForegroundColor White
Write-Host "Necesitas actualizar el frontend con la nueva IP.`n" -ForegroundColor White

$response = Read-Host "¿Quieres actualizar la IP del frontend ahora? (s/N)"

if ($response -eq "s" -or $response -eq "S" -or $response -eq "si" -or $response -eq "SI") {
    Write-Host ""
    
    # Verificar que existe el script
    if (Test-Path "update-frontend-ip.ps1") {
        $dockerUser = Read-Host "Ingresa tu usuario de Docker Hub"
        
        if ($dockerUser) {
            Write-Host "`nEjecutando actualización de IP..." -ForegroundColor Cyan
            Write-Host "Esto tomará 5-8 minutos...`n" -ForegroundColor Yellow
            
            & .\update-frontend-ip.ps1 -DockerUsername $dockerUser
        } else {
            Write-Host "   ⚠️  Usuario no proporcionado, saltando actualización`n" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ❌ Script update-frontend-ip.ps1 no encontrado" -ForegroundColor Red
        Write-Host "   Actualiza manualmente después`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n   ⚠️  Recuerda actualizar la IP más tarde con:" -ForegroundColor Yellow
    Write-Host "   .\update-frontend-ip.ps1 -DockerUsername `"tu-usuario`"`n" -ForegroundColor Cyan
}

# Resumen final
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ✅ RECONEXIÓN COMPLETADA" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Estado del cluster:" -ForegroundColor Yellow
Write-Host "  ✅ Credenciales: Válidas" -ForegroundColor Green
Write-Host "  ✅ kubectl: Conectado" -ForegroundColor Green
Write-Host "  ✅ Cluster: Accesible`n" -ForegroundColor Green

Write-Host "Comandos útiles:" -ForegroundColor Yellow
Write-Host "  kubectl get pods -n bookstore" -ForegroundColor Cyan
Write-Host "  kubectl get services -n bookstore" -ForegroundColor Cyan
Write-Host "  kubectl logs -n bookstore deployment/[SERVICE]`n" -ForegroundColor Cyan

Write-Host "Para ver la URL del frontend:" -ForegroundColor Yellow
Write-Host "  kubectl get service frontend -n bookstore`n" -ForegroundColor Cyan

Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "¡Listo para trabajar! 🚀`n" -ForegroundColor Green

