/* SmartSafeHub mGBA WebAssembly bridge (GPL-3.0-or-later).
 * Upstream mGBA C core is MPL-2.0, copyright Jeffrey Pfau and contributors.
 * Uses upstream mCore APIs, no Nintendo BIOS or game data.
 * Initial integration is deliberately silent (no AudioWorklet on HTTP).
 */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba-util/vfs.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define GBA_W 240u
#define GB_W 160u
#define GB_H 144u
#define GBA_H 160u
static struct mCore *emulator_core;
static uint8_t *rom_data;
/* mGBA 0.10.5 declares setVideoBuffer(..., color_t*, ...) in core.h. */
_Static_assert(sizeof(color_t) == 4, "mGBA must use 32-bit pixels");
static color_t video[GBA_W * GBA_H];
static uint8_t rgba[GBA_W * GBA_H * 4u];
static uint32_t key_bits;
static int core_ready;
static unsigned video_width = GBA_W, video_height = GBA_H;

void ssh_mgba_destroy(void) {
    if (emulator_core) {
        if (core_ready) {
            emulator_core->unloadROM(emulator_core);
            mCoreConfigDeinit(&emulator_core->config);
            emulator_core->deinit(emulator_core);
        }
        emulator_core = NULL;
    }
    free(rom_data);
    rom_data = NULL;
    key_bits = 0;
    core_ready = 0;
    video_width = GBA_W;
    video_height = GBA_H;
}

/* platform = 0 for Game Boy Advance, 1 for Game Boy / Color. */
int ssh_mgba_load(const uint8_t *rom, int size, int platform) {
    ssh_mgba_destroy();
    if (platform != 0 && platform != 1) return 0;
    if (!rom || size < (platform ? 0x150 : 0xc0) ||
        size > (platform ? (8 << 20) : (32 << 20))) return 0;
    rom_data = malloc((size_t)size);
    if (!rom_data) return 0;
    memcpy(rom_data, rom, (size_t)size);
    emulator_core = mCoreCreate(platform ? mPLATFORM_GB : mPLATFORM_GBA);
    if (!emulator_core) { ssh_mgba_destroy(); return 0; }
    mCoreInitConfig(emulator_core, NULL);
    if (!emulator_core->init(emulator_core)) {
        /* init failure path must not call unloadROM on an uninitialised core */
        emulator_core = NULL;
        ssh_mgba_destroy();
        return 0;
    }
    core_ready = 1;
    struct mCoreOptions opts = { .useBios = true, .skipBios = true, .volume = 0 };
    mCoreConfigLoadDefaults(&emulator_core->config, &opts);
    mCoreLoadConfig(emulator_core);
    emulator_core->setVideoBuffer(emulator_core, video, GBA_W);
    struct VFile *vf = VFileFromMemory(rom_data, (size_t)size);
    if (!vf) { ssh_mgba_destroy(); return 0; }
    if (!emulator_core->loadROM(emulator_core, vf)) {
        vf->close(vf);
        ssh_mgba_destroy();
        return 0;
    }
    emulator_core->reset(emulator_core);
    emulator_core->desiredVideoDimensions(emulator_core, &video_width, &video_height);
    if (!((video_width == GB_W && video_height == GB_H) ||
          (video_width == GBA_W && video_height == GBA_H))) {
        ssh_mgba_destroy();
        return 0;
    }
    return 1;
}

void ssh_mgba_frame(void) {
    if (!core_ready) return;
    emulator_core->runFrame(emulator_core);
    /* libmgba's 32-bit color_t uses low-byte red (COLOR_16_BIT disabled).
     * Set alpha explicitly: the buffer's fourth channel is reserved by mGBA. */
    /* The core renders with stride GBA_W for both GB and GBA.
     * Pack GB 160x144 tightly for the Canvas RGBA buffer. */
    for (unsigned y = 0; y < video_height; ++y) {
        for (unsigned x = 0; x < video_width; ++x) {
            size_t index = (size_t)y * video_width + x;
            uint32_t pixel = (uint32_t)video[(size_t)y * GBA_W + x];
            rgba[index*4]     = (uint8_t)(pixel);
            rgba[index*4 + 1] = (uint8_t)(pixel >> 8);
            rgba[index*4 + 2] = (uint8_t)(pixel >> 16);
            rgba[index*4 + 3] = 255;
        }
    }
}

const uint8_t *ssh_mgba_framebuffer(void) { return rgba; }
int ssh_mgba_width(void) { return (int)video_width; }
int ssh_mgba_height(void) { return (int)video_height; }
void ssh_mgba_key(int key, int pressed) {
    if (!core_ready || key < 0 || key > 9) return;
    if (pressed) key_bits |= (1u << key);
    else key_bits &= ~(1u << key);
    emulator_core->setKeys(emulator_core, key_bits);
}
/* savedataClone returns a heap allocation owned by caller. */
int ssh_mgba_save_size(void) {
    if (!core_ready) return 0;
    void *save = NULL;
    size_t n = emulator_core->savedataClone(emulator_core, &save);
    free(save);
    return n > 0 && n <= (256u << 10) ? (int)n : 0;
}
int ssh_mgba_save(uint8_t *dest, int capacity) {
    if (!core_ready || !dest || capacity <= 0) return -1;
    void *save = NULL;
    size_t n = emulator_core->savedataClone(emulator_core, &save);
    if (!save || n == 0 || n > (size_t)capacity || n > (256u << 10)) {
        free(save); return -1;
    }
    memcpy(dest, save, n);
    free(save);
    return (int)n;
}
int ssh_mgba_restore(const uint8_t *src, int size) {
    if (!core_ready || !src || size <= 0 || size > (256 << 10)) return 0;
    return emulator_core->savedataRestore(emulator_core, src, (size_t)size, true) ? 1 : 0;
}
