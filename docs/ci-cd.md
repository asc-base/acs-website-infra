# Centralized application CI/CD

The CI implementation for `asc-base/acs-portal` and `asc-base/acs-core-service`
is maintained in this repository's `.github/workflows/release.yml` and
`ci-template/release.py`. Application repositories retain only event-trigger
workflows calling the reusable workflow at `@main`. GitHub runs these jobs in
the calling application's context, so `github.repository`, `GITHUB_TOKEN`,
environments, secrets, variables and GitHub Releases belong to the application.
Portal PR lint/build checks are also implemented here in `pr-build-test.yml`.

## Release flow

1. Push a branch named `release/MAJOR.MINOR.PATCH`, for example `release/1.0.1`.
   The version is taken from the branch, not `package.json` or a manually created tag.
2. Build the release commit once and publish to the application's own GHCR repository:
   `ghcr.io/asc-base/acs-portal:staging-1.0.1` or
   `ghcr.io/asc-base/acs-core-service:staging-1.0.1`.
   An additional `staging-1.0.1-<full-source-sha>` image tag retains each build.
   The core-service uses Docker's `production` target for this shared image;
   environment-specific configuration remains in compose/Dokploy at runtime.
3. Update `staging/<service>/docker-compose.yml` to
   `<image>:staging-1.0.1@sha256:<digest>` and trigger that application's staging webhook.
4. After the staging deployment webhook succeeds, publish GitHub pre-release/tag
   `staging-1.0.1-<full-source-sha>` on the source commit. Its `image.json` asset records
   `repository`, `version`, `source_sha`, `image` and `image_digest` (`IMAGE_DIGEST`).
   Each branch push gets a separate pre-release; rerunning a published commit reuses its digest.
5. Merge that release branch into **main**. A merged-PR event downloads metadata for
   the exact PR head commit. Missing metadata, a mismatched version/commit or a merged
   source tree different from staging stops promotion. Merge, squash and rebase work
   when their resulting source tree matches the staged commit; merge main into the
   release branch and stage it again if main has additional changes.
6. Promote `<image>@${IMAGE_DIGEST}` with `docker buildx imagetools create --prefer-index=false`
   to `<image>:1.0.1` and verify the resulting digest is unchanged. Production does not build.
   Publish GitHub release/tag `1.0.1` on the merge commit with the same metadata asset.
   Existing production version tags are reusable only when their release metadata is identical.
7. Pin `prod/<service>/docker-compose.yml` and the corresponding image in
   `prod/docker-compose.yml` to `<image>:1.0.1@${IMAGE_DIGEST}`, then trigger the production webhook.
   The portal no longer needs `PORTAL_IMAGE_DIGEST` after its first promotion.

Git tag pushes do not trigger builds. A production version is final: subsequent staging
pushes for that version are rejected, so start a new release branch for the next version.
The webhook confirms that Dokploy accepted the deployment request; inspect Dokploy and
validate the staging application before merging. It does not wait for application health.
If staging fails before publishing the pre-release, rerun its workflow before merging.
If production deployment fails, rerun the merged-PR workflow; its metadata and digest are retained.

## Repository configuration and rollout

Publish the infra workflow and helper on **infra/main first**, then roll out the caller
workflows to both application repositories (including active release branches and main).
Keep the workflows available in the application main branches for merged-PR events.

If infra is private, allow both applications to access its reusable workflows in
**infra → Settings → Actions → General → Access**. Ensure each GHCR package grants
Actions write access to its application repository. Caller workflows request
`contents: write` for tags/releases and `packages: write` for GHCR.

Configure the following secrets in **each application repository**, or as organization
secrets available to both callers. Environment-specific secrets may be placed in the
application's `staging` and `production` environments:

| Secret | Purpose |
| --- | --- |
| `ACS_WEBSITE_INFRA_TOKEN` | Read/checkout infra and push image changes to infra/main. Use a token with infra Contents read/write and permission to push to main under its branch rules. |
| `DOKPLOY_STAGING_WEBHOOK_URL` | Deploy this application's staging compose after its digest update. |
| `DOKPLOY_PROD_WEBHOOK_URL` | Deploy this application's production compose after promotion. |

`GITHUB_TOKEN` is provided automatically by GitHub for the calling application's
releases and GHCR package. Secrets placed only in infra are not inherited by callers.
Portal image rendering uses source URLs directly in the browser, so the shared artifact no longer needs a build-time image-host variable.

Jobs are serialized per application without cancelling an active deployment. Infra pushes
refresh and reapply image updates with up to three attempts to handle another application
committing during a build. GitHub concurrency may replace an older pending run with a newer
one, so wait for the exact commit's pre-release before merging it.

The existing infra `development.yml` workflow separately deploys development through Portainer.
Scope its main-branch trigger to `dev/**`, so automated staging/production image commits
do not also deploy development.

## Local checks

```sh
python3 -m unittest discover -s ci-template -p 'test_*.py'
actionlint .github/workflows/release.yml .github/workflows/pr-build-test.yml
```

References: [GitHub reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
and [Docker manifest promotion](https://docs.docker.com/reference/cli/docker/buildx/imagetools/create/).
