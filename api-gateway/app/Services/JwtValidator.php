<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

/**
 * Valida tokens JWT emitidos por usuarios-service.
 *
 * Modo "local": verifica firma HS256 (HMAC-SHA256, comparación en tiempo
 * constante) y los claims exp/nbf/iat con el secreto compartido. Se implementa
 * directamente porque firebase/php-jwt v7 rechaza secretos < 32 bytes y el
 * JWT_SECRET actual del equipo tiene 28.
 * Modo "remote": delega en POST /auth/verify de usuarios-service.
 *
 * Como en modo local el gateway no conoce la lista de tokens revocados de
 * usuarios-service, mantiene su propia lista negra (alimentada cuando un
 * logout pasa por el gateway) en la caché compartida entre workers.
 */
class JwtValidator
{
    private const REVOKED_PREFIX = 'jwt:revoked:';

    /**
     * Devuelve el payload del token o null si no es válido.
     *
     * @throws ConnectionException si el modo es remoto y usuarios-service no responde.
     */
    public function validate(string $token): ?array
    {
        if ($this->isRevoked($token)) {
            return null;
        }

        return config('gateway.jwt.mode') === 'remote'
            ? $this->validateRemote($token)
            : $this->validateLocal($token);
    }

    public function revoke(string $token): void
    {
        $payload = $this->decodeWithoutVerification($token);
        $ttl = isset($payload['exp']) ? max(60, (int) $payload['exp'] - time()) : 12 * 3600;

        Cache::put(self::REVOKED_PREFIX.hash('sha256', $token), true, $ttl);
    }

    private function isRevoked(string $token): bool
    {
        return Cache::has(self::REVOKED_PREFIX.hash('sha256', $token));
    }

    private function validateLocal(string $token): ?array
    {
        $secret = (string) config('gateway.jwt.secret');
        if ($secret === '') {
            throw new \RuntimeException('JWT_SECRET no está configurado en el gateway');
        }

        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        [$encodedHeader, $encodedPayload, $encodedSignature] = $parts;

        $header = json_decode($this->base64UrlDecode($encodedHeader), true);
        // Solo se acepta el algoritmo configurado (evita "alg": "none" o confusión de algoritmos).
        if (! is_array($header) || ($header['alg'] ?? null) !== config('gateway.jwt.algorithm')) {
            return null;
        }

        $expected = hash_hmac('sha256', "$encodedHeader.$encodedPayload", $secret, true);
        if (! hash_equals($expected, $this->base64UrlDecode($encodedSignature))) {
            return null;
        }

        $payload = json_decode($this->base64UrlDecode($encodedPayload), true);
        if (! is_array($payload)) {
            return null;
        }

        $now = time();
        $leeway = (int) config('gateway.jwt.leeway');
        if (! isset($payload['exp']) || ! is_numeric($payload['exp']) || $now - $leeway >= (int) $payload['exp']) {
            return null;
        }
        if (isset($payload['nbf']) && $now + $leeway < (int) $payload['nbf']) {
            return null;
        }
        if (isset($payload['iat']) && $now + $leeway < (int) $payload['iat']) {
            return null;
        }

        return $payload;
    }

    private function validateRemote(string $token): ?array
    {
        $response = Http::withToken($token)
            ->acceptJson()
            ->connectTimeout(config('gateway.connect_timeout'))
            ->timeout(config('gateway.timeout'))
            ->post(config('gateway.jwt.verify_url'));

        if (! $response->ok() || $response->json('valid') !== true) {
            return null;
        }

        return $response->json('payload') ?? [];
    }

    private function decodeWithoutVerification(string $token): array
    {
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return [];
        }

        return json_decode($this->base64UrlDecode($parts[1]), true) ?: [];
    }

    private function base64UrlDecode(string $value): string
    {
        $remainder = strlen($value) % 4;
        if ($remainder) {
            $value .= str_repeat('=', 4 - $remainder);
        }

        return (string) base64_decode(strtr($value, '-_', '+/'), true);
    }
}
