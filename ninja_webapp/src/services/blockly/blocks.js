/**
 * @file blocks.js
 * @description Custom Blockly blocks for NinjaRobot V5 hardware.
 * Covers: Servos, Display, Buzzer, Distance Sensor, Control
 */

import * as Blockly from 'blockly';

// ============================================
// MOTION BLOCKS (Servos)
// ============================================

Blockly.Blocks['ninja_servo_set'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Set servo')
            .appendField(new Blockly.FieldDropdown([
                ['1', '0'],
                ['2', '1'],
                ['3', '2'],
                ['4', '3'],
                ['5', '4'],
                ['6', '5'],
                ['7', '6'],
                ['8', '7']
            ]), 'SERVO');
        this.appendValueInput('ANGLE')
            .setCheck('Number')
            .appendField('to');
        this.appendDummyInput()
            .appendField('°');
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Set servo to a specific angle (0-180)');
    }
};

Blockly.Blocks['ninja_servo_sweep'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Sweep servo')
            .appendField(new Blockly.FieldDropdown([
                ['1', '0'],
                ['2', '1'],
                ['3', '2'],
                ['4', '3'],
                ['5', '4'],
                ['6', '5'],
                ['7', '6'],
                ['8', '7']
            ]), 'SERVO');
        this.appendValueInput('FROM')
            .setCheck('Number')
            .appendField('from');
        this.appendValueInput('TO')
            .setCheck('Number')
            .appendField('to');
        this.appendValueInput('SPEED')
            .setCheck('Number')
            .appendField('speed');
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Smoothly sweep servo from one angle to another');
    }
};

// ============================================
// DISPLAY BLOCKS (ST7789)
// ============================================

Blockly.Blocks['ninja_display_text'] = {
    init: function () {
        this.appendValueInput('TEXT')
            .setCheck('String')
            .appendField('Display text');
        this.appendValueInput('X')
            .setCheck('Number')
            .appendField('at X');
        this.appendValueInput('Y')
            .setCheck('Number')
            .appendField('Y');
        this.appendDummyInput()
            .appendField('color')
            .appendField(new Blockly.FieldTextInput('#FFFFFF'), 'COLOR'); // Using TextInput to avoid build error with FieldColour
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(290);
        this.setTooltip('Display text on the screen');
    }
};

Blockly.Blocks['ninja_display_clear'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Clear display');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(290);
        this.setTooltip('Clear the display screen');
    }
};

Blockly.Blocks['ninja_display_image'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Display image')
            .appendField(new Blockly.FieldDropdown([
                ['Star', 'star'],
                ['Heart', 'heart'],
                ['Happy', 'happy'],
                ['Sad', 'sad'],
                ['Robot', 'robot']
            ]), 'IMAGE');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(290);
        this.setTooltip('Display a preset image');
    }
};

// ============================================
// SENSOR BLOCKS (VL53L0X)
// ============================================

Blockly.Blocks['ninja_distance_read'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Read distance (mm)');
        this.setOutput(true, 'Number');
        this.setColour(210);
        this.setTooltip('Read distance from VL53L0X sensor in millimeters');
    }
};

// ============================================
// SOUND BLOCKS (Buzzer)
// ============================================

Blockly.Blocks['ninja_buzzer_tone'] = {
    init: function () {
        this.appendValueInput('FREQUENCY')
            .setCheck('Number')
            .appendField('Play tone at');
        this.appendValueInput('DURATION')
            .setCheck('Number')
            .appendField('Hz for');
        this.appendDummyInput()
            .appendField('ms');
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(330);
        this.setTooltip('Play a tone at specified frequency and duration');
    }
};

Blockly.Blocks['ninja_buzzer_melody'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Play melody')
            .appendField(new Blockly.FieldDropdown([
                ['Startup', 'startup'],
                ['Success', 'success'],
                ['Error', 'error'],
                ['Alert', 'alert'],
                ['Happy', 'happy']
            ]), 'MELODY');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(330);
        this.setTooltip('Play a preset melody');
    }
};

// ============================================
// CONTROL BLOCKS
// ============================================

Blockly.Blocks['ninja_wait'] = {
    init: function () {
        this.appendValueInput('SECONDS')
            .setCheck('Number')
            .appendField('Wait');
        this.appendDummyInput()
            .appendField('seconds');
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(120);
        this.setTooltip('Pause execution for a number of seconds');
    }
};

Blockly.Blocks['ninja_repeat'] = {
    init: function () {
        this.appendValueInput('TIMES')
            .setCheck('Number')
            .appendField('Repeat');
        this.appendDummyInput()
            .appendField('times');
        this.appendStatementInput('DO')
            .setCheck(null);
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(120);
        this.setTooltip('Repeat the enclosed blocks a number of times');
    }
};

export default Blockly.Blocks;
