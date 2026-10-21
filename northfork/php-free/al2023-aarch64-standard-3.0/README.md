# PHP-free native ARM image

This profile applies the [same isolation and qualification contract](../al2023-x86_64-standard-5.0/README.md) to native ARM.
Its public base manifest is pinned in the Dockerfile and provenance file.
All non-PHP environment values and tool versions must match that exact public base.
The final image starts from scratch and contains no original parent diffIDs.

Run `bash build-and-verify.sh` on a native ARM machine.
The verifier reports image-save and layer-scan progress without file contents or environment values.
The build does not publish an image.

DockerBuild, URL Shortener, and Meili require native ARM qualification.
Preserve `ARM_CONTAINER` and each project's original privileged, compute, role, and network settings.
Qualify their actual Docker, Buildx, Compose, AWS CLI, Bash, and other host commands before a project update.
Do not run their publishing or deployment phases as qualification.
No AMD64 emulation substitutes for the native proof.

This image does not restore managed language selectors.
ARM Node projects require separately qualified selected-version profiles.
