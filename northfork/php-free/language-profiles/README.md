# Explicit Node profiles

These recipes preserve the runtime selectors required by twelve retained CodeBuild projects.
The CI owner builds and publishes the profiles after root review.
These files do not change applications or CodeBuild projects.

Custom CodeBuild images skip `runtime-versions` and override image entrypoints.
Each profile therefore selects its exact Node version during image construction.
The recipes preserve the base entrypoint and working directory.

| Native architecture | Node | Required package tools |
|---|---|---|
| amd64 | 12.22.12 | Bundled npm |
| amd64 | 18.20.8 | Bundled npm, Yarn Classic 1.22.22 |
| amd64 | 20.20.2 | Bundled npm |
| amd64 | 22.23.3 | Bundled npm, Yarn Classic 1.22.22 |
| amd64 | 24.19.0 | Bundled npm, Corepack 0.36.0, cached pnpm 11.27.1 |
| arm64 | 20.20.2 | Bundled npm |

The Node 18, 20, and 22 recipes select the base cache with `n --offline --no-preserve`.
A missing cache fails the build.
Node 12.22.12 and amd64 Node 24.19.0 use official archives with fixed SHA256 checksums.
Package tools use fixed registry versions and integrity hashes.
No package lifecycle script runs during tool installation.

The product locator source already installs `corepack@latest`.
That updater does not select Node or change its exact `packageManager` version.
Qualification must run that unchanged updater and then confirm Node 24.19.0 and pnpm 11.27.1.
Do not classify the updater alone as a compatibility failure.

## Render and build

Use an approved immutable PHP-free base for the same native architecture.
The renderer accepts no mutable base tag.
Run these commands from this directory:

```sh
python3 render-profile.py node-18.20.8-amd64 --base "$VERIFIED_NATIVE_BASE" > /tmp/node-profile.Dockerfile
docker build --platform linux/amd64 -f /tmp/node-profile.Dockerfile -t local-node18-profile .
```

The build runs exact Node and bundled npm checks, offline package fixtures, and a PHP scan.
The Node binary must match the cached version byte for byte.
Yarn and pnpm fixtures use a local file dependency without lifecycle scripts or registry access.

Run `qualification/profile-buildspec.yml` in a standalone CodeBuild execution after image publication.
Use the immutable profile digest, exact CI source commit, native architecture, `NO_ARTIFACTS`, and `NO_CACHE`.
The CI owner must retain full filesystem/layer PHP absence proof from the sanitized base.
A static renderer test is not native runtime qualification.

## Source qualification

`qualification/source-contracts.json` binds each retained project to exact source and manifest hashes.
It records lockfiles, package-manager requirements, candidate scripts, and required review gates.
No application command in that contract has executed from this change.

Review lifecycle scripts, build configuration, plugins, static generation, and tests before source execution.
Materialize locked dependencies without lifecycle scripts first.
Run approved build and test commands in a disposable container without network access or production credentials.
Do not execute original publication, notification, deployment, or data-job phases.
Do not pass production environment files to qualification.
Use synthetic local configuration.

Serverless and SST packaging can resolve real infrastructure and invoke plugins.
Those commands require a reviewed contract before execution.
The inline `gastrofy-api-codedeploy` source remains unbound and cannot receive source qualification yet.

## Exclusions and gates

The four Docker-selector retirement candidates and `resolver-java` are excluded.
Corretto 8 and Gradle 4.4 requirements remain recorded in the coordinator's retirement audit.
No Java profile is implemented.

Native profile builds, standalone CodeBuild launch proofs, and approved source builds remain release gates.
The CI owner controls base publication and project rollout.
Do not push this shared repository until its external build webhook audit permits publication.
