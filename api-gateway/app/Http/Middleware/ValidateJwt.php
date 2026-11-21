<?php

namespace App\Http\Middleware;

use App\Services\JwtValidator;
use Closure;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;

/**
 * Exige un JWT válido (Authorization: Bearer <token>) en todas las rutas
 * del gateway excepto las declaradas en config('gateway.public_routes').
 */
class ValidateJwt
{
    public function __construct(private readonly JwtValidator $validator)
    {
    }

    public function handle(Request $request, Closure $next): Response
    {
        $service = (string) $request->route('service');
        $path = trim((string) $request->route('path'), '/');

        if ($request->isMethod('OPTIONS') || $this->isPublic($service, $path)) {
            return $next($request);
        }

        $token = $request->bearerToken();
        if (! $token) {
            return $this->unauthorized('Token Bearer requerido');
        }

        try {
            $payload = $this->validator->validate($token);
        } catch (ConnectionException) {
            return response()->json(
                ['error' => 'No fue posible validar el token: usuarios-service no disponible'],
                503,
            );
        }

        if ($payload === null) {
            return $this->unauthorized('Token inválido o expirado');
        }

        $request->attributes->set('jwt_payload', $payload);

        return $next($request);
    }

    private function isPublic(string $service, string $path): bool
    {
        $rules = config('gateway.public_routes');
        $patterns = array_merge($rules['*'] ?? [], $rules[$service] ?? []);

        return Str::is($patterns, $path);
    }

    private function unauthorized(string $message): Response
    {
        return response()
            ->json(['error' => $message], 401)
            ->header('WWW-Authenticate', 'Bearer');
    }
}
