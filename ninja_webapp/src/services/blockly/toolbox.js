/**
 * @file toolbox.js
 * @description Blockly toolbox configuration for NinjaRobot.
 * Organized by category: Motion, Display, Sound, Sensors, Control
 */

export const toolbox = {
    kind: 'categoryToolbox',
    contents: [
        {
            kind: 'category',
            name: '🤖 Motion',
            colour: '160',
            contents: [
                { kind: 'block', type: 'ninja_servo_set' },
                { kind: 'block', type: 'ninja_servo_sweep' },
            ],
        },
        {
            kind: 'category',
            name: '📺 Display',
            colour: '290',
            contents: [
                { kind: 'block', type: 'ninja_display_text' },
                { kind: 'block', type: 'ninja_display_image' },
                { kind: 'block', type: 'ninja_display_clear' },
            ],
        },
        {
            kind: 'category',
            name: '🔊 Sound',
            colour: '330',
            contents: [
                { kind: 'block', type: 'ninja_buzzer_melody' },
                { kind: 'block', type: 'ninja_buzzer_tone' },
            ],
        },
        {
            kind: 'category',
            name: '📏 Sensors',
            colour: '210',
            contents: [
                { kind: 'block', type: 'ninja_distance_read' },
            ],
        },
        {
            kind: 'category',
            name: '🔁 Control',
            colour: '120',
            contents: [
                { kind: 'block', type: 'ninja_wait' },
                { kind: 'block', type: 'ninja_repeat' },
            ],
        },
        { kind: 'sep' },
        {
            kind: 'category',
            name: '📐 Math',
            colour: '230',
            contents: [
                { kind: 'block', type: 'math_number' },
                { kind: 'block', type: 'math_arithmetic' },
                { kind: 'block', type: 'math_random_int' },
            ],
        },
        {
            kind: 'category',
            name: '📝 Text',
            colour: '160',
            contents: [
                { kind: 'block', type: 'text' },
                { kind: 'block', type: 'text_join' },
            ],
        },
        {
            kind: 'category',
            name: '🔀 Logic',
            colour: '210',
            contents: [
                { kind: 'block', type: 'controls_if' },
                { kind: 'block', type: 'logic_compare' },
                { kind: 'block', type: 'logic_operation' },
                { kind: 'block', type: 'logic_boolean' },
            ],
        },
    ],
};
