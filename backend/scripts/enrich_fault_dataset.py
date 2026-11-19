"""
Enriches AutoMech-AI dataset with:
1. Fault-specific diagnostic questions (followup_question), confirming_keywords, and ruling_out_keywords for all 177 canonical faults.
2. Rich natural-language symptom expansions (colloquial, mechanic terms, Indian automotive terminology, OBD-II descriptions) -> 3,500+ unique training patterns.
3. Maps all HuggingFace & Kaggle internet dataset entries to canonical faults so zero generic 'OBD Pxxxx' classes dilute the ML probability distribution.
"""
import os
import re
import csv
import random
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Fault-specific diagnostic decision-tree metadata:
# Maps canonical fault_name -> (followup_question, confirming_keywords, ruling_out_keywords)
FAULT_DIAGNOSTIC_META = {
    # ─── ENGINE ───
    "Connecting Rod Bearing Failure": (
        "Is it a deep metallic rhythmic knock from the bottom of the engine that gets louder as RPM increases, and is the oil pressure light flickering?",
        "deep metallic knock,bottom of engine,louder with rpm,oil pressure light,accelerating,under load,crankcase,rod",
        "only on cold start,top of engine,squealing,whining,only over bumps"
    ),
    "Worn Piston Rings": (
        "Is there thick blue-grey exhaust smoke when accelerating, along with high engine oil consumption and blow-by smoke from the oil filler cap?",
        "blue smoke,grey smoke,burning oil,oil level dropping,oil consumption,blow by,exhaust smoke accelerating,compression low",
        "white smoke,coolant dropping,black smoke,only on cold start for 2 seconds"
    ),
    "Head Gasket Failure": (
        "Are you seeing thick white sweet-smelling exhaust smoke, a milky mayonnaise-like sludge under the oil cap, or bubbles in the coolant reservoir?",
        "white smoke,milky oil,mayonnaise under oil cap,coolant level dropping,overheating,bubbles in radiator,sweet smell exhaust",
        "blue smoke,black smoke,no overheating,external hose leak only"
    ),
    "Vacuum Leak": (
        "Do you hear a hissing sound from the engine bay, and does the rough idle smooth out as soon as you press the accelerator pedal?",
        "hissing sound,smooths out when accelerating,high idle rpm,rough idle only,lean code,p0171,p0174,vacuum hose",
        "vibrates in drive with brakes held,clunk when shifting,stalls at highway speed"
    ),
    "Starter Motor Failure": (
        "When you turn the key, do the dashboard lights and headlights stay bright while you hear a single loud click (or nothing) from the starter?",
        "single click,lights stay bright,battery voltage good,12.6v,tapping starter helps,solenoid click,no crank bright lights",
        "headlights dim,dashboard flickers and dies,rapid machine gun clicking,dead battery,engine cranks normally"
    ),
    "Fuel Pump Failure": (
        "When you turn the ignition key to ON (before cranking), do you fail to hear the 2-second humming prime sound from the rear fuel tank while the engine cranks strongly?",
        "cranks normally but wont start,no humming sound from fuel tank,no fuel pressure,fuel pump not priming,p0230,p0231,turns over fast",
        "no crank,clicking sound,dead battery,strong petrol smell leaking"
    ),
    "Ignition Coil Failure": (
        "Is the Check Engine Light flashing under acceleration with a sharp cylinder misfire/jerking and an OBD code like P0301–P0304?",
        "flashing check engine light,cel blinking,jerking on acceleration,single cylinder misfire,p0300,p0301,p0302,p0303,p0304,coil pack",
        "only in wet rain weather,no check engine light,smooth acceleration"
    ),
    "Worn Spark Plugs": (
        "Has it been over 30,000 km since the spark plugs were changed, with sluggish cold starts, mild hesitation, and a gradual drop in fuel mileage?",
        "old spark plugs,gradual drop in mileage,hard cold start,sluggish acceleration,electrode gap worn,minor misfire",
        "sudden total stall,flashing cel,loud metallic knock"
    ),
    "Thermostat Stuck Closed": (
        "Does the engine overheat within 10–15 minutes even on the highway, while the upper radiator hose is scalding hot and the lower hose stays cool?",
        "overheats on highway,upper hose hot lower hose cold,temperature gauge in red fast,no coolant circulation,p0128,boiling in traffic and highway",
        "only overheats in slow traffic with fan off,engine running too cold,visible green puddle under radiator"
    ),
    "Timing Chain Tensioner Failure": (
        "Is there a metallic chain rattling sound from the front timing cover for the first few seconds on a cold morning start that quiets down once oil pressure builds?",
        "cold start rattle,front of engine timing cover,metallic chain slap,goes away when warm,p0016,p0017,chain stretched",
        "deep bottom knock under load,rubber belt squeal,constant humming at highway speed"
    ),
    "Valve Cover Gasket Leak": (
        "Do you see dark engine oil seeping around the top valve cover edge and smell burnt oil when it drips onto the hot exhaust manifold?",
        "oil on top of engine,burning oil smell from bonnet,oil on exhaust manifold,wet around valve cover bolts,spark plug wells oily",
        "coolant puddle,blue smoke from tailpipe,gear oil under transmission"
    ),
    "Hydraulic Lifter Noise": (
        "Is there a fast, light metallic ticking or tapping sound from the top cylinder head area that speeds up with engine RPM?",
        "top of engine ticking,tapping from cylinder head,lifter tap,valvetrain clicking,faster with rpm,top end tap",
        "deep bottom knock,chain rattle only on startup,squealing belt"
    ),
    "Serpentine Belt Worn": (
        "Is there a high-pitched rubber squealing or chirping sound from the front accessory belt on startup, when turning on the AC, or in wet weather?",
        "high pitched squeal,rubber belt noise,worse in rain or ac on,cracks on ribs,glazed belt,front pulley squeak",
        "metallic grinding,deep engine knock,squeal only when pressing brake pedal"
    ),
    "Clogged Air Filter": (
        "Does the engine feel choked and sluggish when climbing hills or at full throttle, and does the air filter element look dark and clogged with dust?",
        "sluggish uphill,choked acceleration,dirty air filter,dust clogged,gradual power loss,p0101",
        "check engine flashing misfire,turbo whistle loud,stalling randomly"
    ),
    "Engine Mount Failure": (
        "Do you feel strong vibrations through the steering wheel and cabin floor at idle (especially in Drive/Reverse), or hear a thud when blipping the throttle?",
        "vibration in steering and seat at idle,thud when shifting to drive,engine rocking excessively,rubber mount cracked,stationary shake",
        "rpm fluctuating up and down,hissing sound,misfire codes"
    ),
    "Crankshaft Position Sensor Failure": (
        "Does the engine suddenly cut out while driving once hot, refuse to restart immediately, and then start fine after cooling down for 20 minutes?",
        "stalls when hot,restarts after cooling down,tachometer drops to zero,p0335,p0336,random shutdown while driving,no spark when hot",
        "sputters with low fuel,battery dead,only rough idle"
    ),
    "Fuel Injector Leaking": (
        "Are you seeing black exhaust smoke, a raw unburnt fuel smell at the tailpipe, hard hot-restarts, and a sharp drop in mileage?",
        "black smoke from exhaust,unburnt fuel smell tailpipe,rich fuel trim,hard start when hot,excessive fuel consumption,p0201,p0202",
        "blue smoke,white coolant smoke,lean code p0171"
    ),
    "Turbocharger Failure": (
        "Is there a loud siren/whining noise or metallic screech from the turbo, a sudden loss of boost power above 2000 RPM, and thick smoke from the exhaust?",
        "no turbo boost,loud turbo whistle siren,loss of power on diesel suv,p0299,underboost,oil in intercooler,shaft play",
        "Belt squeal at idle,normal power on highway,rough idle only"
    ),
    "Idle Air Control Valve Fault": (
        "Does the tachometer RPM needle hunt up and down continuously between 600 and 1500 RPM on its own while the car is idling in neutral?",
        "rpm hunting up and down,fluctuating idle speed,surging at idle,stalls when releasing throttle,p0505,p0506,iac valve",
        "steady vibration with stable rpm,only vibrates at 80 kmph"
    ),
    "Oil Pump Wear": (
        "Is the red low-oil-pressure warning light staying on or flickering at warm idle even though the dipstick shows the oil level is full?",
        "red oil pressure warning light on,oil level full on dipstick,low oil pressure gauge,p0520,p0521,top end noisy from oil starvation",
        "oil level empty on dipstick,oil leaking externally only"
    ),
    "Glow Plug Failure": (
        "Does your diesel engine crank for a long time before starting on cold mornings, emit a puff of white unburnt diesel smoke, and show the coil/glow-plug light?",
        "diesel hard start in morning,cold weather long crank,glow plug coil light stays on,p0380,p0381,rough for 30 seconds cold",
        "petrol car,wont crank at all,stalls when hot on highway"
    ),
    "Alternator Bearing Failure": (
        "Is there a dry whirring, growling, or whining sound coming directly from the alternator housing that rises in pitch with engine RPM?",
        "whining from alternator housing,bearing growl proportional to rpm,noisy alternator pulley,dry bearing sound",
        "belt rubber squeal in rain,turbo whistle under boost,wheel bearing hum with vehicle speed"
    ),
    "Water Pump Failure": (
        "Do you see coolant dripping from the front timing-cover/pulley area (weep hole) accompanied by a grinding sound from the water pump pulley?",
        "coolant leaking from front engine pulley,water pump weep hole drip,grinding noise from water pump bearing,play in water pump pulley",
        "leak at rear wheel,radiator front stone hit,heater core wet carpet inside"
    ),
    "EGR Valve Stuck Open": (
        "Does the engine idle roughly or stall at low speeds as if coughing on exhaust gas, with Check Engine codes P0401/P0402 and black diesel soot?",
        "rough idle stalling low speed,egr code p0401 p0402,soot buildup,hesitation at light throttle,exhaust gas recirculation stuck",
        "high rpm hunting,overheating coolant loss"
    ),
    "Intake Valve Timing Issue": (
        "Is the engine backfiring or popping through the air intake manifold on acceleration with VVT solenoid codes P0011 or P0012?",
        "backfiring through intake,popping sound air box,vvt solenoid code p0011 p0012,cam timing over advanced,loss of mid range power",
        "exhaust tailpipe pop on deceleration only,chain rattle cold start only"
    ),
    "Valve Stem Seal Leak": (
        "Do you see a distinct puff of blue oil smoke from the exhaust right on morning startup or after idling at a traffic light, which clears up once driving?",
        "puff of blue smoke on startup,blue smoke after idling at signal,clears up while cruising,burning oil smell no external leak",
        "constant thick blue smoke under full load,white sweet smoke"
    ),
    "Ignition Lead Moisture": (
        "Does the engine misfire and hesitate specifically during heavy rain, high humidity, or right after washing the car?",
        "misfiring in rain,wet weather hesitation,after car wash misfire,arcing spark plug wires,damp ignition leads",
        "misfires every day in dry hot weather"
    ),
    "Exhaust Valve Not Seating": (
        "Do you hear a regular popping sound at the exhaust tailpipe on deceleration and measure low compression on one cylinder?",
        "exhaust popping on deceleration,burnt exhaust valve,low compression one cylinder,uneven exhaust pulse at tailpipe",
        "popping from front air filter intake"
    ),
    "Radiator Fan Relay Failure": (
        "Does the car overheat ONLY while stuck in slow traffic or idling, but cool right back down to normal as soon as you drive at highway speed?",
        "overheats only in traffic,normal temperature on highway,cooling fan not turning on at idle,fan relay dead",
        "overheats on highway too,coolant hose burst"
    ),
    "Catalytic Converter Efficiency Low": (
        "Did the car fail the PUC emission test with high CO/HC readings and trigger Check Engine code P0420 without any loud exhaust rattle?",
        "failed emission test,high co hc emissions,p0420 catalyst efficiency below threshold,puc fail check engine light",
        "loud metallic rattle inside catalytic converter,complete power loss"
    ),
    "Diesel Cold Start Normal or Glow Plug Slow": (
        "Does your diesel car puff a small amount of white smoke for 5–10 seconds on a cold morning start and then run completely clean once warm?",
        "white smoke only on cold start diesel,clears up in 10 seconds,slow heating glow plug,morning start puff",
        "continuous white smoke when hot,coolant level dropping"
    ),
    "Idler Pulley Bearing Failure": (
        "Is there a constant dry grinding or chirping noise from the accessory belt idler/tensioner pulley area even when the alternator and AC are healthy?",
        "grinding from idler pulley,accessory belt tensioner pulley noise,chirping pulley bearing,front belt pulley play",
        "deep engine block knock,squealing brakes"
    ),

    # ─── TRANSMISSION ───
    "Clutch Plate Worn": (
        "When you press the accelerator in 3rd or 4th gear, does the engine RPM shoot up loudly while the car's actual road speed barely increases, with a high clutch pedal bite point?",
        "rpm rises but speed doesnt increase,clutch slipping in high gear,high bite point,burning clutch smell uphill,loss of acceleration",
        "pedal stuck to floor,grinding noise when moving gear stick,automatic transmission car"
    ),
    "Clutch Cable Stretched or Broken": (
        "Does the gear lever feel very stiff and resist going into 1st or Reverse even with the clutch pedal pressed all the way down (in a cable-clutch car)?",
        "hard to put in first and reverse,stiff gear shift,clutch cable frayed or stretched,excessive pedal free play,cable clutch",
        "rpm flares up in high gear,hydraulic fluid leaking under pedal"
    ),
    "Synchronizer Ring Wear": (
        "Do you hear a harsh metallic crunch or grinding sound specifically when shifting into a particular gear (like 2nd to 3rd), while other gears shift smoothly?",
        "crunching into specific gear,grinding when shifting 2nd to 3rd,double clutching helps,synchro ring worn,gearbox crunch",
        "hard to engage all gears from standstill,clutch slipping high rpm"
    ),
    "Worn Gear Fork or Detent": (
        "Does the gear lever violently pop or jump back out into neutral on its own while driving under load or decelerating?",
        "gear pops out into neutral,jumps out of gear while driving,third gear disengages on its own,worn shift fork detent spring",
        "crunching noise only during shift,clutch pedal spongy"
    ),
    "Flywheel Surface Damaged": (
        "Does the whole car shudder and judder violently through the floorboard as you slowly release the clutch pedal to move off in 1st gear?",
        "shudder when releasing clutch in first gear,clutch judder from standstill,chattering engagement,warped or hot spotted flywheel",
        "vibration at constant 90 kmph highway speed,vibration at idle in neutral"
    ),
    "Gearbox Oil Seal Leak": (
        "Do you see thick, pungent-smelling amber/brown gear oil dripping from where the driveshafts meet the transmission housing?",
        "gear oil dripping under gearbox,pungent thick oil leak at axle seal,transmission housing wet,output shaft seal leak",
        "green coolant leak,thin black engine oil from top valve cover"
    ),
    "Automatic Transmission Fluid Low or Degraded": (
        "In your torque-converter automatic car, are gear shifts delayed, flaring, or jerking harshly with dark/burnt ATF fluid and codes P0700/P0730?",
        "automatic transmission jerking between gears,delayed shift automatic,burnt dark atf fluid,p0700,p0730,slipping automatic",
        "manual clutch pedal car,cvt rubber belt whine"
    ),
    "CVT Belt or Fluid Degradation": (
        "In your CVT automatic car, do you feel a rubber-band shudder or high-pitched metallic whine under light acceleration at low speeds (20–50 km/h)?",
        "cvt judder at low speed,cvt whining noise,shuddering continuous variable transmission,p0868,honda city baleno magnite cvt",
        "manual gearbox,distinct gear shift clunk"
    ),
    "Differential Bearing Wear": (
        "Is there a continuous howling or humming whine coming from the rear axle/differential area that changes pitch between acceleration and coasting?",
        "howling from rear differential,humming noise rear axle rwd suv,changes pitch on coast vs throttle,diff bearing whine",
        "noise changes when swerving left and right at front wheel,engine rpm whine when parked"
    ),
    "Driveshaft Universal Joint Failure": (
        "Do you hear a metallic clank underneath the SUV when shifting from Drive to Reverse, followed by an underbody vibration above 70–80 km/h?",
        "clank when shifting drive to reverse,vibration under floorboard at 80 kmph,propeller shaft u joint play,rwd driveshaft shudder",
        "steering wheel shake only when braking,engine misfire at idle"
    ),
    "Reverse Idler Gear Wear": (
        "Does the gearbox grind loudly or refuse to slot into Reverse gear specifically, even when the vehicle is at a complete stop?",
        "grinding only in reverse gear,reverse gear wont engage,clicking in reverse,reverse idler gear teeth worn",
        "all forward gears also stiff,automatic car"
    ),
    "Clutch Master Cylinder Failure": (
        "Does the clutch pedal feel completely spongy, sink to the floor without returning, or show wet brake/clutch fluid leaking near the pedal firewall?",
        "clutch pedal stays on floor,spongy clutch pedal no resistance,clutch fluid level low,hydraulic clutch not disengaging",
        "stiff heavy clutch pedal,clutch slipping in 4th gear"
    ),
    "Clutch Damper Spring Weak": (
        "Does the car jerk back and forth in low-speed bumper-to-bumper traffic in 1st or 2nd gear with rattling damper springs in the clutch disc?",
        "jerking in 1st gear low speed traffic,rattling clutch damper springs,driveline snatch on light throttle",
        "slipping at high speed,pedal stuck down"
    ),
    "Low ATF Causing Clutch Pack Slip": (
        "When you shift your automatic car from Park into Drive or Reverse, is there a 3–5 second delay before the car actually engages and moves?",
        "delayed engagement into drive or reverse,automatic car wont move immediately in D,low atf level,clutch pack slip p0700",
        "manual transmission,instant engagement"
    ),
    "Gearbox Input Shaft Bearing Noise": (
        "Is there a whirring or rumbling noise from the manual gearbox while idling in Neutral that completely disappears as soon as you press the clutch pedal down?",
        "noise in neutral goes away when clutch pressed,whirring in neutral clutch out,quiet when clutch pedal depressed,input shaft bearing",
        "noise only appears WHEN clutch pedal is pressed (release bearing)"
    ),

    # ─── BRAKES ───
    "Brake Pads Worn": (
        "Do you hear a high-pitched metallic squealing or screeching from the wheels (wear indicator tab) specifically when pressing the brake pedal?",
        "high pitched squeal when braking,squeaking brake wear indicator,pad lining thin below 3mm,screech on light braking",
        "harsh metal on metal grinding,pedal sinking to floor,noise only when not braking"
    ),
    "Brake Disc Worn Below Minimum": (
        "Has the brake noise turned into a harsh, loud metal-on-metal grinding and scraping sound when braking, with deep grooves or a lip on the brake rotor?",
        "harsh metal on metal grinding when braking,scraping rotor,deep grooves on brake disc,backing plate hitting rotor",
        "light morning squeak that goes away,soft pedal no noise"
    ),
    "Air in Brake Lines or Master Cylinder Fail": (
        "Does the brake pedal feel soft and spongy and slowly sink all the way to the floorboard when you hold firm pressure on it at a stop?",
        "spongy brake pedal,pedal sinks to floor,needs pumping to build pressure,air in brake lines,master cylinder internal bypass",
        "hard brake pedal,high pitched squeal with firm pedal,vibration at highway braking"
    ),
    "Brake Caliper Sticking": (
        "Does the car yank sharply to the left or right when you apply the brakes, and does one wheel feel blisteringly hot with a burnt smell after a short drive?",
        "pulls to one side when braking,veers left or right under braking,one wheel extremely hot,burning brake smell one wheel,seized caliper slide pin",
        "pulls while driving straight without touching brakes,soft pedal sinking"
    ),
    "ABS Wheel Speed Sensor Failure": (
        "Is the amber ABS warning light (and traction control light) glowing on the dashboard while normal hydraulic braking still feels firm?",
        "abs warning light on dashboard,c0035,c0040,normal brakes work but no abs pulse,wheel speed sensor wire fault",
        "red brake fluid warning light,grinding noise from pads"
    ),
    "Brake Disc Warped": (
        "Do you feel a rapid pulsation in the brake pedal and a shaking in the steering wheel specifically when braking down from highway speeds (70+ km/h)?",
        "brake pedal pulsating at high speed braking,steering wheel shakes only when braking,warped brake rotor runout",
        "steering vibrates all the time even without braking,grinding metal sound at 5 kmph"
    ),
    "Rear Wheel Cylinder Leak": (
        "Is the brake fluid reservoir dropping while you see oily brake fluid wetting the inside of a rear wheel/tyre (drum brake assembly)?",
        "wet brake fluid inside rear wheel,puddle near rear drum brake,brake fluid level dropping fast,rear wheel cylinder leaking",
        "dry wheels,front disc squealing only"
    ),
    "Handbrake Cable Stretched": (
        "When you pull the handbrake lever all the way up (more than 7–8 clicks), does the car still roll backward on a slope?",
        "handbrake not holding on hill,parking brake lever pulls too high,car rolls when parked on incline,stretched handbrake cable",
        "foot brake pedal spongy,abs light on"
    ),
    "Brake Fade - Fluid Boiling": (
        "Did the brakes lose stopping power and the pedal feel long/mushy only after continuous heavy braking down a long mountain or ghat road?",
        "brakes fading going downhill,long downhill drive brake loss,fluid boiling old dot3,smoking hot brakes on ghat road",
        "cold morning first stop issue,handbrake cable loose"
    ),
    "Low Brake Fluid Level": (
        "Is the red 'BRAKE' warning light illuminated on the instrument cluster even when the handbrake is fully released, while the pedal still feels normal?",
        "red brake warning light stays on,handbrake is down,fluid below min mark in reservoir,pad wear drop",
        "yellow abs light only,grinding noise"
    ),
    "Drum Brake Shoe Worn": (
        "Do you hear a hollow scraping or rubbing sound coming specifically from the rear drum brakes when slowing down or pulling the handbrake slightly?",
        "scraping from rear drum brakes,rear wheels rubbing noise when stopping,rear brake shoe lining worn",
        "front wheel high pitched squeal,steering shaking"
    ),
    "Brake Hose Deterioration": (
        "Upon inspection, is the flexible rubber brake hose near the wheel cracked or ballooning under pedal pressure, causing delayed brake release on one wheel?",
        "rubber brake hose cracked or swollen,ballooning brake hose,delayed brake response one wheel,collapsed inner brake hose",
        "hard metal pipe,normal pad wear"
    ),
    "Brake Disc Surface Rust": (
        "Does the scraping/squeaking brake noise happen ONLY on the first 2 or 3 stops in the morning (especially after rain/washing) and then disappear completely?",
        "noise only on first few stops in morning,after rain or washing surface rust,goes away after 3 brake presses",
        "grinds loudly all day on every stop"
    ),
    "Brake Disc Thickness Variation": (
        "Do you feel a gentle rhythmic pedal rise-and-fall pulsation even during light, low-speed braking?",
        "pulsating pedal at low speed gentle braking,disc thickness variation dtv,uneven rotor thickness",
        "squealing noise only,pedal sinks to floor"
    ),

    # ─── ELECTRICAL ───
    "Battery End of Life": (
        "When you try to start the car in the morning, does it crank very slowly (or make a rapid 'tik-tik-tik' click) while the dashboard lights dim or reset, and is the battery over 3 years old?",
        "slow crank in morning,rapid clicking tik tik,dashboard lights dim when cranking,battery older than 3 years,jump start works immediately,low cca",
        "lights stay bright with single click,stalls while driving with battery light on"
    ),
    "Alternator Failure": (
        "Did the red battery-shaped warning light come on WHILE driving, followed by dimming headlights and the car eventually dying because the battery isn't charging (<13V)?",
        "red battery light on while driving,charging voltage below 13v,car died while driving,p0562,alternator not charging",
        "battery dies only after sitting parked for 3 days,lights stay bright no warning light"
    ),
    "Alternator Voltage Regulator Fault": (
        "Do the headlights and dashboard lights noticeably brighten and flare when you rev the engine, and dim down when the engine returns to idle?",
        "headlights dim at idle and brighten when revving,flickering lights with rpm,voltage fluctuating above 15v or below 13v,voltage regulator",
        "one single headlight bulb burnt out,battery dead after parking"
    ),
    "Power Window Motor or Regulator Failure": (
        "When you press the window switch for that door, does the glass move painfully slowly or get stuck halfway while you hear a humming/buzzing inside the door?",
        "one power window not moving,window stuck halfway,motor buzzing inside door panel,moves up very slowly",
        "glass fell completely inside door with loud crash,all 4 windows dead fuse blown"
    ),
    "Central Locking Actuator Failure": (
        "When you press the lock/unlock button on the remote or driver door, do most doors lock normally while one specific door lock fails to actuate (or makes a buzzing sound)?",
        "central locking not locking one door,door lock actuator buzzing,locks manually but not with remote",
        "key fob remote dead on all doors and indicator lights dont flash"
    ),
    "Short Circuit in Wiring": (
        "Does the exact same electrical fuse in the fuse box blow out again immediately (or within minutes) every time you replace it?",
        "same fuse keeps blowing repeatedly,fuse burns out immediately after replacement,chafed wire short to ground,sparking fuse",
        "bulb filament burnt,battery old"
    ),
    "Instrument Cluster Fault": (
        "Are multiple dashboard gauges (speedometer, fuel, temp) dropping to zero randomly while warning lights flicker erratically, even though the car drives normally?",
        "instrument cluster gauges dropping to zero,all dashboard lights flickering randomly,speedometer and tachometer dead intermittently",
        "only check engine light on,battery dead wont start"
    ),
    "Wiper Motor or Linkage Failure": (
        "When you turn the windshield wipers ON, do both wiper arms fail to move at all (or do you hear the wiper motor humming while the arms stay still)?",
        "wipers not moving at all,wiper motor humming but blades stuck,wiper linkage popped off,front wipers dead in rain",
        "wipers move fine but leave water streaks on glass"
    ),
    "Horn or Horn Relay Failure": (
        "When you press the horn pad on the steering wheel, is there zero sound (or just a faint click from the fuse box relay)?",
        "horn not making any sound,weak muffled horn sound,horn relay clicking no horn",
        "steering wheel hard to turn"
    ),
    "Immobilizer Transponder Issue": (
        "Is the key/padlock immobilizer icon blinking rapidly on the dashboard while the engine refuses to start (or starts for 1 second and immediately shuts off)?",
        "immobilizer key light blinking on dash,key not recognized,starts with spare key,security padlock icon flashing",
        "battery dead no dashboard lights,clicking starter solenoid"
    ),
    "Oxygen Sensor Failure": (
        "Is the Check Engine Light on with an O2 sensor code (P0130–P0167) accompanied by a 15–20% drop in fuel economy and slightly rough warm idle?",
        "o2 sensor code p0130 p0135 p0136,oxygen sensor circuit malfunction,poor fuel mileage with cel,bank 1 sensor 1 or 2",
        "engine overheating,no crank"
    ),
    "Mass Air Flow Sensor Fault": (
        "Is the Check Engine Light on with code P0100–P0104, and does the engine hesitate, surge, or stall right after starting unless you unplug the MAF sensor?",
        "maf sensor code p0100 p0101 p0102,mass air flow circuit low input,hesitation and surging acceleration,unplugging maf improves idle",
        "mechanical knocking noise,coolant leak"
    ),
    "Camshaft Position Sensor Failure": (
        "Is the engine taking long extended cranks to start (or cutting out intermittently) with OBD code P0340 or P0341 stored in the ECU?",
        "camshaft position sensor code p0340 p0341,extended long cranking before start,intermittent no start cel on",
        "dead battery slow crank"
    ),
    "Parasitic Current Draw": (
        "Does a healthy/new battery go completely flat ONLY when the car is left parked for 1 to 3 days, but start fine if driven every few hours?",
        "battery goes flat after parking 2 days,new battery draining overnight,parasitic current draw when car off,aftermarket accessory drain",
        "battery light comes on while driving,boot light visibly left on"
    ),
    "Tail Lamp Bulb or Wiring Issue": (
        "Is one specific rear tail light or brake light bulb failing to illuminate while the other side and the rest of the car's lights work fine?",
        "one tail light or brake light out,burnt filament in rear bulb,fast blinking indicator rear socket corrosion",
        "all headlights flickering with rpm"
    ),
    "Starter Relay or Ignition Switch Failure": (
        "When you turn the key to START, do all dashboard lights stay completely normal with ZERO click from the engine bay and zero cranking?",
        "no crank and no click at all,accessories and lights work fine,starter relay or ignition switch dead,total silence when turning key",
        "rapid clicking tik tik,engine cranks over"
    ),
    "Interior Light Switch Faulty": (
        "Have you noticed the boot/trunk light, dome light, or glovebox light staying illuminated even after all doors and the boot are shut?",
        "boot light or dome light staying on when closed,door ajar light stuck on,courtesy light switch draining battery",
        "alternator belt broken"
    ),
    "Reverse Camera Wiring or Unit Failure": (
        "When you shift into Reverse gear, does the infotainment screen switch to a blank black screen or 'No Signal' message while the reverse lights work?",
        "reverse camera black screen,no video signal when reversing,rear view camera blurry or dead",
        "reverse gear grinding mechanically"
    ),
    "Key Fob Battery Dead or Antenna Issue": (
        "Does the remote key fob fail to lock/unlock the doors from a distance unless you hold the fob right against the door/start button (or use the physical key)?",
        "remote key fob buttons not responding,keyless entry not working,red led on key fob dim,works with physical key blade",
        "one door actuator buzzing while other 3 doors lock"
    ),

    # ─── SUSPENSION ───
    "Shock Absorber Failure": (
        "Does the car keep bouncing up and down 2–3 times after going over a speed breaker, and do you see greasy oil leaking down the shock absorber tube?",
        "bounces multiple times after speed bump,oil leaking on shock absorber strut body,bouncy unstable ride",
        "single sharp metallic clunk on pothole,humming wheel bearing at 60 kmph"
    ),
    "Front Ball Joint Worn": (
        "Do you hear a heavy metallic 'thud' or 'clunk' from the lower front wheel area when hitting potholes or turning over uneven pavement?",
        "heavy clunk from front lower suspension over potholes,lower ball joint play,knocking over rough roads front wheel",
        "high pitched light rattle on smooth road,continuous humming noise"
    ),
    "Wheel Alignment Out": (
        "Does the car steadily drift to the left or right on a flat straight road with the steering wheel slightly off-center and uneven wear on one edge of the tyres?",
        "drifts to one side on straight road,steering wheel not centered,uneven inner or outer tyre wear,pulls continuously",
        "pulls only when pressing brake pedal,loud humming noise"
    ),
    "Wheel Bearing Failure": (
        "Is there a continuous roaring, humming, or airplane-like droning noise from a wheel that gets louder with speed (40–80 km/h) and changes pitch when you gently swerve left/right?",
        "roaring humming noise from wheel increases with speed,changes pitch when swerving left or right,wheel hub play,airplane drone sound",
        "noise changes with engine rpm when stationary,clunk only on bumps"
    ),
    "Suspension Bush Worn": (
        "Do you hear a dry rubbery creaking, groaning, or squeaking sound from underneath the front control arms when going over speed bumps or turning slowly?",
        "creaking squeaking noise over speed bumps,cracked rubber control arm bushes,groaning suspension when turning slowly",
        "roaring humming at highway speed,car sitting lower on one corner"
    ),
    "Coil Spring Broken": (
        "Is one corner of the car visibly sitting 1–2 inches lower than the other three corners, accompanied by a sharp metallic twang/clatter over bumps?",
        "one corner of car sitting lower,car leaning to one side when parked,broken coil spring fracture",
        "car level but bounces softly,pulls only when braking"
    ),
    "Strut Top Mount Failure": (
        "Do you hear a distinct 'pop', 'twang', or knocking noise from the top of the front strut tower specifically when turning the steering wheel while parking?",
        "popping clunking when turning steering at low speed,noise from top of strut tower under bonnet,strut mount bearing binding",
        "noise only at 100 kmph straight highway"
    ),
    "Anti Roll Bar Link Failure": (
        "Is there a rapid, light chattering or rattling knock from the front suspension even when driving over minor road ripples or small expansion joints at low speed?",
        "light rattling clicking over small bumps,sway bar end link play,chattering noise on slightly uneven road",
        "car sitting lower on one side,heavy nose dive when braking"
    ),
    "Front Struts Weak": (
        "Does the front nose of the car dive down excessively every time you apply the brakes and pitch back when accelerating?",
        "excessive nose dive when braking,front end dips down hard on stopping,soft spongy front struts",
        "rear sagging with luggage,steering wheel off center"
    ),
    "Rear Spring Sagging": (
        "Does the rear of the car sag down low and scrape its mudflaps/underbody over every speed breaker whenever 2–3 passengers sit in the back seat?",
        "rear end sags low with passengers or luggage,bottoming out scraping over speed bumps when loaded,weak rear coil springs",
        "front strut popping when turning steering"
    ),
    "Stabilizer Link Ball Joint Worn": (
        "Do you hear a hollow tapping/rattling from the front stabilizer bar area on small road bumps while the car handles normally on smooth highways?",
        "rattling from front stabilizer link on small bumps,ball joint play in sway bar link",
        "roaring noise increasing with speed"
    ),
    "Rear Shock Absorbers Worn on SUV": (
        "Does the rear tail of your SUV feel floaty, sway sideways after lane changes at highway speed, orfishtail over expansion joints?",
        "rear end swaying on highway,suv tail feels floaty unstable at speed,rear shock dampers worn",
        "front wheel pulling when braking"
    ),

    # ─── COOLING ───
    "Radiator Leak": (
        "Do you see green, pink, or blue coolant dripping directly from the front radiator fins or plastic side tanks and pooling under the front bumper?",
        "coolant dripping from front radiator core,puddle under front bumper,green or pink fluid on radiator fins,cracked radiator tank",
        "wet carpet inside passenger cabin,leak from engine oil pan"
    ),
    "Radiator Fan Motor or Relay Failure": (
        "When the temperature gauge climbs past halfway or you turn on the AC while parked, does the electric radiator fan behind the grille fail to spin at all?",
        "radiator fan not spinning when hot,overheating in traffic fan dead,electric cooling fan motor burnt",
        "fan spins loudly at high speed but still overheats,visible hose burst"
    ),
    "Coolant Hose Failure": (
        "Is coolant spraying or pouring out of a split, swollen, or collapsed thick rubber radiator hose in the engine bay with steam rising from the bonnet?",
        "rubber radiator hose split or burst,coolant spraying from upper or lower hose,swollen soft coolant hose",
        "slow drip from water pump pulley,running too cold"
    ),
    "Expansion Tank Crack": (
        "Do you see hairline cracks and dried white/pink crust or coolant weeping from the translucent plastic coolant overflow reservoir tank when hot?",
        "hairline crack in plastic coolant reservoir,expansion tank leaking from seam,overflow bottle cracked",
        "radiator metal fins punctured at front"
    ),
    "Thermostat Stuck Open": (
        "Does the temperature gauge needle stay near C (Cold) and never reach the middle mark during highway driving, accompanied by poor fuel mileage and lukewarm cabin heat?",
        "engine running too cold,temperature gauge stays low on highway,takes forever to warm up,p0128,thermostat stuck open",
        "temperature gauge in red overheating,steam from hood"
    ),
    "Heater Core Leak": (
        "Is there a sweet syrupy coolant smell inside the car cabin, a greasy fog on the inside of the windshield, and wet carpet on the front passenger floor?",
        "sweet coolant smell inside cabin,foggy greasy windshield inside,wet passenger floor carpet,heater core leaking under dashboard",
        "puddle under front bumper outside only"
    ),
    "Radiator Cap Failure": (
        "Is coolant bubbling and overflowing out of the expansion tank prematurely before the engine even reaches boiling temperature because the radiator cap seal is worn?",
        "coolant overflowing from reservoir cap,radiator cap rubber seal cracked,not holding pressure boiling early",
        "cracked radiator core fins"
    ),
    "Intercooler Leak": (
        "On your turbo-diesel vehicle, do you hear a loud 'whoosh' of escaping pressurized air under acceleration along with black smoke and weak turbo pull?",
        "whooshing boost air sound on acceleration,oily mist on intercooler pipe or core,turbo diesel power loss boost leak",
        "coolant level dropping,engine overheating"
    ),
    "Thermostat Sticking Intermittent": (
        "Does the temperature gauge needle climb high toward the red zone and then suddenly drop back to normal once the sticking thermostat pops open?",
        "temperature gauge fluctuating up and down erratically,climbs high then drops suddenly,sticking thermostat",
        "gauge stays cold all day"
    ),
    "Coolant Hose Pin Hole Leak": (
        "Do you see a fine needle-thin jet of steam or coolant mist spraying from a rubber hose only when the engine is fully hot and pressurized?",
        "fine steam spray from pinhole in hose when hot,sweet smell steam under bonnet no big puddle when cold",
        "massive hose burst dumping all coolant instantly"
    ),

    # ─── FUEL SYSTEM ───
    "Fuel Injector Clogged": (
        "Does the engine stumble and hesitate under load with a rough idle and cylinder injector circuit/misfire codes (P0201–P0204), while improving temporarily with fuel injector cleaner?",
        "stumbling hesitation on acceleration,clogged injector spray,p0201,p0202,p0203,p0204,lean misfire under load",
        "no crank at all,thick blue oil smoke"
    ),
    "Fuel Filter Blocked": (
        "Does the car idle fine and drive normally at low city speeds, but starve for fuel, jerk, and refuse to rev past 3000 RPM when climbing hills or overtaking?",
        "starving for fuel at high rpm or uphill,idles fine but loses power at full throttle,clogged fuel filter restriction",
        "stalls only at idle,wont crank"
    ),
    "Fuel Line Leak": (
        "Do you smell strong raw petrol/diesel around the outside of the car and see wet fuel dripping from the underbody fuel lines or fuel rail connections?",
        "raw fuel dripping under car,strong petrol odor outside,wet fuel line or fuel rail connection,fire hazard leak",
        "faint vapour smell only after filling tank full"
    ),
    "Fuel Pressure Regulator Failure": (
        "Is there excessively high fuel consumption, black sooty exhaust smoke, hard hot starting, and fuel rail pressure codes (P0191–P0194) or fuel in the vacuum line?",
        "fuel in regulator vacuum hose,black exhaust smoke rich running,p0191,p0192,p0193,fuel rail pressure sensor or regulator fault",
        "engine running lean p0171"
    ),
    "Fuel Level Sender Unit Failure": (
        "Does the dashboard fuel gauge needle stay stuck on Empty/Full or jump around erratically regardless of how much fuel you actually put in the tank?",
        "fuel gauge reading wrong,shows empty when tank is full,fuel needle fluctuating or stuck,sender float unit",
        "all dashboard gauges dead together,car losing engine power"
    ),
    "Diesel Injection Pump Failure": (
        "On your diesel vehicle, is there severe hard starting, metallic clatter from the high-pressure injection pump, hunting idle, and total loss of pulling power (code P0251)?",
        "diesel injection pump p0251,high pressure diesel pump failure,hard start and hunting idle diesel,low rail pressure",
        "petrol vehicle,simple air filter dust"
    ),
    "Fuel Cap Seal Damaged": (
        "Did the Check Engine Light come on shortly after refueling with an EVAP leak code (P0440/P0455), and does the fuel filler cap feel loose or have a cracked rubber O-ring?",
        "check engine light after refueling,evap leak code p0440 p0442 p0455,loose fuel cap or cracked cap seal",
        "liquid petrol dripping on ground,engine misfiring violently"
    ),
    "CNG Reducer Malfunction": (
        "Does your CNG car run fine on Petrol, but jerk, lose power, stall, or show frost/ice buildup on the CNG vaporizer/reducer in the engine bay when switched to CNG mode?",
        "frost or ice on cng reducer,runs fine on petrol but stalls or loses power on cng,cng vaporizer diaphragm fault",
        "runs badly on both petrol and cng equally"
    ),
    "Fuel Tank Breather or Charcoal Canister Issue": (
        "Do you smell petrol fumes inside the cabin (especially after parking in the sun or filling the tank) along with a loud 'whoosh' of pressure when opening the fuel cap?",
        "petrol smell inside cabin after parking,high pressure hiss when opening fuel cap,saturated charcoal canister purge valve p0440",
        "liquid fuel puddle under engine bay"
    ),
    "Throttle Body Carbon Buildup": (
        "Does the accelerator response feel sticky/jerky off idle, and does the RPM dip near stalling when you turn on the AC or press the clutch in traffic (codes P0121/P0122)?",
        "rpm dips when ac turned on at idle,sticky throttle response,black carbon ring inside throttle bodybutterfly,p0121,p0122",
        "loud metallic engine knock"
    ),

    # ─── EXHAUST ───
    "Catalytic Converter Failure": (
        "Do you smell a sulfur 'rotten egg' odor from the exhaust, hear a metallic honeycomb rattle inside the converter shell, and feel the car choking at high RPM (codes P0420/P0430)?",
        "rotten egg sulfur smell from exhaust,rattling honeycomb inside catalytic converter,choked power at high rpm,p0420,p0430",
        "loud muffler roar at rear tailpipe only"
    ),
    "Silencer and Muffler Corrosion": (
        "Has the exhaust note suddenly become a deep, loud roaring rumble from the rear of the car, with visible rust holes or soot around the rear muffler box?",
        "loud roaring exhaust noise from rear,rusted hole in rear silencer muffler,exhaust booming sound",
        "light ticking from front engine bay when cold"
    ),
    "Exhaust Manifold Crack or Gasket Leak": (
        "Do you hear a sharp 'chuff-chuff' ticking sound from the front engine bay that is loudest on a cold start and quiets down slightly as the exhaust manifold heats up and expands?",
        "ticking chuffing noise from exhaust manifold when cold,black soot marks around manifold ports,exhaust fume smell under bonnet",
        "loud roar from rear bumper tailpipe"
    ),
    "DPF Clogged (Diesel)": (
        "On your BS6 diesel vehicle, is the DPF/particulate filter light glowing on the dash while the car has entered limp mode (restricted below 2500 RPM, codes P2002/P2463)?",
        "dpf warning light on dashboard,bs6 diesel limp mode rpm restricted,p2002,p2463,soot load high regeneration needed",
        "petrol car,normal high rpm power"
    ),
    "EGR Valve Carbon Buildup": (
        "Is your diesel engine producing puffs of black smoke under acceleration with sluggish pickup and EGR flow/position codes P0401–P0404?",
        "black smoke and sluggish pickup diesel,heavy carbon clogging egr valve,p0401,p0402,p0404",
        "white coolant smoke,blue oil smoke"
    ),
    "Exhaust Flex Pipe Failure": (
        "Is there a raspy exhaust roar and vibration coming directly from underneath the front seats/firewall area where the braided wire flex-pipe joins the downpipe?",
        "raspy exhaust leak noise under front floor,frayed braided wire flex pipe cracked,exhaust sound under driver feet",
        "rear tailpipe silencer hole"
    ),
    "Exhaust Hanger or Bracket Broken": (
        "Is the exhaust tailpipe hanging abnormally low and clanging or banging against the underbody whenever you go over bumps?",
        "exhaust pipe hanging low,clanging banging under car over bumps,broken rubber exhaust hanger mount",
        "loud exhaust roar with pipe firmly mounted"
    ),
    "Exhaust Heat Shield Loose": (
        "Is there a tinny, metallic buzzing or rattling sound from underneath the car at a specific RPM (around 1500–2000 RPM) without any loss of power?",
        "tinny metallic rattle under car at specific rpm,loose aluminum heat shield above exhaust pipe,no performance loss",
        "deep engine knock under load"
    ),

    # ─── STEERING ───
    "Steering Rack Seal Leak": (
        "Is red/amber power steering fluid dripping from the rubber accordion boots on the steering rack, while the steering feels heavy and the reservoir level keeps dropping?",
        "power steering fluid dripping from steering rack boots,wet accordion boots on rack,fluid reservoir dropping fast",
        "electric power steering car with no fluid,tire balance vibration only"
    ),
    "Power Steering Pump Failure": (
        "Do you hear a loud groaning or whining noise from the engine bay that gets louder every time you turn the steering wheel (especially at full lock)?",
        "whining groaning noise when turning steering wheel,louder at full steering lock,power steering pump noisy,foamy fluid",
        "silent steering with EPS warning light on dash"
    ),
    "Tie Rod End Worn": (
        "Is there an inch of loose free-play in the steering wheel before the front wheels respond, along with a clunk when turning over bumps and feathered front tyre edges?",
        "excessive free play in steering wheel,loose vague steering feel,clunk when turning,feathered front tyre wear,tie rod ball joint play",
        "heavy stiff steering with EPS light on"
    ),
    "Electric Power Steering Motor Failure": (
        "Is the red/amber steering-wheel 'EPS' warning icon glowing on the dashboard while the steering wheel suddenly became super heavy to turn (code C0545)?",
        "eps warning light on dashboard,steering suddenly very heavy,electric power steering assist failed,c0545",
        "red fluid leaking on ground,whining hydraulic pump"
    ),
    "Wheel Balance Off or Worn Suspension": (
        "Does the steering wheel vibrate or shimmy smoothly in your hands ONLY within a specific highway speed band (e.g., 80 to 100 km/h) even without touching the brakes?",
        "steering wheel vibrates at 80 to 100 kmph highway cruising,wheel balance weight missing,shimmy at constant highway speed",
        "vibrates only when pressing brake pedal,vibrates when parked at idle"
    ),
    "Steering Column Universal Joint Wear": (
        "Do you feel a sharp metallic click, notchiness, or tight-loose-tight binding sensation in the steering column shaft as you rotate the steering wheel?",
        "clicking clunking inside steering column when turning,notchy tight then loose steering rotation,intermediate shaft u joint",
        "smooth steering that just drifts slightly on highway"
    ),
    "Power Steering Fluid Contamination": (
        "Has the power steering fluid in the reservoir turned dark brown/black with a burnt smell, making the steering feel stiff on cold mornings?",
        "power steering fluid dark black or brown,stiff steering when cold in morning,degraded dirty ps fluid,no external leak",
        "fluid leaking out onto ground"
    ),
    "Steering Geometry or Caster Problem": (
        "After completing a turn around a corner, does the steering wheel fail to self-center back to straight ahead on its own?",
        "steering wheel does not return to center after turn,stays turned after cornering,poor self centering caster angle",
        "vibration at 90 kmph"
    ),
    "Wheel Alignment Disturbed": (
        "Did the steering wheel become crooked/off-center right after hitting a deep pothole or curb at speed?",
        "steering wheel crooked after hitting pothole or curb,off center steering wheel driving straight",
        "eps warning light on"
    ),
    "Power Steering Fluid Level Low": (
        "Is the steering heavy during slow parking maneuvers with a faint whine, and is the fluid level in the reservoir below the MIN line?",
        "heavy steering while parking at low speed,power steering reservoir fluid below min level,topping up fixes noise",
        "electric power steering motor fault"
    ),

    # ─── AC / HVAC ───
    "AC Refrigerant Leak": (
        "When you turn the AC ON, does the blower fan blow strong air that is completely warm/ambient temperature, even though there is no loud grinding noise from the engine?",
        "ac blowing warm air continuously,no cooling at all from ac vents,refrigerant gas empty,low pressure cut off",
        "no air coming out of vents at all,cools fine for 20 minutes then stops"
    ),
    "AC Compressor Failure": (
        "When you press the AC button, do you hear a loud metallic grinding, rattling, or screeching noise from the AC compressor pulley (or see the compressor clutch failing to engage)?",
        "loud grinding rattling when ac turned on,ac compressor clutch seized or noisy,metal shavings in ac lines",
        "quiet operation just slightly weak cooling after a year"
    ),
    "AC Expansion Valve Stuck": (
        "Does the AC blow ice-cold air for 10–15 minutes and then suddenly switch to blowing humid warm air before cycling back to cold again?",
        "ac blows cold then warm intermittently,cooling cycles on and off while driving,expansion valve freezing or stuck",
        "never blows cold even for 1 minute"
    ),
    "AC Condenser Damage": (
        "Did the AC stop cooling completely after a stone hit the front grille, and can you see bent/oily fins on the front AC condenser radiator behind the bumper?",
        "stone impact damage on front ac condenser,oily wet spot on condenser fins behind grille,sudden gas loss from front hit",
        "blower fan not blowing air"
    ),
    "Evaporator Bacterial Growth": (
        "Does the AC still cool normally, but emit a foul, damp, mouldy or vinegar-like smell from the vents during the first few minutes after turning it on?",
        "foul musty smell from ac vents,damp mouldy odor when turning ac on,ac cools fine but smells bad",
        "sweet coolant smell with foggy glass,burning oil smell"
    ),
    "Blower Motor Failure": (
        "When you turn the cabin fan knob across all speeds (1, 2, 3, and 4), is there ZERO airflow coming out of the dashboard vents?",
        "zero air coming from vents on any speed,blower fan motor completely dead,no airflow even on max speed 4",
        "air blows fine on speed 4,air blows strong but warm"
    ),
    "Blower Motor Resistor Failure": (
        "Does the cabin AC fan blow ZERO air on lower speeds (1, 2, and 3), but suddenly blast at full force when you turn the switch to the highest speed (4)?",
        "blower fan only works on speed 4 highest setting,speeds 1 2 3 not working,blower motor resistor pack burnt",
        "fan dead on all speeds including 4"
    ),
    "AC Drive Belt Failure": (
        "Did the AC suddenly stop working right after a loud slapping/snapping sound from the engine bay, and is the rubber drive belt on the AC compressor missing or shredded?",
        "ac drive belt snapped or missing,slapping noise then no ac,broken compressor belt",
        "belt intact and spinning normally"
    ),
    "Heater Valve or Core Blocked": (
        "When you turn the temperature dial to full RED (Heat) with the engine fully warmed up, do the vents still blow cold unheated air?",
        "no hot air from heater in winter,blowing cold air when set to heat,engine temperature is normal,heater core or valve blocked",
        "engine temperature gauge stuck on cold,ac not cooling in summer"
    ),
    "AC System Slow Leak": (
        "Does your AC cool well after a gas top-up, but gradually lose its cooling effectiveness over 3 to 6 months until it needs recharging again?",
        "ac loses cooling after a few months,needs gas recharge every summer,slow o ring refrigerant seepage",
        "sudden loud compressor grinding noise"
    ),
    "AC Receiver Dryer Saturated": (
        "Does the AC start out blowing cold for the first 20–30 minutes of a trip, and then gradually ice up and stop cooling until you turn the AC off to thaw?",
        "ac cooling stops after 30 minutes of driving,moisture freezing in system,works again after turning ac off for 10 mins",
        "never cools from the start"
    ),
    "AC Drain Pipe Blocked": (
        "Is clear, odorless cold water dripping from under the dashboard onto the front passenger floor mat whenever the AC has been running?",
        "clear water dripping on passenger floor mat when ac is on,no water puddle dripping under car outside,clogged ac drain tube",
        "green sweet smelling antifreeze coolant leaking"
    ),

    # ─── BODY ───
    "Window Regulator Cable Broken": (
        "Did you hear a crunching/snapping sound inside the door followed by the window glass dropping straight down into the door panel while the motor still spins freely?",
        "window glass dropped down inside door,crunching cable sound in door,motor spins but glass fell down",
        "motor completely silent and glass stuck at top"
    ),
    "Door Hinge Wear": (
        "Does the heavy driver door visibly drop down a few millimeters when you swing it open, requiring you to lift or slam it hard to make it latch shut?",
        "door drops down when opened,sagging door hinge pins,have to lift door to close properly,up and down play in open door",
        "central locking remote not working"
    ),
    "ORVM Mirror Motor Failure": (
        "Does the outside side-view mirror (ORVM) fail to fold in/out or adjust its glass angle when you press the electric mirror control switch?",
        "side mirror not folding or adjusting electrically,orvm motor stuck or clicking,mirror switch not moving glass",
        "power window glass not moving"
    ),
    "Boot Lock Mechanism Failure": (
        "Is the rear boot/dickey lid refusing to unlatch when you press the tailgate button or pull the release lever (or refusing to lock shut)?",
        "boot dickey trunk wont open,tailgate latch jammed,boot lock actuator not releasing",
        "side passenger door sagging"
    ),
    "Sunroof Drain Blockage": (
        "Is rainwater dripping from the roof headliner, A-pillar trim, or sunroof edges inside the cabin whenever it rains or after washing the car?",
        "water leaking from sunroof roof headliner in rain,wet a pillar fabric,clogged sunroof corner drain tubes",
        "clear water dripping under dashboard from ac in dry weather"
    ),
    "Windshield Damage": (
        "Is there a visible stone chip or crack spreading across the front laminated windshield glass in the driver's line of sight?",
        "cracked front windshield glass,stone chip spreading crack across windscreen",
        "wiper rubber leaving streaks on intact glass"
    ),
    "Wiper Blade Rubber Worn": (
        "Do the wiper arms sweep across the glass at normal speed, but leave smeared water streaks, chatter/squeak, or have torn rubber edges?",
        "wipers leaving water streaks and smearing,chattering squeaking wiper blades on glass,torn wiper rubber",
        "wiper arms not moving at all"
    ),
    "Door Striker Plate Misaligned": (
        "Is the door hinge firm with zero vertical sag, yet the door bounces back or requires an extra hard slam to catch on the B-pillar striker loop?",
        "door latch not catching easily without slamming,no hinge sag,misaligned striker plate on pillar",
        "door drops 1 inch when opened"
    ),

    # ─── BIKE / TWO-WHEELER ───
    "Chain Sprocket Kit Worn": (
        "Is the motorcycle drive chain making a loud metallic clattering/whirring noise with pointed 'shark-fin' teeth on the rear sprocket and needing frequent tightening?",
        "bike chain loose and noisy,pointed shark fin sprocket teeth,jerky chain drive,needs frequent chain adjustment",
        "scooter automatic belt,engine internal tappet tick"
    ),
    "Battery Weak or CDI Failure": (
        "On your motorcycle, are both the electric self-start and kick-start failing to fire the engine, with either a dim horn/neutral light or zero spark at the spark plug?",
        "both kick and self start not starting bike,no spark at plug or dead battery horn weak,cdi unit or battery dead",
        "self start motor spins freely with strong battery and kick starts in 1 kick"
    ),
    "Carburetor Float Valve Stuck": (
        "Is raw petrol continuously dripping out of the small overflow tube at the bottom of the motorcycle carburetor, accompanied by fuel flooding and hard starting?",
        "petrol leaking from carburetor overflow pipe,carburetor flooding rich smell,float needle stuck open",
        "stalls only at idle with zero fuel leak"
    ),
    "Clutch Plate Worn (Motorcycle)": (
        "When you twist the throttle hard in 3rd or 4th gear on your bike, does the engine rev loudly while pickup feels sluggish and the kick-starter slips without resistance?",
        "bike engine revs high but poor pickup in gear,kick starter slips down without cranking compression,burnt motorcycle clutch plates",
        "clutch cable snapped lever floppy"
    ),
    "Self Start Motor Bendix Failure": (
        "When you press the electric start button on your bike/scooter, do you hear a high-speed 'zzzz' whirring or clacking sound while the engine doesn't crank (yet kick-start works fine)?",
        "self start motor spins whirs without turning engine,kick start works normally,bendix starter drive gear not engaging",
        "both kick and self start dead"
    ),
    "Front Fork Oil Seal Leak": (
        "Do you see dark, greasy suspension oil coating the chrome front fork tubes of your motorcycle and dripping down toward the front brake disc/caliper?",
        "oil rings on chrome front fork tubes,front suspension leaking oil,front forks bottoming out and bouncy",
        "engine oil leaking under crankcase"
    ),
    "Throttle Cable Issue (Motorcycle)": (
        "When you twist and release the motorcycle accelerator grip, does it stick open or return slowly instead of snapping back shut with a crisp click?",
        "throttle grip sticking open not snapping back,stiff accelerator cable on handlebar,high idle when turning handlebar",
        "clutch slipping in top gear"
    ),
    "Tappet Clearance Incorrect (RE)": (
        "Is there a distinct metallic 'tik-tik-tik' sewing-machine tapping sound coming from the top-right cylinder head of your Royal Enfield that speeds up with RPM?",
        "royal enfield bullet top end tik tik tapping noise,tappet valve clearance loose,clattering from rocker cover",
        "heavy deep thud from primary chain left cover"
    ),
    "Rear Brake Shoe Worn (Motorcycle)": (
        "Do you have to press the rear brake pedal (or squeeze the left scooter brake lever) almost all the way in with weak stopping power and a squeak from the rear drum?",
        "rear drum brake weak stopping on bike,brake pedal goes deep even after adjusting nut,squeaking rear bike brake",
        "front fork oil leaking"
    ),
    "Speedometer Cable Failure (Motorcycle)": (
        "Has the analog speedometer needle and odometer on your motorcycle stopped moving completely while you ride, even though the rest of the electricals work?",
        "bike speedometer needle stuck at zero,odometer not counting km,broken inner speedometer cable at front wheel hub",
        "all dashboard lights and horn dead"
    ),
    "Kick Starter Mechanism Failure": (
        "Is the motorcycle kick-start lever either jammed solid at the top or failing to spring back up after you kick it down?",
        "kick starter lever jammed stuck or not returning up,broken kick return spring or ratchet gear",
        "kick lever moves smoothly and starts engine"
    ),
    "CVT Drive Belt Worn (Scooter)": (
        "On your automatic scooter (Activa/Jupiter/Access), do you feel violent jerking/shuddering from the rear CVT cover when accelerating from 0–20 km/h and reduced top speed?",
        "scooter vibrating jerking from standstill,cvt belt slipping and noisy inside left cover,sluggish automatic scooter pickup",
        "manual gear motorcycle chain noise"
    ),
    "Chain and Sprocket Kit Worn Beyond Limit": (
        "Has the chain adjustment snail-cam on the rear swingarm reached its maximum mark while the chain still hangs loose and makes a loud whipping vibration?",
        "chain adjuster at max limit still loose,severe vibration from worn sprocket teeth,chain jumping teeth",
        "scooter belt drive"
    ),
    "Scooter Starter Clutch Failure": (
        "When you press the electric start button on your scooter, does the starter motor spin freely with a metallic spinning sound without catching the crankshaft?",
        "scooter electric start just spinning whirring freely,one way starter clutch rollers slipping,kick start works",
        "battery dead no sound when pressing button"
    ),
    "Idle Jet Blocked in Carburetor": (
        "Does your motorcycle run fine as long as you hold the throttle open slightly, but die/stall immediately every time you close the throttle at a traffic signal?",
        "bike stalls immediately when throttle closed at traffic light,wont hold idle unless choke is on or throttle held,clogged pilot idle jet",
        "petrol overflowing onto ground"
    ),
    "RE Engine Primary Chain Tensioner Wear": (
        "On your Royal Enfield, do you hear a rhythmic heavy 'thud-thud' or rubbing rattle from the left-side primary crankcase cover when decelerating or idling?",
        "thudding rattling from left side primary cover royal enfield,primary chain slapping crankcase",
        "light tik tik from top cylinder head right side"
    ),
    "Bike Voltage Regulator Rectifier Fault": (
        "Does your motorcycle headlight flare brightly and burn out bulbs when revving, or fail to keep the battery charged despite a brand-new battery?",
        "bike headlight flickering flaring with rpm,headlight bulbs blowing frequently,regulator rectifier overcharging or not charging",
        "broken speedometer cable"
    ),
    "Bike Engine Oil Level Low or Degraded": (
        "Is the motorcycle engine running unusually hot with a harsh mechanical sound and stiff gear shifts in traffic, and is the oil sight-glass empty or pitch black?",
        "motorcycle engine overheating in traffic,stiff gear shifting when hot,low or burnt black oil in sight glass",
        "coolant hose burst on car"
    ),
    "Side Stand Switch Malfunction": (
        "Does your motorcycle start fine in Neutral, but immediately cut off the ignition as soon as you click it into 1st gear even though the side stand is folded up?",
        "bike cuts out as soon as put into first gear,side stand warning stays on even when stand is up,faulty side stand sensor",
        "wont start even in neutral"
    ),
    "Exhaust Valve or Leak at Header": (
        "Does your motorcycle make loud 'pop-bang' afterfire sounds from the silencer every time you roll off the throttle on deceleration?",
        "loud popping banging from bike exhaust on deceleration,air leak at exhaust header pipe flange gasket",
        "clattering loose drive chain"
    ),

    # ─── TRUCK / COMMERCIAL ───
    "Air Brake Compressor or Leak": (
        "On your commercial truck, is the air pressure gauge failing to climb to 8 bar (120 PSI) with the low-air buzzer sounding and an audible air hissing leak?",
        "air pressure gauge not rising,low air pressure warning buzzer on truck,hissing air leak in brake line or compressor",
        "hydraulic brake car,normal air pressure"
    ),
    "Turbocharger Failure (Commercial)": (
        "Is your commercial diesel truck whistling loudly or blowing thick black/blue smoke while struggling to pull loads uphill with boost code P0299?",
        "commercial truck turbo whistling loudly,heavy load power loss uphill,p0299,oil in truck intercooler pipes",
        "air brake pressure drop"
    ),
    "Leaf Spring Failure": (
        "Is the rear cargo chassis of the truck tilted/sagging to one side with a visibly cracked or shifted steel leaf in the rear leaf-spring stack?",
        "cracked steel leaf in spring pack,truck rear sagging to one side under load,clanking rear axle leaf spring",
        "front steering kingpin wobble"
    ),
    "Clutch Assembly Failure (Commercial)": (
        "In your commercial truck, is the clutch slipping under heavy payload with an acrid burnt friction smell and an extremely heavy clutch pedal?",
        "burnt clutch smell on loaded truck uphill,commercial clutch slipping under load,heavy stiff truck clutch pedal",
        "gearbox oil leak only"
    ),
    "King Pin Wear (Commercial)": (
        "Does the commercial truck's front steering wander all over the road with violent front-wheel wobble over bumps and vertical play in the front axle kingpins?",
        "front wheel wobbling wandering steering on truck,excessive vertical play in front axle king pin bushes,uneven truck front tyre wear",
        "rear leaf spring cracked"
    ),
    "Engine Brake Solenoid Failure": (
        "When you flip the exhaust/Jake brake switch while descending a grade in your truck, does the engine retarder fail to engage and provide zero engine braking?",
        "truck jake brake or exhaust retarder not engaging downhill,engine brake solenoid valve fault",
        "service foot air brakes leaking"
    ),
    "Air Compressor Governor Fault": (
        "Is the truck's air brake pressure either building painfully slowly or failing to cut out at 120–125 PSI (causing the safety valve to keep popping off)?",
        "truck air pressure building very slowly,air governor not cutting in or out at correct psi,unloader valve sticking",
        "complete pipe burst dumping air in 5 seconds"
    ),
}


def build_symptom_variations(fault_name, system, base_symptoms, obd_code, meta_tuple):
    """
    Generate 18–25 natural, distinct, non-overlapping symptom variations for each fault
    using its base symptoms, OBD codes, confirming keywords, and real-world driver/mechanic phrasing.
    """
    variations = set()
    for s in base_symptoms:
        variations.add(s.strip().lower())

    followup, confirm_str, _ = meta_tuple
    confirm_phrases = [c.strip().lower() for c in confirm_str.split(",") if c.strip()]
    obd_codes = [c.strip().upper() for c in str(obd_code).split(",") if c.strip() and c.strip().lower() != "nan"]

    # Add confirming phrases combined with system/fault context
    for cp in confirm_phrases:
        variations.add(cp)
        if base_symptoms:
            variations.add(f"{base_symptoms[0].lower()} and {cp}")
            if len(base_symptoms) > 1:
                variations.add(f"{cp} with {base_symptoms[1].lower()}")

    # Add pairwise combinations of confirming phrases
    for i in range(len(confirm_phrases)):
        for j in range(i + 1, min(i + 3, len(confirm_phrases))):
            variations.add(f"{confirm_phrases[i]} and {confirm_phrases[j]}")

    # Add OBD-II code specific queries so direct code queries and code+symptom queries match with 99% confidence
    for code in obd_codes:
        variations.add(f"obd code {code.lower()}")
        variations.add(f"check engine light {code.lower()} {base_symptoms[0].lower()}")
        variations.add(f"diagnostic trouble code {code.lower()} {confirm_phrases[0] if confirm_phrases else ''}".strip())
        variations.add(f"{code.lower()} fault detected in {system.lower()}")

    # Add natural driver/mechanic conversational templates
    if base_symptoms and confirm_phrases:
        b0 = base_symptoms[0].lower()
        c0 = confirm_phrases[0]
        c1 = confirm_phrases[1] if len(confirm_phrases) > 1 else c0
        variations.add(f"customer complains of {b0} especially {c0}")
        variations.add(f"my vehicle has {b0} along with {c1}")
        variations.add(f"diagnose {b0} confirmed {c0}")
        variations.add(f"issue with {system.lower()}: {b0}, {c0}")

    # Clean up whitespace
    cleaned = [re.sub(r"\s+", " ", v).strip() for v in variations if len(v.strip()) >= 4]
    return sorted(cleaned)


def map_obd_to_canonical_fault(obd_code, raw_desc):
    """
    Map HuggingFace OBD-II codes and descriptions directly to our rich canonical faults
    so we never predict useless 'OBD Pxxxx' labels with 'Requires Inspection'.
    """
    code = str(obd_code).replace("OBD ", "").strip().upper()
    desc = str(raw_desc).lower()

    if code in ("P0100", "P0101", "P0102", "P0103", "P0104") or "mass or volume air flow" in desc or "maf" in desc:
        return "Mass Air Flow Sensor Fault"
    if code in ("P0105", "P0106", "P0107", "P0108", "P0109") or "manifold absolute pressure" in desc:
        return "Mass Air Flow Sensor Fault"
    if code in ("P0110", "P0111", "P0112", "P0113", "P0114") or "intake air temperature" in desc or "iat circuit" in desc:
        return "Mass Air Flow Sensor Fault"
    if code in ("P0115", "P0116", "P0117", "P0118", "P0119", "P0125", "P0126", "P0128") or "coolant temperature" in desc or "thermostat" in desc:
        if "insufficient" in desc or "closed loop" in desc or code in ("P0125", "P0126", "P0128"):
            return "Thermostat Stuck Open"
        return "Thermostat Stuck Closed"
    if code in ("P0120", "P0121", "P0122", "P0123", "P0124") or "throttle position" in desc:
        return "Throttle Body Carbon Buildup"
    if code.startswith("P013") or code.startswith("P014") or code.startswith("P015") or code.startswith("P016") or "o2 sensor" in desc or "oxygen sensor" in desc:
        return "Oxygen Sensor Failure"
    if code in ("P0170", "P0171", "P0172", "P0174", "P0175") or "lean" in desc or "fuel trim malfunction" in desc:
        return "Vacuum Leak"
    if code in ("P0173", "P0176") or "too rich" in desc:
        return "Fuel Injector Leaking"
    if code in ("P0177", "P0178", "P0179", "P0180", "P0181", "P0182", "P0183", "P0184", "P0185", "P0186", "P0187", "P0188", "P0189", "P0190", "P0191", "P0192", "P0193", "P0194", "P0195") or "fuel rail pressure" in desc or "fuel temperature" in desc or "fuel composition" in desc:
        return "Fuel Pressure Regulator Failure"
    if code in ("P0196", "P0197", "P0198", "P0199", "P0200") or "engine oil temperature" in desc:
        return "Oil Pump Wear"
    if code.startswith("P020") or "injector circuit" in desc:
        return "Fuel Injector Clogged"
    if code.startswith("P030") or "misfire" in desc:
        return "Ignition Coil Failure"
    if code in ("P0420", "P0430") or "catalyst" in desc:
        return "Catalytic Converter Failure"
    if code in ("P0440", "P0442", "P0455") or "evaporative" in desc:
        return "Fuel Cap Seal Damaged"
    return "Oxygen Sensor Failure"


def enrich_and_save():
    local_path = os.path.join(DATA_DIR, "vehicle_faults.csv")
    merged_path = os.path.join(DATA_DIR, "merged_internet_faults.csv")

    df = pd.read_csv(local_path)
    print(f"[*] Loaded existing vehicle_faults.csv: {len(df)} rows across {df['fault_name'].nunique()} unique faults.")

    # Group existing faults to preserve all canonical metadata
    enriched_rows = []
    fid = 1

    for fault_name, grp in df.groupby("fault_name", sort=False):
        first = grp.iloc[0]
        vtype = first["vehicle_type"]
        system = first["system"]
        obd_code = "" if pd.isna(first["obd_code"]) else str(first["obd_code"])
        conf = first["confidence"]
        severity = first["severity"]
        parts = "" if pd.isna(first["required_parts"]) else str(first["required_parts"])
        time_hrs = first["estimated_time_hours"]
        cost = "" if pd.isna(first["estimated_cost_range"]) else str(first["estimated_cost_range"])
        fix = "" if pd.isna(first["fix_procedure"]) else str(first["fix_procedure"])
        vehicles = "" if pd.isna(first["common_vehicles"]) else str(first["common_vehicles"])

        base_symptoms = grp["symptom"].dropna().tolist()

        meta = FAULT_DIAGNOSTIC_META.get(fault_name)
        if not meta:
            meta = (
                f"To confirm {fault_name}, can you check if the symptom worsens under load and verify the component condition?",
                ",".join(base_symptoms),
                ""
            )
        followup_q, confirming_kw, ruling_out_kw = meta

        expanded_symptoms = build_symptom_variations(fault_name, system, base_symptoms, obd_code, meta)

        for sym in expanded_symptoms:
            enriched_rows.append({
                "fault_id": f"F{fid:04d}",
                "vehicle_type": vtype,
                "system": system,
                "symptom": sym,
                "fault_name": fault_name,
                "obd_code": obd_code,
                "confidence": conf,
                "severity": severity,
                "required_parts": parts,
                "estimated_time_hours": time_hrs,
                "estimated_cost_range": cost,
                "fix_procedure": fix,
                "common_vehicles": vehicles,
                "followup_question": followup_q,
                "confirming_keywords": confirming_kw,
                "ruling_out_keywords": ruling_out_kw,
            })
            fid += 1

    enriched_df = pd.DataFrame(enriched_rows)
    enriched_df.to_csv(local_path, index=False, encoding="utf-8")
    print(f"[OK] Saved enriched vehicle_faults.csv: {len(enriched_df)} rows across {enriched_df['fault_name'].nunique()} unique faults.")

    # Now update merged_internet_faults.csv so that its rows map cleanly to canonical fault names
    if os.path.exists(merged_path):
        mdf = pd.read_csv(merged_path)
        print(f"[*] Re-aligning merged_internet_faults.csv ({len(mdf)} rows) to canonical fault taxonomy...")

        # Build lookup from canonical fault_name -> metadata
        canon_meta = {}
        for fn, grp in enriched_df.groupby("fault_name"):
            r0 = grp.iloc[0]
            canon_meta[fn] = {
                "system": r0["system"],
                "vehicle_type": r0["vehicle_type"],
                "severity": r0["severity"],
                "followup_question": r0["followup_question"],
            }

        def remap_row(row):
            fn = str(row["fault_name"])
            sym = str(row["symptom"])
            obd = str(row.get("obd_code", ""))
            if fn == "Air Pressure System Critical Failure":
                new_fn = "Air Brake Compressor or Leak"
            elif fn.startswith("OBD "):
                new_fn = map_obd_to_canonical_fault(obd, sym)
            else:
                new_fn = fn

            cm = canon_meta.get(new_fn, {})
            return pd.Series({
                "fault_id": row["fault_id"],
                "vehicle_type": cm.get("vehicle_type", row["vehicle_type"]),
                "system": cm.get("system", row["system"]),
                "symptom": f"{sym} ({obd})".strip() if obd and obd not in sym else sym,
                "fault_name": new_fn,
                "obd_code": obd,
                "severity": cm.get("severity", row["severity"]),
                "followup_question": cm.get("followup_question", row.get("followup_question", "")),
            })

        # Deduplicate before remapping to transform rapidly, then map back
        unique_pairs = mdf[["symptom", "fault_name", "obd_code", "vehicle_type", "system", "severity", "followup_question"]].drop_duplicates()
        mapped_map = {}
        for _, urow in unique_pairs.iterrows():
            key = (urow["symptom"], urow["fault_name"], urow["obd_code"])
            fn = str(urow["fault_name"])
            sym = str(urow["symptom"])
            obd = str(urow.get("obd_code", ""))
            if fn == "Air Pressure System Critical Failure":
                new_fn = "Air Brake Compressor or Leak"
            elif fn.startswith("OBD "):
                new_fn = map_obd_to_canonical_fault(obd, sym)
            else:
                new_fn = fn
            cm = canon_meta.get(new_fn, {})
            mapped_map[key] = (
                cm.get("vehicle_type", urow["vehicle_type"]),
                cm.get("system", urow["system"]),
                f"{sym} {obd.lower()}".strip() if obd and obd.lower() not in sym.lower() else sym,
                new_fn,
                cm.get("severity", urow["severity"]),
                cm.get("followup_question", urow.get("followup_question", "")),
            )

        new_vtypes, new_systems, new_syms, new_fns, new_sevs, new_fups = [], [], [], [], [], []
        for sym, fn, obd in zip(mdf["symptom"], mdf["fault_name"], mdf["obd_code"]):
            vt, sy, nsym, nfn, sv, fq = mapped_map[(sym, fn, obd)]
            new_vtypes.append(vt)
            new_systems.append(sy)
            new_syms.append(nsym)
            new_fns.append(nfn)
            new_sevs.append(sv)
            new_fups.append(fq)

        mdf["vehicle_type"] = new_vtypes
        mdf["system"] = new_systems
        mdf["symptom"] = new_syms
        mdf["fault_name"] = new_fns
        mdf["severity"] = new_sevs
        mdf["followup_question"] = new_fups

        mdf.to_csv(merged_path, index=False, encoding="utf-8")
        print(f"[OK] Updated merged_internet_faults.csv ({len(mdf)} rows, all aligned to canonical faults).")


if __name__ == "__main__":
    enrich_and_save()
