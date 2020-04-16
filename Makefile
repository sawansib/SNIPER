.PHONY: all platform_check dependencies_internal distclean.internal
all: platform_check dependencies_internal

# Disable some stuff in the public makefile that we'll implement ourselves
NO_PIN_CHECK=1
NO_PYTHON_DOWNLOAD=1
NO_MCPAT_DOWNLOAD=1
# Force local copy of Pin (downloaded automatically)
PIN_HOME=$(SIM_ROOT)/pin_kit
# Enable Pinplay
USE_PINPLAY=1

include Makefile.external

ifneq ($(DEBUG_DOWNLOAD_LOCATION),)
  DOWNLOAD_CMD=cat
  DOWNLOAD_PREFIX=$(DEBUG_DOWNLOAD_LOCATION)/
else
  DOWNLOAD_CMD=ssh benved.it.uu.se cat
  DOWNLOAD_PREFIX="/it/project/fo/uart/git/swoop/downloads/"
endif

# The target 'dependencies_internal' links with depedencies in Makefile.external
.PHONY: pin_internal boost mcpat hotspot python platform_check manual manualclean
dependencies_internal: pin_internal boost mcpat hotspot python platform_check
dependencies: dependencies_internal

platform_check:
	@if [ "$(readlink -f $(SNIPER_ROOT))" != "$(readlink -f $(CURDIR))" ]; then echo "You should set SNIPER_ROOT to $(CURDIR)"; false; fi
	@if [ -e .build_os -a "`cat .build_os 2>/dev/null`" != $(OS_TYPE) ]; then $(MAKE) $(MAKE_QUIET) clean; fi
	@echo $(OS_TYPE) > .build_os

PIN_VERSION=2.14
PIN_SUB_VERSION=67254
ifeq ($(USE_PINPLAY),1)
PINPLAY_VERSION=1.4
PIN_PREFIX=pinplay-$(PINPLAY_VERSION)-
else
PIN_PREFIX=
endif
PIN_FILE=$(PIN_PREFIX)pin-$(PIN_VERSION)-$(PIN_SUB_VERSION)-gcc.4.4.7-linux.tar.gz
pin_internal: $(PIN_HOME)/.pin_version_$(PIN_PREFIX)$(PIN_VERSION)_$(PIN_SUB_VERSION)
$(PIN_HOME)/.pin_version_$(PIN_PREFIX)$(PIN_VERSION)_$(PIN_SUB_VERSION):
ifeq ($(PIN_PREFIX),)
	$(_MSG) '[DOWNLO] Pin $(PIN_VERSION)-$(PIN_SUB_VERSION)'
else
	$(_MSG) '[DOWNLO] Pin ($(patsubst %-,%,$(PIN_PREFIX))) $(PIN_VERSION)-$(PIN_SUB_VERSION)'
endif
	$(_CMD) -rm -rf $(PIN_HOME)
	$(_CMD) mkdir -p $(PIN_HOME)
	$(_CMD) $(DOWNLOAD_CMD) $(addprefix $(DOWNLOAD_PREFIX),$(PIN_FILE)) | tar xz --strip-components 1 -C $(PIN_HOME)
	$(_CMD) touch $(PIN_HOME)/.pin_version_$(PIN_PREFIX)$(PIN_VERSION)_$(PIN_SUB_VERSION)
	@# Remove files compiled with the previous version of Pin
	$(_CMD) $(MAKE) $(MAKE_QUIET) clean

OS_TYPE=$(shell $(SIM_ROOT)/tools/get_os_type.sh)
boost:

mcpat: mcpat/mcpat-1.0
mcpat/mcpat-1.0:
	$(_MSG) '[DOWNLO] McPAT'
	$(_CMD) mkdir -p mcpat
	$(_CMD) $(DOWNLOAD_CMD) $(addprefix $(DOWNLOAD_PREFIX),"mcpat-1.0.tgz") | tar xz -C mcpat

hotspot: hotspot/hotspot
hotspot/hotspot:
	$(_MSG)  '[DOWNLO] Hotspot'
	$(_CMD) mkdir -p hotspot
	$(_CMD) $(DOWNLOAD_CMD) $(addprefix $(DOWNLOAD_PREFIX),"hotspot.tgz") | tar xz -C hotspot

PYTHON_DEP=python_kit/$(SNIPER_TARGET_ARCH)/lib/python2.7/lib-dynload/_sqlite3.so
python: $(PYTHON_DEP)
$(PYTHON_DEP):
	$(_MSG) '[DOWNLO] Python $(SNIPER_TARGET_ARCH)'
	$(_CMD) mkdir -p python_kit/$(SNIPER_TARGET_ARCH)
	$(_CMD) $(DOWNLOAD_CMD) $(addprefix $(DOWNLOAD_PREFIX),"sniper-python27-$(SNIPER_TARGET_ARCH).tgz") | tar xz --strip-components 1 -C python_kit/$(SNIPER_TARGET_ARCH)

manual:
	@$(MAKE) $(MAKE_QUIET) -C $(SIM_ROOT)/doc/manual

manualclean:
	@$(MAKE) $(MAKE_QUIET) -C $(SIM_ROOT)/doc/manual clean

# Depends on distclean (and also clean) through Makefile.external
distclean: distclean.internal
distclean.internal:
	$(_MSG) '[DISTCL] Pin $(PIN_VERSION)-$(PIN_SUB_VERSION)'
	$(_CMD) rm -rf $(PIN_HOME)
	$(_MSG) '[DISTCL] mcpat'
	$(_CMD) rm -rf mcpat
	$(_MSG) '[DISTCL] hotspot'
	$(_CMD) rm -rf hotspot
