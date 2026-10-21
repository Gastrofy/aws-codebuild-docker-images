# Northfork PHP-free builders

These native CodeBuild images remove every PHP installation and module from pinned public bases.
A scratch final stage removes the original parent layers from the distributed image.
The verification reads every final layer and rejects remaining PHP executables and modules.
It also verifies exact non-PHP environment values and the public base tool versions.

| Architecture | Profile | Validated manifest digest | Actual CodeBuild launch |
| --- | --- | --- | --- |
| AMD64 | [AL2023 standard 5](al2023-x86_64-standard-5.0) | `sha256:a4ceb9350d181c50f6cbd048ed412e077c545b914be18626dd3c62c39a0a9108` | `90307d03-5af0-4534-a65a-0d02ccf9c5b4` |
| ARM64 | [AL2023 standard 3](al2023-aarch64-standard-3.0) | `sha256:50cf9b7005ad623cd2c5dc29a62e1833f1ed119d79b18004927fab5fbb3854f2` | `df25cfdd-33f0-4ae3-9ea3-b47db3c4f5f4` |

Both images use the existing ECR repository `950664063715.dkr.ecr.eu-central-1.amazonaws.com/northfork/php-security-base`.
The provenance files bind each recipe package, public base, tested image ID, manifest digest, and actual runner proof.
The upstream recipe reference is not a claim about the public binary image's source commit.

Actual CodeBuild tests verify PHP absence, AWS CLI authentication, template substitution, Docker, Buildx, and JSON metadata extraction.
They also verify explicit Node selection and Yarn availability.
The AMD64 image contains 5.93 GB of compressed layers; ARM64 contains 4.87 GB.
Cold provisioning took 182 seconds and 152 seconds in the recorded standalone builds.
These measurements do not guarantee another project's provisioning time.

Custom CodeBuild images ignore image entrypoints and managed runtime selectors.
Every Docker source buildspec must initialize the daemon before its first Docker command.
The validated [startup helper](al2023-x86_64-standard-5.0/qualification/ensure-docker.sh) keeps a healthy daemon or starts the bundled official daemon with a 75-second limit.
It does not start an application entrypoint.
Projects that do not use Docker do not need daemon initialization or privileged mode.

Explicit language requirements use separate [Node profiles](language-profiles).
The base selects Node 18 and Python 3.11; higher version constants describe installed caches.
Each project still needs its exact source, role, network, compute, architecture, and tool tests before an image change.
A cache hit does not replace runtime or digest verification.
Do not select a pre-upgrade image as a validated output.

Run `python3 verify-frozen-packages.py` to verify package hashes.
Run each profile's build script on its native architecture for the full image and layer checks.
The base startup proofs do not certify completion of the infrastructure migration.
