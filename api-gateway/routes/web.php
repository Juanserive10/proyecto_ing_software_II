<?php

use Illuminate\Support\Facades\Route;

Route::get('/', fn () => response()->json([
    'service' => 'Distribuidora Andina - API Gateway',
    'docs' => 'Todas las peticiones deben ir a /api/{usuarios|catalogo|inventario|abastecimiento|ventas|reportes}/...',
]));
