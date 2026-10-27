# Copyright (C) 2026 SmartSafeHub contributors
# SPDX-License-Identifier: GPL-3.0-or-later
include $(TOPDIR)/rules.mk

PKG_NAME:=smartsafehub-app-retro-arcade
PKG_VERSION:=0.1.0
PKG_RELEASE:=5
PKG_LICENSE:=GPL-3.0-or-later MPL-2.0 Apache-2.0
PKG_LICENSE_FILES:=LICENSE LICENSES/mGBA.txt LICENSES/JSNES.txt
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
  Browser-based CHIP-8, mGBA GB/GBC/GBA and JSNES NES/Famicom emulators served by OpenWrt.
  Pinned mGBA WASM and verified JSNES JavaScript sources are bundled locally; no APK downloads.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./LICENSE $(PKG_BUILD_DIR)/
	$(INSTALL_DIR) $(PKG_BUILD_DIR)/LICENSES
	$(CP) ./LICENSES/mGBA.txt $(PKG_BUILD_DIR)/LICENSES/
	$(CP) ./LICENSES/JSNES.txt $(PKG_BUILD_DIR)/LICENSES/
endef

define Build/Compile
	@python3 $(CURDIR)/scripts/release_audit.py --release
endef

define Package/smartsafehub-app-retro-arcade/install
	$(INSTALL_DIR) $(1)/www/retro-arcade
	$(CP) ./web/. $(1)/www/retro-arcade/
	$(INSTALL_DATA) ./LICENSE $(1)/www/retro-arcade/LICENSE.txt
	$(INSTALL_DIR) $(1)/www/retro-arcade/LICENSES
	$(INSTALL_DATA) ./LICENSES/mGBA.txt $(1)/www/retro-arcade/LICENSES/mGBA.txt
	$(INSTALL_DATA) ./LICENSES/JSNES.txt $(1)/www/retro-arcade/LICENSES/JSNES.txt
	$(INSTALL_DATA) ./docs/THIRD_PARTY.md $(1)/www/retro-arcade/THIRD_PARTY.md
	$(INSTALL_DIR) $(1)/www/retro-arcade/docs
	$(INSTALL_DATA) ./docs/SOURCE_OFFER.md $(1)/www/retro-arcade/docs/SOURCE_OFFER.md
	$(INSTALL_DATA) ./docs/INSTALLATION_INFO.md $(1)/www/retro-arcade/docs/INSTALLATION_INFO.md
endef

$(eval $(call BuildPackage,smartsafehub-app-retro-arcade))
