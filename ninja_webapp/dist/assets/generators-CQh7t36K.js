import{p as o,O as t}from"./index-DfY-MttO.js";o.forBlock.ninja_servo_set=function(e){const n=e.getFieldValue("SERVO"),r=o.valueToCode(e,"ANGLE",t.ATOMIC)||"90";return`robot.servo[${n}].set_angle(${r})
`};o.forBlock.ninja_servo_sweep=function(e){const n=e.getFieldValue("SERVO"),r=o.valueToCode(e,"FROM",t.ATOMIC)||"0",s=o.valueToCode(e,"TO",t.ATOMIC)||"180",a=o.valueToCode(e,"SPEED",t.ATOMIC)||"50";return`robot.servo[${n}].sweep(${r}, ${s}, ${a})
`};o.forBlock.ninja_display_text=function(e){const n=o.valueToCode(e,"TEXT",t.ATOMIC)||'""',r=o.valueToCode(e,"X",t.ATOMIC)||"0",s=o.valueToCode(e,"Y",t.ATOMIC)||"0",a=e.getFieldValue("COLOR"),i=parseInt(a.slice(1,3),16),l=parseInt(a.slice(3,5),16),c=parseInt(a.slice(5,7),16);return`robot.display.text(${n}, x=${r}, y=${s}, color=(${i}, ${l}, ${c}))
`};o.forBlock.ninja_display_clear=function(){return`robot.display.clear()
`};o.forBlock.ninja_display_image=function(e){return`robot.display.image("${e.getFieldValue("IMAGE")}")
`};o.forBlock.ninja_distance_read=function(){return["robot.distance.read()",t.FUNCTION_CALL]};o.forBlock.ninja_buzzer_tone=function(e){const n=o.valueToCode(e,"FREQUENCY",t.ATOMIC)||"440",r=o.valueToCode(e,"DURATION",t.ATOMIC)||"500";return`robot.buzzer.tone(${n}, ${r})
`};o.forBlock.ninja_buzzer_melody=function(e){return`robot.buzzer.play("${e.getFieldValue("MELODY")}")
`};o.forBlock.ninja_wait=function(e){return`time.sleep(${o.valueToCode(e,"SECONDS",t.ATOMIC)||"1"})
`};o.forBlock.ninja_repeat=function(e){const n=o.valueToCode(e,"TIMES",t.ATOMIC)||"10",r=o.statementToCode(e,"DO");return`for _ in range(int(${n})):
${r||`    pass
`}`};export{o as pythonGenerator};
