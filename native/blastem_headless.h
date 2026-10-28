/* SmartSafeHub / Retro Arcade: optional BlastEm desktop-debugger stubs.
 * GPL-3.0-or-later. Included only in the BlastEm browser bridge translation
 * unit. Must agree with headers from the pinned upstream BlastEm checkout.
 * These stubs have no impact on emulation or its normal audio/video path.
 */
#ifndef SSH_BLASTEM_HEADLESS_H
#define SSH_BLASTEM_HEADLESS_H

#include "oscilloscope.h"
#include "nuklear_ui/debug_ui.h"

/* No standalone debug windows in the browser libretro frontend. */
uint8_t debug_create_window(uint8_t debug_type, char *caption,
                            uint32_t width, uint32_t height,
                            window_close_handler close_handler)
{
    (void)debug_type;
    (void)caption;
    (void)width;
    (void)height;
    (void)close_handler;
    return 0;
}

/* Only the debug oscilloscope's visual sample collection is disabled. */
void scope_add_sample(oscilloscope *scope, uint8_t channel, int16_t value,
                      uint8_t trigger)
{
    (void)scope;
    (void)channel;
    (void)value;
    (void)trigger;
}

#endif /* SSH_BLASTEM_HEADLESS_H */
