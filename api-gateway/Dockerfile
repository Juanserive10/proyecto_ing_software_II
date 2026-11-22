# ---------- Dependencias de Composer ----------
FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --no-scripts --no-autoloader --prefer-dist
COPY . .
RUN composer dump-autoload --no-dev --optimize --classmap-authoritative

# ---------- Imagen final: nginx + php-fpm ----------
FROM php:8.4-fpm-alpine
RUN apk add --no-cache nginx \
    && docker-php-ext-install opcache \
    && rm -f /etc/nginx/http.d/default.conf

WORKDIR /var/www/html
COPY --from=vendor /app /var/www/html
COPY docker/nginx.conf /etc/nginx/http.d/gateway.conf
COPY docker/php-fpm.conf /usr/local/etc/php-fpm.d/zz-gateway.conf
COPY docker/php.ini /usr/local/etc/php/conf.d/gateway.ini
COPY docker/entrypoint.sh /usr/local/bin/gateway-entrypoint

RUN cp .env.example .env \
    && sed -i 's/^APP_KEY=.*/APP_KEY=/' .env \
    && mkdir -p storage/framework/cache/data storage/framework/views storage/framework/sessions storage/logs bootstrap/cache \
    && chown -R www-data:www-data storage bootstrap/cache

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1:8000/api/health || exit 1
ENTRYPOINT ["gateway-entrypoint"]
