import{p as n,O as t}from"./index-DxjDtQRL.js";n.forBlock.ninja_servo_set=function(e){const o=e.getFieldValue("SERVO_NUM"),r=e.getFieldValue("ANGLE");return`robot.servo[${o-1}].set_angle(${r})
`};n.forBlock.ninja_servo_sweep=function(e){const o=e.getFieldValue("SERVO_NUM"),r=n.valueToCode(e,"START_ANGLE",t.ATOMIC)||"0",s=n.valueToCode(e,"END_ANGLE",t.ATOMIC)||"180",a=n.valueToCode(e,"SPEED",t.ATOMIC)||"50";return`robot.servo[${o-1}].sweep(${r}, ${s}, ${a})
`};n.forBlock.ninja_display_text=function(e){const o=n.valueToCode(e,"TEXT",t.ATOMIC)||'""',r=n.valueToCode(e,"X",t.ATOMIC)||"0",s=n.valueToCode(e,"Y",t.ATOMIC)||"0",a=e.getFieldValue("COLOR"),i=parseInt(a.slice(1,3),16),l=parseInt(a.slice(3,5),16),u=parseInt(a.slice(5,7),16);return`robot.display.text(${o}, x=${r}, y=${s}, color=(${i}, ${l}, ${u}))
`};n.forBlock.ninja_display_clear=function(){return`robot.display.clear()
`};n.forBlock.ninja_display_image=function(e){return`robot.display.image("${e.getFieldValue("IMAGE")}")
`};n.forBlock.ninja_distance_read=function(){return["robot.distance.read()",t.FUNCTION_CALL]};n.forBlock.ninja_buzzer_tone=function(e){const o=n.valueToCode(e,"FREQUENCY",t.ATOMIC)||"440",r=n.valueToCode(e,"DURATION",t.ATOMIC)||"500";return`robot.buzzer.tone(${o}, ${r})
`};n.forBlock.ninja_buzzer_melody=function(e){return`robot.buzzer.play("${e.getFieldValue("MELODY")}")
`};n.forBlock.ninja_wait=function(e){return`time.sleep(${n.valueToCode(e,"SECONDS",t.ATOMIC)||"1"})
`};n.forBlock.ninja_repeat=function(e){const o=n.valueToCode(e,"TIMES",t.ATOMIC)||"10",r=n.statementToCode(e,"DO");return`for _ in range(int(${o})):
${r||`    pass
`}`};export{n as pythonGenerator};
