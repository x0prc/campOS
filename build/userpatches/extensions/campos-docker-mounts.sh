#!/usr/bin/env bash
#
# campOS: make the sibling userpatches dir and the campd package visible
# inside Armbian's docker build container.
#
# Armbian only bind-mounts ${SRC}/{lib,config,extensions,packages,patch,
# tools,userpatches} (docker.sh), i.e. armbian-build/userpatches. Our
# userpatches live next to armbian-build (build/userpatches) so they stay
# in git, and campd/ sits above that. Without these mounts the container
# cannot see ${USERPATCHES_PATH}, customize-image.sh never gets copied
# into the chroot, and the build silently produces a vanilla image.
#
# This hook runs on the host (docker args are assembled host-side), where
# both paths exist. Native builds never call it.

function host_pre_docker_launch() {
	local campos_root
	campos_root="$(cd "${USERPATCHES_PATH}/../.." && pwd)" # <root>/build/userpatches -> <root>
	display_alert "campOS docker mounts" "userpatches + campd -> container" "info"
	DOCKER_EXTRA_ARGS+=(
		"--mount" "type=bind,source=${USERPATCHES_PATH},target=${USERPATCHES_PATH}"
		"--mount" "type=bind,source=${campos_root}/campd,target=${campos_root}/campd"
	)
	return 0
}
