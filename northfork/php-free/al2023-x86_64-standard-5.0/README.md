# PHP-free CodeBuild image

This image supports native AMD64 Docker orchestration without host PHP.
It removes PHP installations, modules, Composer, and PHP runtime selectors from a pinned public CodeBuild image.
The final stage starts from scratch and copies the sanitized filesystem.
Old PHP files cannot remain in parent image layers.

The image preserves non-PHP configuration and tools from the pinned public image.
It does not reproduce every default tool version in the current managed CodeBuild image.
The official source selects Node 18 and Python 3.11 as defaults, which the actual runner confirms.
Higher version constants describe installed caches.
Some other tools differ from the managed baseline, including the default .NET SDK.
Use this profile only after the project's actual source and tool contract pass qualification.
Do not use this AMD64 image for ARM projects.

## Build and verify

Use a native AMD64 machine with Docker, privileged containers, Bash, and Python 3.
Run `bash build-and-verify.sh` from this directory.
The script builds the image without publishing it.
It compares tool versions with the pinned public base.
It checks exact non-PHP environment values, including escaped newlines.
It verifies the entrypoint, working directory, and volume declarations.
It rejects original parent diffIDs and scans every final filesystem layer for PHP executables and modules.
It also tests the Docker daemon and a nested build.

`provenance.json` records the exact frozen package hash and file hashes.
The upstream recipe commit is a reference only.
It does not prove which source commit produced the public binary image.
The base manifest and configuration digests provide the binary binding.

## Qualify actual CodeBuild execution

Run a standalone build with the candidate manifest digest as `imageOverride`.
Use `SERVICE_ROLE` for image pull credentials and preserve the project's architecture, role, VPC, compute, and privileged mode.
Use `NO_ARTIFACTS` and the qualification buildspec in this directory.
The buildspec scans the live filesystem for PHP, reports tool versions, and tests Docker, Buildx, and Python JSON metadata parsing.
It also checks explicit Node 22 selection and Yarn availability.
No application pipeline or deployment runs during this proof.

CodeBuild overrides custom image entrypoints.
Preserving the image entrypoint does not replace the actual CodeBuild launch test.
Run `bash qualification/ensure-docker.sh` before Docker commands in each migrated source buildspec.
It keeps a healthy daemon or starts the bundled official daemon entrypoint with a 75-second limit.
The launch proof calls it twice to check idempotency.
Do not background the application entrypoint.

Custom images do not implement managed `runtime-versions` selection.
Projects with explicit language requirements need an explicit version selector and a source build test.
Do not replace those requirements with the candidate image defaults.

## First application contracts

The Campaign source `9a0b04328815245fc42489a44aa02e86e22141e9` uses Docker orchestration without host Node or Python.
Its safe proof builds the existing application Dockerfile, checks Composer requirements, displays command help, and generates a synthetic PDF.
It does not send reports, send email, consume Kafka messages, or publish images.

The RRPS source `9c85ad6e48612a0ddca8cc9a568d7947386d9289` uses Docker and host Python's standard `json` module for Buildx metadata.
Its safe proof builds the existing application Dockerfile and runs Composer checks, unit tests, output policy tests, and command listing.
The host qualification tests the exact JSON digest extraction contract.
It does not run business consumers or publish images.

Qualify each project's exact service role before its application source test.
Add only repository-scoped ECR pull actions when the role lacks them.
Back up the role before any approved permission change.
Do not modify project image configuration until all proofs pass and the rollout owner approves the digest.

## References

- [CodeBuild project configuration](https://docs.aws.amazon.com/codebuild/latest/userguide/create-project.html)
- [CodeBuild runtime selection](https://docs.aws.amazon.com/codebuild/latest/userguide/runtime-versions.html)
