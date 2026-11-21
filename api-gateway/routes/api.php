<?php

use App\Http\Controllers\GatewayController;
use Illuminate\Support\Facades\Route;

/*
| Todas las rutas quedan bajo el prefijo /api (ver bootstrap/app.php):
|   /api/usuarios/*  /api/catalogo/*  /api/inventario/*
|   /api/abastecimiento/*  /api/ventas/*  /api/reportes/*
*/

Route::get('health', [GatewayController::class, 'health']);

Route::any('{service}/{path?}', [GatewayController::class, 'proxy'])
    ->whereIn('service', array_keys(config('gateway.services')))
    ->where('path', '.*')
    ->middleware('jwt');
