/* SmartSafeHub Sega browser libretro host; GPL-3.0-or-later.
 * The libretro API header is supplied by the exact locally checked-out core.
 * No proprietary firmware or game images are part of this bridge.
 */
#include "libretro.h"
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#define SSH_MAX_WIDTH 1024u
#define SSH_MAX_HEIGHT 512u
#define SSH_AUDIO_CAPACITY 16384u
static uint8_t pixels[SSH_MAX_WIDTH * SSH_MAX_HEIGHT * 4u];
static int16_t samples[SSH_AUDIO_CAPACITY * 2u];
static unsigned audio_read, audio_write;
static unsigned frame_width, frame_height, pixel_format = RETRO_PIXEL_FORMAT_0RGB1555;
static unsigned joypad;
static int initialized, loaded;
static void *rom_copy;
static size_t rom_size;
static double fps = 60.0, rate = 44100.0;

static void on_video(const void *data, unsigned width, unsigned height, size_t pitch) {
    if (!data || width == 0 || height == 0 || width > SSH_MAX_WIDTH || height > SSH_MAX_HEIGHT) return;
    const unsigned bpp = pixel_format == RETRO_PIXEL_FORMAT_XRGB8888 ? 4 : 2;
    if (pitch < width * bpp || pitch > (SSH_MAX_WIDTH * 8u)) return;
    const uint8_t *row = data;
    for (unsigned y = 0; y < height; y++, row += pitch) {
        for (unsigned x = 0; x < width; x++) {
            const unsigned idx = (y * width + x) * 4u;
            unsigned r, g, b;
            if (bpp == 4) {
                uint32_t p;
                memcpy(&p, row + x * 4u, 4u);
                r = (p >> 16) & 255; g = (p >> 8) & 255; b = p & 255;
            } else {
                uint16_t p;
                memcpy(&p, row + x * 2u, 2u);
                if (pixel_format == RETRO_PIXEL_FORMAT_RGB565) {
                    r = ((p >> 11) & 31) * 255 / 31;
                    g = ((p >> 5) & 63) * 255 / 63;
                    b = (p & 31) * 255 / 31;
                } else {
                    r = ((p >> 10) & 31) * 255 / 31;
                    g = ((p >> 5) & 31) * 255 / 31;
                    b = (p & 31) * 255 / 31;
                }
            }
            pixels[idx] = (uint8_t)r; pixels[idx + 1] = (uint8_t)g;
            pixels[idx + 2] = (uint8_t)b; pixels[idx + 3] = 255;
        }
    }
    frame_width = width; frame_height = height;
}
static void on_audio(int16_t left, int16_t right) {
    unsigned next = (audio_write + 1u) % SSH_AUDIO_CAPACITY;
    if (next == audio_read) audio_read = (audio_read + 1u) % SSH_AUDIO_CAPACITY;
    samples[audio_write * 2u] = left;
    samples[audio_write * 2u + 1u] = right;
    audio_write = next;
}
static size_t on_audio_batch(const int16_t *data, size_t frames) {
    for (size_t i = 0; i < frames; i++) on_audio(data[i * 2u], data[i * 2u + 1u]);
    return frames;
}
static void on_input_poll(void) {}
static int16_t on_input_state(unsigned port, unsigned device, unsigned index, unsigned id) {
    if (port || device != RETRO_DEVICE_JOYPAD || index || id >= 16) return 0;
    return (joypad & (1u << id)) != 0;
}
static bool on_environment(unsigned command, void *data) {
    switch (command) {
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
        if (!data) return false;
        if (*(const enum retro_pixel_format *)data > RETRO_PIXEL_FORMAT_RGB565) return false;
        pixel_format = *(const enum retro_pixel_format *)data;
        return true;
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
    case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
        if (!data) return false;
        *(const char **)data = "/tmp";
        return true;
    case RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME: return true;
    case RETRO_ENVIRONMENT_GET_CAN_DUPE:
        if (!data) return false;
        *(bool *)data = true;
        return true;
    case RETRO_ENVIRONMENT_GET_OVERSCAN:
        if (!data) return false;
        *(bool *)data = false;
        return true;
    case RETRO_ENVIRONMENT_SET_GEOMETRY: return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
        if (!data) return false;
        *(bool *)data = false;
        return true;
    case RETRO_ENVIRONMENT_GET_LANGUAGE:
        if (!data) return false;
        *(unsigned *)data = RETRO_LANGUAGE_ENGLISH;
        return true;
    default: return false;
    }
}
int ssh_retro_init(void) {
    if (initialized) return 1;
    if (retro_api_version() != RETRO_API_VERSION) return 0;
    retro_set_environment(on_environment);
    retro_set_video_refresh(on_video);
    retro_set_audio_sample(on_audio);
    retro_set_audio_sample_batch(on_audio_batch);
    retro_set_input_poll(on_input_poll);
    retro_set_input_state(on_input_state);
    retro_init(); initialized = 1; return 1;
}
/* kind: 1=.gg, 2=.sms, 3=.sg, 4=.gen (never derived from untrusted JS string) */
int ssh_retro_load(const uint8_t *rom, unsigned length, int kind) {
    if (!initialized || loaded || !rom || length < 64 || length > 8u * 1024u * 1024u || kind < 1 || kind > 4) return 0;
    static const char *paths[] = {"", "/tmp/game.gg", "/tmp/game.sms", "/tmp/game.sg", "/tmp/game.gen"};
    rom_copy = malloc(length);
    if (!rom_copy) return 0;
    memcpy(rom_copy, rom, length); rom_size = length;
    struct retro_game_info info = { paths[kind], rom_copy, rom_size, NULL };
    frame_width = frame_height = joypad = audio_read = audio_write = 0;
    if (!retro_load_game(&info)) { free(rom_copy); rom_copy = NULL; rom_size = 0; return 0; }
    loaded = 1;
    struct retro_system_av_info av;
    memset(&av, 0, sizeof(av)); retro_get_system_av_info(&av);
    if (av.timing.fps >= 30 && av.timing.fps <= 120) fps = av.timing.fps;
    if (av.timing.sample_rate >= 8000 && av.timing.sample_rate <= 192000) rate = av.timing.sample_rate;
    return 1;
}
void ssh_retro_run(void) { if (loaded) retro_run(); }
void ssh_retro_key(int id, int down) { if (id >= 0 && id < 16) { if (down) joypad |= 1u << id; else joypad &= ~(1u << id); } }
unsigned ssh_retro_width(void) { return frame_width; }
unsigned ssh_retro_height(void) { return frame_height; }
const uint8_t *ssh_retro_pixels(void) { return pixels; }
unsigned ssh_retro_fps_milli(void) { return (unsigned)(fps * 1000.0 + 0.5); }
unsigned ssh_retro_audio_rate(void) { return (unsigned)(rate + 0.5); }
/* Returned pointer is valid until next call. JS must copy before the next frame. */
const int16_t *ssh_retro_audio(unsigned max_frames, unsigned *out_frames) {
    static int16_t chunk[2048 * 2];
    unsigned count = 0;
    if (!out_frames) return NULL;
    if (max_frames > 2048u) max_frames = 2048u;
    while (count < max_frames && audio_read != audio_write) {
        chunk[count * 2u] = samples[audio_read * 2u];
        chunk[count * 2u + 1u] = samples[audio_read * 2u + 1u];
        audio_read = (audio_read + 1u) % SSH_AUDIO_CAPACITY;
        count++;
    }
    *out_frames = count;
    return chunk;
}
unsigned ssh_retro_save_size(void) {
    if (!loaded) return 0;
    size_t size = retro_get_memory_size(RETRO_MEMORY_SAVE_RAM);
    return size <= 256u * 1024u ? (unsigned)size : 0;
}
unsigned ssh_retro_save(uint8_t *dst, unsigned capacity) {
    unsigned size = ssh_retro_save_size();
    void *src = retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
    if (!src || !dst || !size || size > capacity) return 0;
    memcpy(dst, src, size); return size;
}
int ssh_retro_restore(const uint8_t *src, unsigned size) {
    unsigned expected = ssh_retro_save_size();
    void *dst = retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
    if (!dst || !src || !expected || size != expected) return 0;
    memcpy(dst, src, size); return 1;
}
void ssh_retro_destroy(void) {
    if (loaded) { retro_unload_game(); loaded = 0; }
    if (initialized) { retro_deinit(); initialized = 0; }
    free(rom_copy); rom_copy = NULL; rom_size = 0;
    joypad = audio_read = audio_write = 0;
}
