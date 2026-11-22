<?php

/*
|--------------------------------------------------------------------------
| API Gateway - Distribuidora Andina (RNF09)
|--------------------------------------------------------------------------
|
| Toda petición externa entra por /api/{servicio}/{ruta} y se reenvía al
| microservicio interno correspondiente. Las URLs internas usan los nombres
| DNS de la red de Docker Compose, por lo que los puertos 5001-5006 nunca
| se exponen al navegador.
|
*/

return [

    'services' => [
        'usuarios' => env('USUARIOS_SERVICE_URL', 'http://usuarios-service:5001'),
        'catalogo' => env('CATALOGO_SERVICE_URL', 'http://catalogo-service:5002'),
        'inventario' => env('INVENTARIO_SERVICE_URL', 'http://inventario-service:5003'),
        'abastecimiento' => env('ABASTECIMIENTO_SERVICE_URL', 'http://abastecimiento-service:5004'),
        'ventas' => env('VENTAS_SERVICE_URL', 'http://ventas-service:5005'),
        'reportes' => env('REPORTES_SERVICE_URL', 'http://reportes-service:5006'),
    ],

    'jwt' => [
        // local  -> valida firma HS256 y expiración con JWT_SECRET (sin salto de red).
        // remote -> delega la validación en POST {usuarios}/auth/verify.
        'mode' => env('JWT_VERIFY_MODE', 'local'),
        'secret' => env('JWT_SECRET'),
        'algorithm' => 'HS256',
        'leeway' => (int) env('JWT_LEEWAY', 30),
        'verify_url' => env('JWT_VERIFY_URL', 'http://usuarios-service:5001/auth/verify'),
    ],

    /*
    | Rutas que no requieren JWT, como "servicio" => [patrones de ruta].
    | Los patrones usan la sintaxis de Str::is() ("*" como comodín).
    */
    'public_routes' => [
        '*' => ['health'],
        'usuarios' => [
            'auth/login',
            'auth/register',
            'auth/verify',
            'auth/forgot-password',
            'auth/reset-password',
        ],
    ],

    'timeout' => (int) env('GATEWAY_UPSTREAM_TIMEOUT', 30),
    'connect_timeout' => (int) env('GATEWAY_CONNECT_TIMEOUT', 5),

];
