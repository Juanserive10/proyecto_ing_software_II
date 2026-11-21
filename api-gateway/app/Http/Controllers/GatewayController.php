<?php

namespace App\Http\Controllers;

use App\Services\JwtValidator;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response as UpstreamResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

/**
 * Proxy inverso: /api/{service}/{path} -> {URL interna del servicio}/{path}.
 */
class GatewayController extends Controller
{
    /** Cabeceras del cliente que se reenvían al microservicio. */
    private const FORWARD_REQUEST_HEADERS = ['Authorization', 'Accept', 'Accept-Language'];

    /** Cabeceras del microservicio que se devuelven al cliente (CORS lo gestiona el gateway). */
    private const FORWARD_RESPONSE_HEADERS = ['Content-Type', 'Content-Disposition', 'Cache-Control', 'Location'];

    public function __construct(private readonly JwtValidator $jwt)
    {
    }

    public function proxy(Request $request, string $service, string $path = ''): Response|JsonResponse
    {
        $baseUrl = rtrim(config("gateway.services.$service"), '/');
        $path = ltrim($path, '/');
        $url = $baseUrl.'/'.$path;
        // Query original sin normalizar (conserva orden y claves repetidas).
        $query = (string) $request->server('QUERY_STRING');
        if ($query !== '') {
            $url .= '?'.$query;
        }

        $requestId = $request->header('X-Request-Id') ?: (string) Str::uuid();
        $started = microtime(true);

        try {
            // Con multipart, send() solo adjunta los archivos si recibe la opción 'multipart'.
            $options = $this->isMultipart($request) ? ['multipart' => []] : [];
            $upstream = $this->buildUpstreamRequest($request, $requestId)
                ->send($request->method(), $url, $options);
        } catch (ConnectionException $e) {
            $this->logRequest($request, $service, $path, 503, $started, $requestId);

            return response()->json([
                'error' => "El servicio '$service' no está disponible",
                'service' => $service,
            ], 503)->header('X-Request-Id', $requestId);
        }

        if ($service === 'usuarios' && $path === 'auth/logout' && $upstream->successful()) {
            $this->jwt->revoke((string) $request->bearerToken());
        }

        $this->logRequest($request, $service, $path, $upstream->status(), $started, $requestId);

        return $this->buildClientResponse($upstream, $service, $requestId, $started);
    }

    public function health(): JsonResponse
    {
        return response()->json([
            'service' => 'api-gateway',
            'status' => 'ok',
            'routes' => array_map(fn ($s) => "/api/$s/", array_keys(config('gateway.services'))),
        ]);
    }

    private function buildUpstreamRequest(Request $request, string $requestId): PendingRequest
    {
        $headers = ['X-Request-Id' => $requestId, 'X-Forwarded-For' => $request->ip(), 'X-Forwarded-By' => 'andina-api-gateway'];
        foreach (self::FORWARD_REQUEST_HEADERS as $name) {
            if ($request->hasHeader($name)) {
                $headers[$name] = $request->header($name);
            }
        }

        if ($payload = $request->attributes->get('jwt_payload')) {
            $headers['X-User-Id'] = (string) ($payload['id_usuario'] ?? $payload['sub'] ?? '');
            $headers['X-User-Rol'] = (string) ($payload['rol'] ?? '');
        }

        $pending = Http::withHeaders($headers)
            ->connectTimeout(config('gateway.connect_timeout'))
            ->timeout(config('gateway.timeout'))
            ->withOptions(['allow_redirects' => false]);

        // PHP-FPM ya parseó los multipart/form-data (php://input viene vacío),
        // así que se reconstruye el formulario con campos y archivos.
        if ($this->isMultipart($request)) {
            $pending->asMultipart();
            foreach ($request->allFiles() as $field => $file) {
                /** @var UploadedFile[] $items */
                $items = is_array($file) ? $file : [$file];
                foreach ($items as $item) {
                    $pending->attach($field, fopen($item->getRealPath(), 'r'), $item->getClientOriginalName(), [
                        'Content-Type' => $item->getClientMimeType(),
                    ]);
                }
            }
            foreach ($request->post() as $field => $value) {
                if (is_scalar($value)) {
                    $pending->attach($field, (string) $value);
                }
            }

            return $pending;
        }

        $body = $request->getContent();
        if ($body !== '') {
            $pending->withBody($body, $request->header('Content-Type', 'application/json'));
        }

        return $pending;
    }

    private function isMultipart(Request $request): bool
    {
        return str_starts_with((string) $request->header('Content-Type'), 'multipart/form-data');
    }

    private function buildClientResponse(UpstreamResponse $upstream, string $service, string $requestId, float $started): Response
    {
        $response = response($upstream->body(), $upstream->status());

        foreach (self::FORWARD_RESPONSE_HEADERS as $name) {
            if ($upstream->hasHeader($name)) {
                $response->header($name, $upstream->header($name));
            }
        }

        return $response
            ->header('X-Request-Id', $requestId)
            ->header('X-Upstream-Service', $service)
            ->header('X-Gateway-Time-Ms', (string) round((microtime(true) - $started) * 1000, 1));
    }

    private function logRequest(Request $request, string $service, string $path, int $status, float $started, string $requestId): void
    {
        Log::info('gateway.request', [
            'request_id' => $requestId,
            'method' => $request->method(),
            'service' => $service,
            'path' => '/'.$path,
            'status' => $status,
            'ms' => round((microtime(true) - $started) * 1000, 1),
            'user' => $request->attributes->get('jwt_payload')['id_usuario'] ?? null,
        ]);
    }
}
