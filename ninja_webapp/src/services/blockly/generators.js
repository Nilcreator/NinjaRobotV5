/**
 * @file generators.js
 * @description Python code generators for NinjaRobot blocks.
 * Generates code compatible with V5 RobotWrapper API.
 */

import { pythonGenerator, Order } from 'blockly/python';

// ============================================
// MOTION GENERATORS (Servos)
// ============================================

pythonGenerator.forBlock['ninja_servo_set'] = function (block) {
    const servoNum = block.getFieldValue('SERVO_NUM');
    const angle = block.getFieldValue('ANGLE');
    // V5 API: robot.servo is MultiServo, 0-indexed
    return `robot.servo[${servoNum - 1}].set_angle(${angle})\n`;
};

pythonGenerator.forBlock['ninja_servo_sweep'] = function (block) {
    const servoNum = block.getFieldValue('SERVO_NUM');
    const startAngle = pythonGenerator.valueToCode(block, 'START_ANGLE', Order.ATOMIC) || '0';
    const endAngle = pythonGenerator.valueToCode(block, 'END_ANGLE', Order.ATOMIC) || '180';
    const speed = pythonGenerator.valueToCode(block, 'SPEED', Order.ATOMIC) || '50';
    return `robot.servo[${servoNum - 1}].sweep(${startAngle}, ${endAngle}, ${speed})\n`;
};

// ============================================
// DISPLAY GENERATORS (ST7789)
// ============================================

pythonGenerator.forBlock['ninja_display_text'] = function (block) {
    const text = pythonGenerator.valueToCode(block, 'TEXT', Order.ATOMIC) || '""';
    const x = pythonGenerator.valueToCode(block, 'X', Order.ATOMIC) || '0';
    const y = pythonGenerator.valueToCode(block, 'Y', Order.ATOMIC) || '0';
    const color = block.getFieldValue('COLOR');
    // Convert hex to RGB tuple
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `robot.display.text(${text}, x=${x}, y=${y}, color=(${r}, ${g}, ${b}))\n`;
};

pythonGenerator.forBlock['ninja_display_clear'] = function () {
    return 'robot.display.clear()\n';
};

pythonGenerator.forBlock['ninja_display_image'] = function (block) {
    const image = block.getFieldValue('IMAGE');
    return `robot.display.image("${image}")\n`;
};

// ============================================
// SENSOR GENERATORS (VL53L0X)
// ============================================

pythonGenerator.forBlock['ninja_distance_read'] = function () {
    return ['robot.distance.read()', Order.FUNCTION_CALL];
};

// ============================================
// SOUND GENERATORS (Buzzer)
// ============================================

pythonGenerator.forBlock['ninja_buzzer_tone'] = function (block) {
    const frequency = pythonGenerator.valueToCode(block, 'FREQUENCY', Order.ATOMIC) || '440';
    const duration = pythonGenerator.valueToCode(block, 'DURATION', Order.ATOMIC) || '500';
    return `robot.buzzer.tone(${frequency}, ${duration})\n`;
};

pythonGenerator.forBlock['ninja_buzzer_melody'] = function (block) {
    const melody = block.getFieldValue('MELODY');
    return `robot.buzzer.play("${melody}")\n`;
};

// ============================================
// CONTROL GENERATORS
// ============================================

pythonGenerator.forBlock['ninja_wait'] = function (block) {
    const seconds = pythonGenerator.valueToCode(block, 'SECONDS', Order.ATOMIC) || '1';
    return `time.sleep(${seconds})\n`;
};

pythonGenerator.forBlock['ninja_repeat'] = function (block) {
    const times = pythonGenerator.valueToCode(block, 'TIMES', Order.ATOMIC) || '10';
    const statements = pythonGenerator.statementToCode(block, 'DO');
    return `for _ in range(int(${times})):\n${statements || '    pass\n'}`;
};

export { pythonGenerator };
