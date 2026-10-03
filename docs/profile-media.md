# Profile media storage

Dev, staging, and production each run the pinned RustFS 1.0.0 image with a separate persistent volume. S3 is reachable only on the Docker network. The console is bound to localhost (`19001` dev, `19002` staging, `9001` production); use an SSH tunnel for administration. Compose checks `/health` before starting the API.

## Provision a bucket and application key

Set unique `RUSTFS_ADMIN_ACCESS_KEY` and `RUSTFS_ADMIN_SECRET_KEY` values in the environment for the RustFS container. Keep those credentials for administration and one-time bootstrap only.

1. Start RustFS with its persistent volume and wait for its healthcheck.
2. Run the core service's `media:bootstrap-rustfs` command with the administrator credentials supplied as `RUSTFS_BOOTSTRAP_ACCESS_KEY` and `RUSTFS_BOOTSTRAP_SECRET_KEY`. The script creates `acs-media` if needed and applies public `GetObject` policies only to `public/profiles/*` and `public/news/*`.
3. In the RustFS console, create an application identity restricted to `s3:PutObject` and `s3:DeleteObject` on `acs-media/public/profiles/*` and `acs-media/public/news/*`. Put its key in `RUSTFS_APP_ACCESS_KEY_ID` and `RUSTFS_APP_SECRET_ACCESS_KEY` for the core service.
4. Set `RUSTFS_BUCKET=acs-media`. Keep `PROFILE_MEDIA_PROVIDER=supabase` until schema deployment, URL backfill, and portal rollout are complete; then switch the core service to `rustfs`.

The Traefik route serves only GET and HEAD under `/media/acs-media/public/profiles/` and `/media/acs-media/public/news/`. It strips `/media` before forwarding to RustFS. No S3 root, object listing, upload route, or console route is public.

Use a separate volume per environment and back up both the database and the corresponding RustFS volume before production rollout. Switching the profile upload provider does not copy or mirror objects.

## Staging media route

`staging/core-service/docker-compose.yml` includes a media proxy on `dokploy-network`.
Its Traefik labels route GET and HEAD requests for profile and news images on
`STAGING_HOST` to `RUSTFS_ENDPOINT`, removing `/media` from the upstream path.
The HTTPS upstream uses its own hostname for Host and TLS SNI. Other object paths
and write methods are rejected.

Set these variables in the staging core-service application's Dokploy environment:

```env
STAGING_HOST=acs-staging.narutchai.com
PROFILE_MEDIA_PROVIDER=rustfs
NEWS_MEDIA_PROVIDER=rustfs
RUSTFS_ENDPOINT=https://acswebsite-rustfs-a21b17-31-97-48-3.sslip.io/
RUSTFS_BUCKET=acs-bucket-staging
RUSTFS_PUBLIC_BASE_URL=https://acs-staging.narutchai.com/media/acs-bucket-staging
RUSTFS_ACCESS_KEY_ID=<application-access-key>
RUSTFS_SECRET_ACCESS_KEY=<application-secret-key>
```

Deploy the updated staging core-service Compose application. The existing `web`,
`websecure`, and `letsencrypt` Traefik configuration is shared with the API route;
no additional Dokploy domain or hand-written Traefik route is needed. Keep
`media-proxy.conf.template` alongside the Compose file in the Git checkout; the
proxy renders the template from its endpoint and bucket environment variables.

With the staging env saved in `staging/core-service/.env`, validate the proxy before
deployment from the repository root:

```sh
docker compose --env-file staging/core-service/.env -f staging/core-service/docker-compose.yml config --quiet
docker compose --env-file staging/core-service/.env -f staging/core-service/docker-compose.yml run --rm --no-deps media-proxy nginx -t
```

After redeploying, an existing profile image URL under the staging `/media` path
should return `200` with an image content type, rather than the portal's HTML 404.
