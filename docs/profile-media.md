# Profile media storage

Dev, staging, and production each run the pinned RustFS 1.0.0 image with a separate persistent volume. S3 is reachable only on the Docker network. The console is bound to localhost (`19001` dev, `19002` staging, `9001` production); use an SSH tunnel for administration. Compose checks `/health` before starting the API.

## Provision a bucket and application key

Set unique `RUSTFS_ADMIN_ACCESS_KEY` and `RUSTFS_ADMIN_SECRET_KEY` values in the environment for the RustFS container. Keep those credentials for administration and one-time bootstrap only.

1. Start RustFS with its persistent volume and wait for its healthcheck.
2. Run the core service's `media:bootstrap-rustfs` command with the administrator credentials supplied as `RUSTFS_BOOTSTRAP_ACCESS_KEY` and `RUSTFS_BOOTSTRAP_SECRET_KEY`. The script creates `acs-media` if needed and applies a public `GetObject` policy only to `public/profiles/*`.
3. In the RustFS console, create an application identity restricted to `s3:PutObject` and `s3:DeleteObject` on `acs-media/public/profiles/*`. Put its key in `RUSTFS_APP_ACCESS_KEY_ID` and `RUSTFS_APP_SECRET_ACCESS_KEY` for the core service.
4. Set `RUSTFS_BUCKET=acs-media`. Keep `PROFILE_MEDIA_PROVIDER=supabase` until schema deployment, URL backfill, and portal rollout are complete; then switch the core service to `rustfs`.

The Traefik route serves only GET and HEAD under `/media/acs-media/public/profiles/`. It strips `/media` before forwarding to RustFS. No S3 root, object listing, upload route, or console route is public.

Use a separate volume per environment and back up both the database and the corresponding RustFS volume before production rollout. Switching the profile upload provider does not copy or mirror objects.
