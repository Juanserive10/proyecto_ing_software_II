<?php

namespace Tests\Feature;

use Illuminate\Http\Client\Request as ClientRequest;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class GatewayTest extends TestCase
{
    private const SECRET = 'test-secret-andina';

    protected function setUp(): void
    {
        parent::setUp();
        config(['gateway.jwt.secret' => self::SECRET, 'gateway.jwt.mode' => 'local']);
    }

    private function makeToken(array $claims = [], ?string $secret = null, string $alg = 'HS256'): string
    {
        $b64 = fn (string $v) => rtrim(strtr(base64_encode($v), '+/', '-_'), '=');
        $header = $b64(json_encode(['alg' => $alg, 'typ' => 'JWT']));
        $payload = $b64(json_encode($claims + ['id_usuario' => 1, 'rol' => 'ADMINISTRADOR', 'iat' => time(), 'exp' => time() + 3600]));
        $signature = $b64(hash_hmac('sha256', "$header.$payload", $secret ?? self::SECRET, true));

        return "$header.$payload.$signature";
    }

    public function test_health_del_gateway_es_publico(): void
    {
        $this->getJson('/api/health')->assertOk()->assertJsonPath('service', 'api-gateway');
    }

    public function test_ruta_protegida_sin_token_responde_401_sin_llamar_al_servicio(): void
    {
        Http::fake();

        $this->getJson('/api/catalogo/products')->assertUnauthorized();

        Http::assertNothingSent();
    }

    public function test_rutas_publicas_de_usuarios_no_exigen_token(): void
    {
        Http::fake(fn () => Http::response(['access_token' => 'x'], 200));

        $this->postJson('/api/usuarios/auth/login', ['correo' => 'a@b.c', 'contrasena' => '123456'])->assertOk();
        $this->getJson('/api/inventario/health')->assertOk();
    }

    public function test_token_valido_se_reenvia_al_microservicio_correcto(): void
    {
        Http::fake(['catalogo-service:5002/*' => Http::response([['id_producto' => 1]], 200)]);
        $token = $this->makeToken();

        $this->getJson('/api/catalogo/products?q=taladro&id_categoria=2', ['Authorization' => "Bearer $token"])
            ->assertOk()
            ->assertHeader('X-Upstream-Service', 'catalogo')
            ->assertJsonPath('0.id_producto', 1);

        Http::assertSent(fn (ClientRequest $r) => $r->url() === 'http://catalogo-service:5002/products?q=taladro&id_categoria=2'
            && $r->hasHeader('Authorization', "Bearer $token")
            && $r->hasHeader('X-User-Id', '1'));
    }

    public function test_cada_prefijo_enruta_a_su_servicio(): void
    {
        Http::fake(fn () => Http::response(['ok' => true]));
        $token = $this->makeToken();

        foreach (config('gateway.services') as $service => $baseUrl) {
            $this->getJson("/api/$service/recurso/1", ['Authorization' => "Bearer $token"])->assertOk();
            Http::assertSent(fn (ClientRequest $r) => $r->url() === "$baseUrl/recurso/1");
        }
    }

    public function test_rechaza_firma_invalida_token_expirado_y_alg_none(): void
    {
        Http::fake();
        $casos = [
            $this->makeToken([], 'otro-secreto'),
            $this->makeToken(['exp' => time() - 3600]),
            rtrim(explode('.', $this->makeToken([], null, 'none'))[0].'.'.explode('.', $this->makeToken())[1].'.', ''),
        ];

        foreach ($casos as $token) {
            $this->getJson('/api/ventas/sales', ['Authorization' => "Bearer $token"])->assertUnauthorized();
        }
        Http::assertNothingSent();
    }

    public function test_logout_revoca_el_token_en_el_gateway(): void
    {
        Http::fake(fn () => Http::response(['message' => 'ok']));
        $token = $this->makeToken();
        $auth = ['Authorization' => "Bearer $token"];

        $this->postJson('/api/usuarios/auth/logout', [], $auth)->assertOk();
        $this->getJson('/api/catalogo/products', $auth)->assertUnauthorized();
    }

    public function test_servicio_caido_responde_503(): void
    {
        Http::fake(fn () => throw new \Illuminate\Http\Client\ConnectionException('down'));

        $this->getJson('/api/reportes/health')->assertStatus(503)->assertJsonPath('service', 'reportes');
    }

    public function test_prefijo_desconocido_responde_404(): void
    {
        $this->getJson('/api/pagos/x')->assertNotFound();
    }

    public function test_rbac_bloquea_escrituras_no_autorizadas_por_rol(): void
    {
        Http::fake(fn () => Http::response(['ok' => true], 200));

        $vendedor = ['Authorization' => 'Bearer '.$this->makeToken(['id_usuario' => 3, 'rol' => 'VENDEDOR'])];
        $bodega = ['Authorization' => 'Bearer '.$this->makeToken(['id_usuario' => 2, 'rol' => 'OPERADOR_BODEGA'])];

        // Vendedor puede vender y consultar catálogo, pero no ajustar inventario ni editar usuarios
        $this->postJson('/api/ventas/sales', ['items' => []], $vendedor)->assertOk();
        $this->getJson('/api/catalogo/products', $vendedor)->assertOk();
        $this->postJson('/api/inventario/inventory/movements', [], $vendedor)->assertForbidden();
        $this->putJson('/api/usuarios/users/1', ['id_rol' => 1], $vendedor)->assertForbidden();

        // Operador de bodega puede mover inventario y recibir OC, pero no registrar ventas POS
        $this->postJson('/api/inventario/inventory/transfers', [], $bodega)->assertOk();
        $this->postJson('/api/abastecimiento/purchase-orders/1/receipts', [], $bodega)->assertOk();
        $this->postJson('/api/ventas/sales', [], $bodega)->assertForbidden();
    }
}
