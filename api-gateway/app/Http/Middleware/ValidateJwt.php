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

        if (! $this->isAuthorizedForRole($request, $service, $path, $payload)) {
            $rol = (string) ($payload['rol'] ?? 'DESCONOCIDO');

            return response()->json(
                ['error' => "Permisos insuficientes para el rol $rol en $service/$path"],
                403,
            );
        }

        $request->attributes->set('jwt_payload', $payload);

        return $next($request);
    }

    private function isAuthorizedForRole(Request $request, string $service, string $path, array $payload): bool
    {
        if (in_array($request->method(), ['GET', 'HEAD'], true)) {
            return true;
        }

        $rol = (string) ($payload['rol'] ?? '');
        if ($rol === 'ADMINISTRADOR') {
            return true;
        }

        $rules = config("gateway.write_roles.$service", []);
        foreach ($rules as $pattern => $allowedRoles) {
            if (Str::is($pattern, $path)) {
                return in_array($rol, $allowedRoles, true);
            }
        }

        return false;
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
