/**
 * NinjaRobot Custom Blocks for Blockly (v12+ compatible)
 * Defines all hardware-specific blocks for the NinjaRobot V5
 */
import * as Blockly from 'blockly';

// In Blockly v12+, some fields require explicit registration
// We use FieldNumber for angles instead of deprecated FieldAngle

// ============================================
// MOTION BLOCKS (Servos)
// ============================================

Blockly.Blocks['ninja_servo_set'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Set Servo')
            .appendField(new Blockly.FieldNumber(1, 1, 8, 1), 'SERVO_NUM')
            .appendField('to angle')
            .appendField(new Blockly.FieldNumber(90, 0, 180, 1), 'ANGLE')
            .appendField('°');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Set a servo motor to a specific angle (0-180°)');
        this.setHelpUrl('');
    }
};

Blockly.Blocks['ninja_servo_sweep'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Sweep Servo')
            .appendField(new Blockly.FieldNumber(1, 1, 8, 1), 'SERVO_NUM');
        this.appendValueInput('START_ANGLE')
            .setCheck('Number')
            .appendField('from');
        this.appendValueInput('END_ANGLE')
            .setCheck('Number')
            .appendField('to');
        this.appendValueInput('SPEED')
            .setCheck('Number')
            .appendField('speed');
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Smoothly move a servo from one angle to another');
        this.setHelpUrl('');
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
            .appendField(new Blockly.FieldDropdown([
                ['White', '#FFFFFF'],
                ['Red', '#FF0000'],
                ['Green', '#00FF00'],
                ['Blue', '#0000FF'],
                ['Yellow', '#FFFF00'],
                ['Cyan', '#00FFFF'],
                ['Magenta', '#FF00FF'],
                ['Orange', '#FF8A00']
            ]), 'COLOR');
        this.setInputsInline(true);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(290);
        this.setTooltip('Display text on the robot screen');
        this.setHelpUrl('');
    }
};

Blockly.Blocks['ninja_display_clear'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Clear display');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(290);
        this.setTooltip('Clear the robot display screen');
        this.setHelpUrl('');
    }
};

Blockly.Blocks['ninja_display_image'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Show image')
            .appendField(new Blockly.FieldDropdown([
                ['Happy', 'happy'],
                ['Sad', 'sad'],
                ['Angry', 'angry'],
                ['Surprised', 'surprised'],
                ['Heart', 'heart'],
                ['Star', 'star']
            ]), 'IMAGE');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(290);
        this.setTooltip('Display a preset image/expression');
        this.setHelpUrl('');
    }
};

// ============================================
// SENSOR BLOCKS (VL53L0X)
// ============================================

Blockly.Blocks['ninja_distance_read'] = {
    init: function () {
        this.appendDummyInput()
            .appendField('Distance (mm)');
        this.setOutput(true, 'Number');
        this.setColour(210);
        this.setTooltip('Read distance from the ToF sensor in millimeters');
        this.setHelpUrl('');
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
        this.setHelpUrl('');
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
        this.setHelpUrl('');
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
        this.setHelpUrl('');
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
        this.setHelpUrl('');
    }
};

export default Blockly.Blocks;
