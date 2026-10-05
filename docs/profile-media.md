# Profile media storage

Dev, staging, and production each run the pinned RustFS 1.0.0 image with a separate persistent volume. S3 is reachable only on the Docker network. The console is bound to localhost (`19001` dev, `19002` staging, `9001` production); use an SSH tunnel for administration. Compose checks `/health` before starting the API.

## Provision a bucket and application key

Set unique `RUSTFS_ADMIN_ACCESS_KEY` and `RUSTFS_ADMIN_SECRET_KEY` values in the environment for the RustFS container. Keep those credentials for administration and one-time bootstrap only.

1. Start RustFS with its persistent volume and wait for its healthcheck.
2. Run the core service's `media:bootstrap-rustfs` command with the administrator credentials supplied as `RUSTFS_BOOTSTRAP_ACCESS_KEY` and `RUSTFS_BOOTSTRAP_SECRET_KEY`. The script creates `acs-media` if needed and applies public `GetObject` policies to the profile, news, project, curriculum, classbook and migration-image prefixes.
3. In the RustFS console, create an application identity restricted to `s3:PutObject`, `s3:GetObject` and `s3:DeleteObject` on those six `acs-media/public/` prefixes. The migration reads the copied object back to verify its checksum before switching database references. Put the key in `RUSTFS_APP_ACCESS_KEY_ID` and `RUSTFS_APP_SECRET_ACCESS_KEY` for the core service.
4. Set `RUSTFS_BUCKET=acs-media`. Keep `PROFILE_MEDIA_PROVIDER=supabase` until schema deployment, URL backfill, and portal rollout are complete; then switch the core service to `rustfs`.

The Next.js runtime rewrite serves only GET and HEAD under the six approved `/media/<bucket>/public/` image prefixes. It proxies objects to RustFS without forwarding browser cookies or authorization headers. No S3 root, object listing, upload route, or console route is exposed through the portal.

Use a separate volume per environment and back up both the database and the corresponding RustFS volume before production rollout. Switching a media upload provider does not copy or mirror existing objects. See the core service's central-media migration guide for the manifest-backed migration.

## Portal media configuration

Set `RUSTFS_READ_ENDPOINT` and `RUSTFS_BUCKET` in each portal environment. They are read when the portal handles a request, so one built portal image works in local, staging and production.

```env
RUSTFS_READ_ENDPOINT=https://acswebsite-rustfs-a21b17-31-97-48-3.sslip.io/
RUSTFS_BUCKET=acs-bucket-staging
```

For local Docker development and production, use `RUSTFS_READ_ENDPOINT=http://rustfs:9000` and `RUSTFS_BUCKET=acs-media`. For a local portal outside Docker, set the endpoint to an address reachable from the host.

Deploy the portal with its two values set. Staging's core-service still uses `RUSTFS_ENDPOINT` for S3 uploads; the portal uses `RUSTFS_READ_ENDPOINT` to serve public objects.

Run `npm run test:media-rewrite` in the portal repository to test its production build against a local mock object store.

After deploying, an existing profile image URL under the staging `/media` path should return `200` with an image content type.
