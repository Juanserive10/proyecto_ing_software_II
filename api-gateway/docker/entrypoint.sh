#!/bin/sh
set -e

# APP_KEY efímero si no se inyecta (el gateway no cifra cookies ni sesiones).
if [ -z "$APP_KEY" ]; then
    export APP_KEY="base64:$(head -c 32 /dev/urandom | base64)"
fi

php artisan config:cache
php artisan route:cache

php-fpm -D
exec nginx -g 'daemon off;'
