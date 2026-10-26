# Copyright (C) 2026 SmartSafeHub contributors
# SPDX-License-Identifier: GPL-3.0-or-later
include $(TOPDIR)/rules.mk

PKG_NAME:=smartsafehub-app-retro-arcade
PKG_VERSION:=0.1.0
PKG_RELEASE:=1
PKG_LICENSE:=GPL-3.0-or-later
PKG_LICENSE_FILES:=LICENSE
PKG_MAINTAINER:=SmartSafeHub Contributors
PKGARCH:=all

include $(INCLUDE_DIR)/package.mk

define Package/smartsafehub-app-retro-arcade
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=SmartSafeHub Retro Arcade
  DEPENDS:=+luci-app-smartsafehub
  URL:=https://github.com/Junatum/retro-arcade
endef

define Package/smartsafehub-app-retro-arcade/description
  Self-contained, browser-based CHIP-8 emulator served by OpenWrt.
  No downloaded cores, console ROMs, BIOS or external runtime services.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./LICENSE $(PKG_BUILD_DIR)/
endef

define Build/Compile
	@python3 $(CURDIR)/scripts/release_audit.py --release
endef

define Package/smartsafehub-app-retro-arcade/install
	$(INSTALL_DIR) $(1)/www/retro-arcade
	$(CP) ./web/. $(1)/www/retro-arcade/
	$(INSTALL_DATA) ./LICENSE $(1)/www/retro-arcade/LICENSE.txt
	$(INSTALL_DATA) ./THIRD_PARTY.md $(1)/www/retro-arcade/THIRD_PARTY.md
	$(INSTALL_DATA) ./SOURCE_OFFER.md $(1)/www/retro-arcade/SOURCE_OFFER.md
	$(INSTALL_DATA) ./INSTALLATION_INFO.md $(1)/www/retro-arcade/INSTALLATION_INFO.md
endef

$(eval $(call BuildPackage,smartsafehub-app-retro-arcade))
