#!/usr/bin/env python3
"""
Nova AI - Comprehensive Automotive Dataset Generator
Generates all CSV datasets for the diagnostic knowledge base.
Run: python generate_datasets.py
"""
import csv, os, random

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FAULT_HEADERS = ["fault_id","vehicle_type","system","symptom","fault_name","obd_code",
    "confidence","severity","required_parts","estimated_time_hours",
    "estimated_cost_range","fix_procedure","common_vehicles"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FAULT DATA: (symptoms[], fault, obd, conf, severity, parts, hrs, cost, fix, vehicles)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENGINE = [
(["engine making loud knocking noise when accelerating","heavy metallic knock from engine block under load","deep knocking sound from bottom engine during acceleration"],
"Connecting Rod Bearing Failure","P0327,P0328",0.88,"Critical","P-001,P-002",8,"8000-15000",
"Remove oil pan. Inspect rod bearings for wear. Replace bearings and check crankshaft journals. Reassemble with new gaskets.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["blue smoke coming from exhaust pipe","engine burning oil and producing blue smoke","thick blue smoke from tailpipe especially on startup"],
"Worn Piston Rings","P0524",0.85,"High","P-003,P-004",10,"12000-20000",
"Remove cylinder head. Inspect and replace worn piston rings. Check cylinder bore for scoring. Hone cylinders if needed. Reassemble.","Maruti Alto,Hyundai Verna,Honda Amaze,Tata Tiago"),

(["white smoke from exhaust and coolant level dropping","milky substance under oil cap with white exhaust smoke","engine overheating with white smoke from exhaust"],
"Head Gasket Failure","P0128",0.90,"Critical","P-005,P-006",6,"6000-12000",
"Remove cylinder head. Replace head gasket. Check head for warping and machine if needed. Replace coolant and oil. Pressure test system.","Maruti Swift,Hyundai Creta,Honda City,Tata Harrier"),

(["engine running rough at idle speed","car vibrating and shaking at idle","uneven idle with engine shaking and misfiring"],
"Vacuum Leak","P0171,P0174",0.78,"Medium","P-007",2,"1500-3000",
"Perform smoke test to locate vacuum leak. Replace cracked or broken vacuum hoses. Check intake manifold gasket. Clear codes and test.","Maruti Baleno,Hyundai i20,Tata Altroz,Kia Seltos"),

(["engine not starting just clicking sound","car won't start makes clicking noise","turning key gives rapid clicking but engine won't crank"],
"Starter Motor Failure","",0.82,"High","P-008",2,"3000-5500",
"Test battery voltage first. If battery OK inspect starter motor. Remove and bench test starter. Replace starter motor and solenoid if faulty.","Maruti Dzire,Hyundai Verna,Honda Amaze,Mahindra XUV300"),

(["engine cranks but won't start no fuel smell","car cranking continuously but not starting","engine turns over but fails to fire up"],
"Fuel Pump Failure","P0230,P0231",0.84,"High","P-009",3,"4000-7000",
"Check fuel pressure at rail. Listen for fuel pump priming. Test fuel pump relay. Replace fuel pump assembly. Clear codes.","Maruti Swift,Hyundai Creta,Tata Nexon,Honda City"),

(["check engine light on with engine misfiring","engine misfiring on one cylinder with CEL flashing","rough running with check engine light and misfire codes"],
"Ignition Coil Failure","P0300,P0301,P0302,P0303,P0304",0.86,"Medium","P-010",1,"2000-4000",
"Read fault codes to identify affected cylinder. Remove and test ignition coil. Replace faulty coil pack. Replace spark plug if damaged. Clear codes.","Maruti Baleno,Hyundai i20,Kia Seltos,Tata Altroz"),

(["spark plugs worn engine running rough and poor mileage","engine missing and poor fuel economy","difficulty starting with rough idle and reduced power"],
"Worn Spark Plugs","P0300",0.80,"Low","P-011",1,"800-2000",
"Remove and inspect spark plugs. Check electrode gap and condition. Replace all spark plugs with correct grade. Check ignition leads.","Maruti WagonR,Hyundai i10,Honda Amaze,Tata Tiago"),

(["engine overheating temperature gauge in red zone","car overheating in traffic with steam from bonnet","temperature warning light on engine getting very hot"],
"Thermostat Stuck Closed","P0128",0.83,"High","P-012",2,"1500-3000",
"Drain coolant. Remove thermostat housing. Replace thermostat. Refill coolant and bleed air from system. Test for normal operating temperature.","Maruti Swift,Hyundai Creta,Honda City,Toyota Innova"),

(["timing chain making rattling noise on cold start","chain rattle from front of engine that goes away when warm","metallic rattling from timing chain area on startup"],
"Timing Chain Tensioner Failure","P0016,P0017",0.87,"High","P-013,P-014",5,"5000-9000",
"Remove timing cover. Inspect chain tensioner and guides. Replace tensioner and chain if stretched. Reset timing marks. Reassemble.","Maruti Swift,Hyundai i20,Tata Nexon,Honda City"),

(["engine oil leaking from top of engine","oil dripping on exhaust manifold burning smell","visible oil leak around valve cover area"],
"Valve Cover Gasket Leak","",0.82,"Medium","P-015",2,"1500-3000",
"Clean area around valve cover. Remove cover bolts. Replace valve cover gasket and grommets. Torque bolts to spec. Clean spilled oil.","Maruti Ertiga,Hyundai Verna,Honda City,Mahindra XUV700"),

(["engine making ticking noise from top","ticking or tapping sound from cylinder head area","rhythmic ticking noise that increases with RPM"],
"Hydraulic Lifter Noise","",0.75,"Medium","P-016",3,"3000-6000",
"Check oil level and condition. If oil OK remove valve cover and inspect lifters. Replace collapsed or noisy lifters. Use correct grade oil.","Hyundai Creta,Tata Harrier,Honda City,Kia Seltos"),

(["serpentine belt squealing on startup","loud squealing noise from engine bay when starting car","belt squealing that gets worse in rain or cold weather"],
"Serpentine Belt Worn","",0.80,"Low","P-017",1,"800-1500",
"Inspect belt for cracks glazing and wear. Check belt tensioner. Replace serpentine belt. Replace tensioner pulley if worn.","Maruti Swift,Hyundai i20,Honda Amaze,Toyota Glanza"),

(["engine losing power going uphill","car struggling to accelerate and feels sluggish","significant loss of power during acceleration"],
"Clogged Air Filter","P0101",0.72,"Low","P-018",0.5,"300-800",
"Remove air filter element. Inspect for dirt and debris. Replace with new air filter. Check air intake duct for obstructions.","Maruti Alto,Hyundai i10,Tata Tiago,Maruti WagonR"),

(["engine vibrating excessively at idle","strong vibration felt through steering and body at idle","engine shaking badly when stationary"],
"Engine Mount Failure","",0.81,"Medium","P-019,P-020",3,"3000-6000",
"Inspect all engine mounts for cracks and deterioration. Replace failed mounts. Check transmission mount also. Torque all bolts correctly.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),

(["engine stalling randomly while driving","car suddenly dies while driving then restarts","intermittent engine shutdown while driving at low speed"],
"Crankshaft Position Sensor Failure","P0335,P0336",0.84,"High","P-021",1.5,"2000-3500",
"Read fault codes. Locate and inspect crankshaft position sensor. Check wiring connector. Replace sensor. Clear codes and test drive.","Maruti Baleno,Hyundai Verna,Tata Altroz,Kia Sonet"),

(["poor fuel economy and black smoke from exhaust","car consuming too much fuel with black exhaust","fuel consumption increased significantly with black smoke"],
"Fuel Injector Leaking","P0201,P0202",0.80,"Medium","P-022",3,"4000-8000",
"Perform injector leak test. Identify leaking injectors. Remove and clean or replace faulty injectors. Replace O-rings. Test fuel trim values.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["turbo not boosting loss of power","turbo whistle changed and car feels slow","turbo lag increased significantly with smoke from exhaust"],
"Turbocharger Failure","P0299",0.86,"Critical","P-023",6,"15000-35000",
"Check boost pressure with gauge. Inspect turbo for shaft play. Check wastegate operation. Replace turbocharger assembly. Replace oil feed lines.","Hyundai Creta Diesel,Tata Nexon Diesel,Mahindra XUV700,Kia Seltos Diesel"),

(["engine surge and fluctuating RPM at idle","RPM going up and down on its own at idle","engine hunting at idle speed RPM unstable"],
"Idle Air Control Valve Fault","P0505,P0506",0.77,"Medium","P-024",1.5,"2000-3500",
"Remove and clean IAC valve with throttle body cleaner. If cleaning fails replace IAC valve. Clean throttle body also. Reset idle parameters.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Indica"),

(["engine oil pressure warning light on","low oil pressure warning on dashboard","oil pressure gauge showing low or warning light flickering"],
"Oil Pump Wear","P0520,P0521",0.85,"Critical","P-025",5,"5000-10000",
"Check oil level and condition. Test oil pressure with mechanical gauge. If low pressure replace oil pump. Check oil pickup screen for blockage.","Maruti Swift,Hyundai Verna,Honda City,Tata Harrier"),

(["diesel engine hard to start in cold weather","diesel car cranking long time before starting in morning","glow plug warning light staying on diesel engine slow start"],
"Glow Plug Failure","P0380,P0381",0.83,"Medium","P-026",2,"2000-4000",
"Test each glow plug with multimeter. Replace failed glow plugs. Check glow plug relay and controller. Test cold start performance.","Maruti Swift Diesel,Hyundai Creta Diesel,Tata Nexon Diesel,Mahindra Bolero"),

(["engine making whining noise that increases with speed","high pitched whine from engine proportional to RPM","whining or whistling noise from alternator area"],
"Alternator Bearing Failure","",0.79,"Medium","P-027",2,"3500-6000",
"Test alternator output voltage. Listen for bearing noise. Remove alternator and replace bearing or full alternator assembly. Check belt condition.","Maruti Dzire,Hyundai i20,Honda Amaze,Tata Tigor"),

(["coolant leaking from water pump area","puddle of coolant under car near engine front","water pump making grinding noise with coolant leak"],
"Water Pump Failure","",0.84,"High","P-028,P-029",3,"3000-5500",
"Inspect water pump for leak and bearing play. Drain coolant. Replace water pump and gasket. Replace timing belt if driven by it. Refill system.","Maruti Swift,Hyundai Creta,Honda City,Toyota Innova"),

(["EGR valve causing rough idle and poor performance","engine light on with EGR flow codes","reduced power and increased emissions with CEL"],
"EGR Valve Stuck Open","P0401,P0402",0.78,"Medium","P-030",2,"3000-5000",
"Remove EGR valve. Clean carbon deposits. If stuck replace EGR valve. Clean intake manifold ports. Clear codes and test drive.","Hyundai Creta Diesel,Tata Harrier,Mahindra XUV700,Toyota Fortuner"),

(["engine backfiring through intake","popping sound from engine intake manifold","backfire and loss of power during acceleration"],
"Intake Valve Timing Issue","P0011,P0012",0.80,"High","P-031",4,"4000-7000",
"Check variable valve timing solenoid. Inspect timing chain alignment. Replace VVT solenoid if faulty. Check oil passages for blockage.","Hyundai i20,Honda City,Kia Seltos,Tata Altroz"),
]

TRANSMISSION = [
(["clutch slipping when accelerating in high gear","RPM rising but car not accelerating proportionally","clutch pedal engagement point very high and slipping"],
"Clutch Plate Worn","",0.87,"High","P-032,P-033,P-034",4,"5000-9000",
"Remove gearbox. Inspect clutch disc friction material. Replace clutch kit including disc plate pressure plate and release bearing. Resurface flywheel.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["difficulty shifting gears gear lever feels stiff","hard to engage gears especially first and reverse","gear shifting requires excessive force"],
"Clutch Cable Stretched or Broken","",0.80,"Medium","P-035",1,"800-1500",
"Inspect clutch cable for fraying and stretch. Adjust cable free play. Replace cable if worn or broken. Lubricate pivot points.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Tiago"),

(["grinding noise when shifting gears","gear crunching sound when changing from second to third","metallic grinding when engaging gear"],
"Synchronizer Ring Wear","",0.82,"High","P-036",8,"8000-15000",
"Remove gearbox and disassemble. Inspect synchronizer rings and hubs. Replace worn synchronizers. Reassemble and fill with fresh gear oil.","Maruti Swift,Hyundai Verna,Honda City,Mahindra Thar"),

(["gear popping out while driving","third gear keeps disengaging on its own","gear slips out of engagement under load"],
"Worn Gear Fork or Detent","",0.79,"High","P-037",8,"7000-12000",
"Remove gearbox. Inspect gear forks for wear. Check detent springs and balls. Replace worn components. Check gear engagement dogs.","Maruti Ertiga,Hyundai Creta,Tata Safari,Mahindra Scorpio"),

(["clutch judder when releasing clutch pedal","vibration when engaging clutch from standstill","shaking when starting from stationary in first gear"],
"Flywheel Surface Damaged","",0.81,"Medium","P-038",5,"4000-8000",
"Remove gearbox and clutch assembly. Inspect flywheel surface for hot spots and scoring. Resurface or replace flywheel. Install new clutch kit.","Maruti Swift,Hyundai i20,Honda Amaze,Tata Altroz"),

(["transmission oil leaking from gearbox","oil spots under car from gearbox area","gear oil dripping from transmission housing"],
"Gearbox Oil Seal Leak","",0.80,"Medium","P-039",3,"2000-4000",
"Identify leak location. Replace output shaft seal or input shaft seal as needed. Top up gear oil to correct level. Clean gearbox exterior.","Maruti Dzire,Hyundai Verna,Honda City,Toyota Glanza"),

(["automatic transmission slipping between gears","auto car jerking when shifting gears","delayed gear engagement in automatic car"],
"Automatic Transmission Fluid Low or Degraded","P0700,P0730",0.83,"High","P-040",2,"3000-6000",
"Check ATF level and condition. Drain and replace transmission fluid and filter. Check for leaks at pan gasket. Clear transmission codes.","Hyundai Creta AT,Kia Seltos AT,Honda City CVT,Maruti Brezza AT"),

(["CVT transmission juddering at low speed","continuous variable transmission vibrating and shuddering","CVT making whining noise with judder"],
"CVT Belt or Fluid Degradation","P0868",0.81,"High","P-041",3,"8000-15000",
"Drain CVT fluid and replace with manufacturer specified fluid. If judder persists inspect CVT belt and pulleys. Calibrate CVT control unit.","Honda City CVT,Honda Amaze CVT,Maruti Baleno CVT,Nissan Magnite CVT"),

(["noise from differential area humming at speed","humming or howling noise from rear axle","vibration and noise from rear differential increasing with speed"],
"Differential Bearing Wear","",0.80,"High","P-042",5,"6000-12000",
"Raise vehicle and check for differential play. Drain diff oil and inspect for metal particles. Replace worn bearings and seals. Refill with correct oil.","Mahindra Scorpio,Toyota Fortuner,Tata Safari,Mahindra Thar"),

(["driveshaft vibration at highway speed","vibration from underneath car at 80 kmph and above","shuddering from driveshaft during acceleration"],
"Driveshaft Universal Joint Failure","",0.82,"Medium","P-043",2,"2000-4000",
"Inspect U-joints for play and rust. Replace worn universal joints. Check driveshaft balance. Inspect center bearing if applicable.","Mahindra Scorpio,Toyota Innova,Tata Safari,Mahindra Bolero"),

(["reverse gear not engaging grinding when selecting reverse","difficult to get reverse gear","reverse gear makes noise when engaging"],
"Reverse Idler Gear Wear","",0.78,"Medium","P-044",6,"5000-9000",
"Wait for gearbox to stop rotating before engaging reverse. If still grinding remove gearbox and inspect reverse idler gear and fork. Replace worn parts.","Maruti Swift,Hyundai i20,Tata Nexon,Honda Amaze"),

(["clutch pedal staying down not returning","clutch pedal has no resistance feels spongy","hydraulic clutch not disengaging properly"],
"Clutch Master Cylinder Failure","",0.83,"Medium","P-045",2,"2500-4500",
"Check clutch fluid level. Inspect master cylinder for leaks. Bleed clutch hydraulic system. Replace master or slave cylinder if leaking.","Hyundai Creta,Kia Seltos,Tata Harrier,Mahindra XUV700"),
]

BRAKES = [
(["squealing noise when applying brakes","high pitched squeal from brakes when stopping","brakes making squeaking noise every time braking"],
"Brake Pads Worn","",0.88,"High","P-046,P-047",1,"1500-3000",
"Remove wheel and caliper. Inspect brake pad thickness. Replace worn pads. Check disc surface condition. Reassemble and bed in new pads.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["grinding noise from brakes metal on metal sound","brakes making harsh grinding noise","scraping metallic sound when pressing brake pedal"],
"Brake Disc Worn Below Minimum","",0.90,"Critical","P-046,P-047,P-048",2,"3000-6000",
"Remove wheel and caliper. Measure disc thickness with micrometer. Replace disc and pads together. Check caliper slides and pins.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),

(["brake pedal going to floor soft brakes","spongy brake pedal needing extra push to stop","brake pedal feels soft with reduced braking power"],
"Air in Brake Lines or Master Cylinder Fail","",0.85,"Critical","P-049,P-050",2,"2000-5000",
"Check brake fluid level. Inspect for leaks at all wheels and lines. Bleed brake system at all four wheels. Replace master cylinder if internal leak.","Maruti Dzire,Hyundai Verna,Honda Amaze,Tata Tigor"),

(["car pulling to one side when braking","vehicle veering left or right under braking","uneven braking car drifts to one side"],
"Brake Caliper Sticking","",0.82,"High","P-051",2,"3000-5000",
"Inspect both front calipers for free movement. Clean and lubricate caliper slide pins. Replace sticking caliper. Check brake hose for collapse.","Maruti Swift,Hyundai i20,Kia Seltos,Tata Altroz"),

(["ABS warning light on dashboard","ABS light illuminated brakes still work but no ABS","anti lock braking system warning light active"],
"ABS Wheel Speed Sensor Failure","C0035,C0040",0.84,"Medium","P-052",1.5,"2500-4500",
"Read ABS fault codes. Inspect wheel speed sensors and tone rings. Check sensor wiring for damage. Replace faulty sensor. Clear codes.","Hyundai Creta,Kia Seltos,Tata Nexon,Honda City"),

(["brake pedal vibrating when braking at high speed","steering wheel shaking when applying brakes","pulsating brake pedal during hard braking"],
"Brake Disc Warped","",0.85,"Medium","P-048",2,"2500-4500",
"Remove wheels and measure disc runout with dial gauge. If runout excessive machine or replace discs. Replace pads. Check hub face for rust.","Maruti Brezza,Hyundai Creta,Toyota Innova,Mahindra XUV700"),

(["brake fluid leaking near rear wheel","wet spot on ground near rear wheel brake area","brake fluid dripping from brake line or wheel cylinder"],
"Rear Wheel Cylinder Leak","",0.83,"Critical","P-053",2,"1500-3000",
"Inspect rear brake assembly. Identify leaking wheel cylinder. Replace wheel cylinder and brake shoes. Bleed rear brake circuit.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Tiago"),

(["handbrake not holding car rolling on slope","parking brake ineffective car rolls when parked on hill","handbrake fully pulled but car still moves"],
"Handbrake Cable Stretched","",0.80,"Medium","P-054",1,"1000-2000",
"Inspect handbrake cable and mechanism. Adjust cable tension at equalizer. Replace cable if frayed or seized. Check rear shoe adjustment.","Maruti Swift,Hyundai i20,Honda Amaze,Tata Altroz"),

(["brakes fading after prolonged use going downhill","brake pedal getting longer after continuous braking","brakes losing effectiveness on long downhill drive"],
"Brake Fade - Fluid Boiling","",0.78,"High","P-050",1,"500-1500",
"Flush and replace brake fluid with DOT4. Check brake pads for glazing and replace if needed. Inspect discs for heat damage and blue spots.","Toyota Fortuner,Mahindra Thar,Tata Harrier,Mahindra Scorpio"),

(["brake warning light on dashboard with normal pedal","red brake light on instrument cluster","brake system warning indicator illuminated"],
"Low Brake Fluid Level","",0.75,"Medium","P-050",0.5,"300-800",
"Check brake fluid reservoir level. Top up with correct specification fluid. Inspect entire brake system for leaks. Check pad wear level.","Maruti Swift,Hyundai Creta,Honda City,Kia Seltos"),

(["rear drum brakes making scraping noise","scraping sound from rear wheels while driving","continuous light rubbing noise from rear brakes"],
"Drum Brake Shoe Worn","",0.82,"Medium","P-055",1.5,"1200-2500",
"Remove rear drums. Inspect shoe lining thickness. Replace shoes and hardware springs. Adjust brake shoes. Check drum surface for scoring.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Tiago"),

(["brake hose cracked and swollen","soft brake pedal and one wheel not braking properly","brake response delayed on one wheel"],
"Brake Hose Deterioration","",0.80,"Critical","P-056",1,"1000-2000",
"Inspect flexible brake hoses for cracks swelling and leaks. Replace damaged hose. Bleed brake circuit at that wheel. Test brake balance.","Maruti Swift,Hyundai i20,Toyota Innova,Tata Nexon"),
]

ELECTRICAL = [
(["car battery dead wont start in morning","battery draining overnight car wont crank","car not starting after sitting overnight flat battery"],
"Battery End of Life","",0.85,"High","P-057",0.5,"4000-8000",
"Test battery with load tester. Check terminal connections for corrosion. Clean terminals. Replace battery if CCA below specification.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["battery warning light on while driving","charging system warning on dashboard","voltmeter showing low voltage while driving"],
"Alternator Failure","P0562",0.86,"High","P-058",2,"4000-7000",
"Test alternator output voltage should be 13.8-14.4V. Check belt tension. Replace alternator if output low. Check battery condition also.","Maruti Baleno,Hyundai Creta,Honda City,Kia Seltos"),

(["headlights dim at idle brighten when revving","lights flickering while driving","electrical accessories losing power intermittently"],
"Alternator Voltage Regulator Fault","P0562",0.79,"Medium","P-058",2,"3500-6000",
"Test alternator voltage output at various RPM. If voltage fluctuates replace voltage regulator or alternator. Check ground connections.","Maruti Dzire,Hyundai Verna,Tata Altroz,Honda Amaze"),

(["power window not working one side","window stuck halfway and motor buzzing","electric window going up very slowly or not at all"],
"Power Window Motor or Regulator Failure","",0.83,"Low","P-059",2,"2500-5000",
"Remove door panel. Test window motor with direct power. Check regulator mechanism for broken cable or gear. Replace motor or regulator as needed.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["central locking not working on all doors","remote key fob not locking unlocking car","one door not locking with central lock system"],
"Central Locking Actuator Failure","",0.80,"Low","P-060",1.5,"1500-3000",
"Test central locking from key fob and interior switch. Identify non-functioning door. Remove door panel and replace door lock actuator motor.","Maruti Baleno,Hyundai Creta,Kia Seltos,Tata Nexon"),

(["fuse keeps blowing repeatedly for same circuit","same fuse burning out after replacement","electrical fuse blowing causing accessory failure"],
"Short Circuit in Wiring","",0.78,"Medium","P-061",3,"1500-4000",
"Identify the circuit from fuse box diagram. Inspect wiring for damage chafing or exposed copper. Repair or replace damaged wire section. Replace fuse.","Maruti Swift,Hyundai i20,Honda City,Tata Altroz"),

(["all dashboard warning lights coming on randomly","instrument cluster flickering and gauges acting erratic","speedometer and fuel gauge not working properly"],
"Instrument Cluster Fault","",0.77,"Medium","P-062",3,"3000-7000",
"Check instrument cluster connectors for corrosion. Test cluster power and ground circuits. Repair solder joints. Replace cluster if circuit board failed.","Maruti Swift,Hyundai i10,Honda Amaze,Tata Tiago"),

(["wiper motor not working wipers stuck","front wipers stopped moving in rain","wiper motor running but blades not moving"],
"Wiper Motor or Linkage Failure","",0.82,"Medium","P-063",1.5,"1500-3000",
"Test wiper motor with direct power. If motor works check linkage mechanism for loose or broken joints. Replace motor or repair linkage.","Maruti WagonR,Hyundai Verna,Honda City,Tata Tigor"),

(["horn not working when pressing steering","car horn makes weak sound or no sound","horn stopped working completely"],
"Horn or Horn Relay Failure","",0.80,"Low","P-064",0.5,"500-1500",
"Test horn with direct power to check horn unit. Check horn relay in fuse box. Inspect steering clock spring if steering mounted switch. Replace faulty part.","Maruti Alto,Hyundai i10,Tata Tiago,Honda Amaze"),

(["car immobilizer activated wont allow starting","key not recognized by immobilizer system","immobilizer light blinking car wont start"],
"Immobilizer Transponder Issue","",0.81,"High","P-065",2,"3000-6000",
"Try spare key to confirm transponder issue. Check key battery. Reprogram key with diagnostic tool. Replace key transponder if damaged.","Maruti Swift,Hyundai Creta,Honda City,Kia Seltos"),

(["oxygen sensor light on poor fuel economy","O2 sensor failure code with increased fuel consumption","check engine light with oxygen sensor code"],
"Oxygen Sensor Failure","P0130,P0135,P0136",0.83,"Medium","P-066",1,"2000-4000",
"Read fault codes to identify which O2 sensor. Check sensor wiring. Replace failed oxygen sensor. Clear codes and verify fuel trim readings.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["MAP sensor or MAF sensor fault code stored","engine light on with airflow sensor reading incorrect","intake air sensor failure causing rough running"],
"Mass Air Flow Sensor Fault","P0100,P0101,P0102",0.81,"Medium","P-067",1,"2500-5000",
"Read fault codes. Remove and clean MAF sensor with MAF cleaner spray. If fault persists replace MAF sensor. Check air filter condition.","Maruti Baleno,Hyundai Creta,Kia Seltos,Honda City"),

(["crankshaft position sensor intermittent failure","engine cutting out randomly crank sensor code","intermittent no-start with crank sensor fault code"],
"Camshaft Position Sensor Failure","P0340,P0341",0.84,"High","P-068",1,"2000-3500",
"Read diagnostic codes. Inspect sensor wiring and connector. Replace camshaft position sensor. Clear codes and test for intermittent fault.","Hyundai i20,Tata Nexon,Kia Seltos,Maruti Swift"),

(["parasitic battery drain car battery dies after parking","battery going flat within two days of parking","something draining battery when car is turned off"],
"Parasitic Current Draw","",0.76,"Medium","P-061",3,"2000-5000",
"Perform parasitic draw test with multimeter on battery. Pull fuses one by one to identify circuit. Check aftermarket accessories boot light glove box light.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),

(["tail light or brake light not working","rear lights not functioning one side","burned out tail lamp or brake lamp bulb"],
"Tail Lamp Bulb or Wiring Issue","",0.85,"Low","P-069",0.5,"200-800",
"Inspect bulb for burnt filament. Replace bulb. If new bulb fails check socket for corrosion. Test wiring and ground connection to tail light assembly.","Maruti Alto,Hyundai i10,Tata Tiago,Honda Amaze"),
]

SUSPENSION = [
(["car bouncing excessively over bumps","shock absorbers leaking oil visible on strut","car continues bouncing after going over speed bump"],
"Shock Absorber Failure","",0.86,"High","P-070,P-071",3,"4000-8000",
"Inspect shock absorbers for oil leaks and bounce test. Replace shocks in pairs front or rear. Check mounting bolts and bushes.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["knocking noise from front suspension over bumps","clunking sound from front when going over potholes","front suspension making noise on rough roads"],
"Front Ball Joint Worn","",0.83,"High","P-072",2,"2000-4000",
"Jack up front end and check ball joints for play. Inspect rubber boot for damage. Replace worn ball joints. Check alignment after replacement.","Maruti Swift,Hyundai Creta,Honda City,Tata Harrier"),

(["car pulling to one side while driving straight","steering wheel not centered vehicle drifts","uneven tyre wear on one side car drifting"],
"Wheel Alignment Out","",0.82,"Low","",1,"500-1500",
"Perform four wheel alignment check. Adjust toe camber and caster to manufacturer specifications. Check for worn suspension parts causing misalignment.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["humming noise from wheel area increases with speed","wheel bearing making roaring noise while driving","grinding humming noise from front or rear wheel"],
"Wheel Bearing Failure","",0.85,"High","P-073",2,"2500-5000",
"Jack vehicle and check for wheel play. Spin wheel listening for roughness. Replace wheel bearing and hub assembly. Torque wheel nut to spec.","Maruti Baleno,Hyundai Creta,Kia Seltos,Tata Nexon"),

(["suspension bush cracked making creaking noise","creaking and squeaking noise from suspension when turning","rubber bush noise from control arm area"],
"Suspension Bush Worn","",0.80,"Medium","P-074",2,"1500-3000",
"Inspect suspension bushes for cracking and deterioration. Replace worn bushes. May need to press out old and press in new bushes.","Maruti Swift,Hyundai i20,Honda City,Tata Altroz"),

(["car leaning to one side sitting lower","one corner of car sitting lower than other","spring broken car sitting unevenly on one side"],
"Coil Spring Broken","",0.84,"High","P-075",2,"2500-5000",
"Inspect coil springs for fracture typically at top or bottom coil. Replace broken spring. Always replace in pairs on same axle. Check alignment.","Maruti Swift,Hyundai Verna,Honda Amaze,Tata Tigor"),

(["strut mount making popping noise when turning steering","knocking noise from top of suspension when turning","popping clunking from strut tower area"],
"Strut Top Mount Failure","",0.81,"Medium","P-076",2,"2000-4000",
"Remove strut assembly. Inspect top mount bearing for roughness and play. Replace strut mount. May replace strut also if worn. Align wheels after.","Maruti Swift,Hyundai i20,Honda City,Kia Seltos"),

(["anti roll bar links making rattling noise","stabilizer bar link clicking over bumps","rattling noise from front when going over small bumps"],
"Anti Roll Bar Link Failure","",0.80,"Low","P-077",1,"1000-2000",
"Inspect sway bar end links for play. Check rubber boots for damage. Replace worn links. Torque to specification.","Maruti Baleno,Hyundai Creta,Tata Nexon,Honda City"),

(["car nose diving badly when braking","excessive front end dip under braking soft front end","front suspension too soft car pitching forward when stopping"],
"Front Struts Weak","",0.79,"Medium","P-070",3,"4000-8000",
"Perform bounce test on front. Check for oil leaks. Replace both front struts. Replace strut mounts and bump stops at same time.","Maruti WagonR,Hyundai i10,Tata Tiago,Honda Amaze"),

(["rear suspension sagging with load car bottoming out","rear springs weak car scraping over speed bumps with passengers","rear end sitting very low when loaded"],
"Rear Spring Sagging","",0.80,"Medium","P-078",2,"2000-4000",
"Inspect rear springs for sag and compare ride height. Replace both rear springs. Consider uprated springs for vehicles that carry heavy loads regularly.","Toyota Innova,Mahindra Scorpio,Maruti Ertiga,Tata Sumo"),
]

COOLING = [
(["radiator leaking coolant from core or tank","green or pink coolant dripping from radiator","radiator leak visible at front of car coolant pooling"],
"Radiator Leak","",0.86,"High","P-079",3,"4000-8000",
"Pressure test cooling system to locate leak. If radiator core leaking replace radiator. If tank cracked attempt repair or replace. Refill coolant.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),

(["car overheating fan not turning on","engine temperature rising fan not spinning","electric radiator fan not working engine overheating"],
"Radiator Fan Motor or Relay Failure","",0.84,"High","P-080",1.5,"2000-4000",
"Check fan operation by jumping relay. Test fan motor with direct power. Check coolant temperature sensor signal. Replace fan motor or relay as needed.","Maruti Swift,Hyundai i20,Tata Altroz,Kia Sonet"),

(["coolant hose burst spraying coolant","rubber coolant hose split or cracked leaking","upper or lower radiator hose leaking coolant"],
"Coolant Hose Failure","",0.85,"High","P-081",1,"800-1800",
"Allow engine to cool. Drain coolant below hose level. Remove clamps and replace damaged hose. Use new clamps. Refill and bleed cooling system.","Maruti Alto,Hyundai i10,Tata Tiago,Honda Amaze"),

(["coolant expansion tank cracked leaking","overflow tank losing coolant visible crack","coolant reservoir leaking from body crack"],
"Expansion Tank Crack","",0.82,"Medium","P-082",1,"1000-2000",
"Inspect expansion tank for cracks. Replace expansion tank and cap. Refill coolant mixture to correct level. Pressure test system.","Maruti Baleno,Hyundai Verna,Honda City,Toyota Glanza"),

(["engine not reaching operating temperature fuel economy poor","thermostat stuck open engine running cold","temperature gauge not reaching middle after long driving"],
"Thermostat Stuck Open","P0128",0.80,"Medium","P-012",1.5,"1200-2500",
"Check engine temperature against coolant temp sensor reading. If engine runs cold replace thermostat. Use correct thermostat rating for vehicle.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["heater core leaking coolant inside car foggy windscreen","sweet smell inside car with coolant loss and foggy glass","coolant dripping under dashboard passenger side"],
"Heater Core Leak","",0.82,"High","P-083",5,"4000-8000",
"Confirm heater core leak by checking coolant level and cabin carpet wetness. Remove dashboard to access heater core. Replace core and O-rings. Refill system.","Maruti Swift,Hyundai i20,Honda City,Mahindra Scorpio"),

(["radiator cap not holding pressure coolant boiling over","coolant overflowing from expansion tank when hot","radiator cap pressure valve failed"],
"Radiator Cap Failure","",0.78,"Low","P-084",0.25,"200-500",
"Pressure test radiator cap. Compare to specified pressure rating. Replace cap with correct pressure rated cap. Check for system overheat damage.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["intercooler leaking boost on turbocharged diesel","turbo diesel losing power intercooler hose popped off","boost leak from intercooler pipes or core"],
"Intercooler Leak","",0.81,"Medium","P-085",2,"3000-6000",
"Check intercooler pipes for cracks and loose clamps. Pressure test intercooler system. Replace leaking intercooler or repair pipes. Tighten all clamps.","Hyundai Creta Diesel,Tata Nexon Diesel,Mahindra XUV700,Kia Seltos Diesel"),
]

FUEL = [
(["fuel injector clogged car hesitating on acceleration","engine stumbling and hesitating under load","one cylinder misfiring due to clogged injector rough running"],
"Fuel Injector Clogged","P0201,P0202,P0203",0.82,"Medium","P-022",2,"3000-6000",
"Remove fuel injectors. Ultrasonic clean or replace clogged injectors. Replace injector O-rings. Test fuel spray pattern after cleaning.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["fuel filter clogged causing loss of power","engine starving for fuel at high RPM reduced performance","car losing power under acceleration fuel starvation"],
"Fuel Filter Blocked","",0.80,"Medium","P-086",1,"800-1500",
"Locate fuel filter in-line or in-tank. Replace fuel filter. Prime fuel system. Check fuel pressure after replacement to confirm fix.","Maruti Dzire,Hyundai Verna,Honda Amaze,Tata Tigor"),

(["strong fuel smell around car possible fuel leak","petrol smell from engine bay or underneath car","fuel odor and visible wet spots near fuel lines"],
"Fuel Line Leak","",0.85,"Critical","P-087",2,"2000-4000",
"Inspect all fuel lines for cracks and wet spots. Check fuel rail connections. Replace damaged fuel line sections. Check injector O-rings for leak.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["fuel pressure regulator failed engine rich running","black smoke and strong fuel smell from exhaust","engine running very rich poor mileage and black smoke"],
"Fuel Pressure Regulator Failure","P0191,P0192",0.80,"Medium","P-088",1.5,"2500-4500",
"Test fuel pressure with gauge. Compare to spec. Check vacuum line to regulator. Replace fuel pressure regulator if pressure out of range. Clear codes.","Maruti Baleno,Hyundai Creta,Kia Seltos,Honda City"),

(["fuel gauge reading incorrect inaccurate fuel level","fuel level showing full when tank is empty","fuel gauge stuck or fluctuating randomly"],
"Fuel Level Sender Unit Failure","",0.78,"Low","P-089",2,"2000-3500",
"Test fuel level sender resistance. Compare to spec range. If out of range replace fuel level sender unit in tank. Calibrate gauge if needed.","Maruti WagonR,Hyundai i10,Tata Tiago,Honda Amaze"),

(["diesel injector pump failing loss of power and hard starting","diesel engine losing power and hunting at idle","diesel fuel injection pump noisy and inconsistent"],
"Diesel Injection Pump Failure","P0251",0.84,"Critical","P-090",6,"15000-30000",
"Test diesel injection pump output pressure. Check timing. Remove and recondition or replace injection pump. Bleed fuel system completely.","Mahindra Bolero,Tata Sumo,Toyota Innova Diesel,Mahindra Scorpio"),

(["check engine light and evap system code fuel cap area","fuel cap check engine light on gas cap not sealing","CEL with evaporative system leak code after refueling"],
"Fuel Cap Seal Damaged","P0440,P0455",0.75,"Low","P-091",0.25,"300-600",
"Inspect fuel cap seal for cracks and damage. Replace fuel cap with OEM specification cap. Clear fault codes and monitor for recurrence.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["CNG kit reducer freezing up in cold weather","CNG vehicle losing power reducer icing","CNG car performance dropping reducer issue"],
"CNG Reducer Malfunction","",0.79,"Medium","P-092",2,"3000-5000",
"Inspect CNG reducer for icing and membrane damage. Check coolant flow to reducer. Replace reducer membrane or entire unit. Recalibrate CNG system.","Maruti WagonR CNG,Hyundai i10 CNG,Maruti Alto CNG,Maruti Ertiga CNG"),
]

EXHAUST = [
(["catalytic converter rattling and check engine light","failed emissions test with catalytic converter code","exhaust smelling like rotten eggs CEL on catalyst codes"],
"Catalytic Converter Failure","P0420,P0430",0.84,"High","P-093",3,"8000-15000",
"Read fault codes. Check catalyst efficiency with exhaust gas analyzer. Replace catalytic converter. Check for root cause of failure.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["exhaust silencer rusted through making loud noise","car exhaust suddenly very loud muffler has hole","exhaust noise increased significantly silencer corroded"],
"Silencer and Muffler Corrosion","",0.85,"Medium","P-094",1.5,"2000-4000",
"Inspect exhaust system from manifold to tailpipe. Identify rusted section. Replace silencer and muffler assembly. Replace gaskets and clamps.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Tiago"),

(["exhaust manifold cracked exhaust leak ticking noise","ticking noise from exhaust manifold area that gets louder cold","exhaust leak at manifold gasket burning smell"],
"Exhaust Manifold Crack or Gasket Leak","",0.82,"Medium","P-095",3,"3000-6000",
"Inspect exhaust manifold for visible cracks. Check manifold studs for breakage. Replace manifold gasket or weld crack. Replace broken studs.","Maruti Swift,Hyundai Creta,Honda City,Toyota Innova"),

(["DPF warning light on diesel car losing power","diesel particulate filter blocked regeneration needed","DPF clogged car going into limp mode"],
"DPF Clogged (Diesel)","P2002,P2463",0.85,"High","P-096",3,"10000-20000",
"Attempt forced DPF regeneration with diagnostic tool. If unsuccessful remove and professionally clean DPF. Replace if damaged. Check root cause.","Hyundai Creta Diesel,Tata Nexon Diesel,Mahindra XUV700,Kia Seltos Diesel"),

(["EGR valve stuck causing rough idle and black smoke","EGR valve carbon buildup reduced performance","exhaust gas recirculation valve failure check engine light"],
"EGR Valve Carbon Buildup","P0401,P0402,P0404",0.80,"Medium","P-030",2,"3000-5000",
"Remove EGR valve and clean carbon deposits thoroughly. Check EGR passages in intake. Replace valve if stuck or damaged. Clear fault codes.","Hyundai Verna Diesel,Tata Harrier,Mahindra Scorpio,Toyota Fortuner Diesel"),

(["flex pipe in exhaust cracked leaking exhaust gases","flexible exhaust joint broken exhaust noise","exhaust flex section damaged vibration noise from underneath"],
"Exhaust Flex Pipe Failure","",0.80,"Medium","P-097",1.5,"1500-3000",
"Inspect flex pipe section of exhaust. Cut out damaged flex pipe and weld in replacement. Check adjacent exhaust sections for damage.","Maruti Swift,Hyundai i20,Honda City,Tata Altroz"),

(["exhaust system hanging low scraping on road","exhaust hanger rubber broken pipe dragging","exhaust bracket broken pipe loose underneath car"],
"Exhaust Hanger or Bracket Broken","",0.82,"Low","P-098",0.5,"500-1000",
"Inspect exhaust hanging rubbers and brackets. Replace broken hangers with new rubber mounts. Reposition exhaust pipe to correct height.","Maruti Dzire,Hyundai Verna,Honda Amaze,Tata Tigor"),
]

STEERING = [
(["power steering fluid leaking from rack","steering rack leaking oil turning difficult","power steering fluid dripping from steering gear"],
"Steering Rack Seal Leak","",0.84,"High","P-099",4,"5000-10000",
"Inspect steering rack seals and boots. If leaking replace rack seals or entire rack assembly. Refill power steering fluid. Bleed system and align.","Maruti Swift,Hyundai Creta,Honda City,Toyota Innova"),

(["power steering pump making whining noise","groaning noise when turning steering wheel","steering makes noise especially at full lock"],
"Power Steering Pump Failure","",0.83,"High","P-100",3,"4000-7000",
"Check power steering fluid level and condition. Listen for pump noise. Test pump pressure output. Replace pump if output low. Flush system.","Maruti Ertiga,Hyundai Verna,Honda City,Mahindra Scorpio"),

(["steering wheel has too much play feels loose","excessive free play in steering before wheels respond","steering vague and imprecise lots of play at center"],
"Tie Rod End Worn","",0.82,"High","P-101",1.5,"1500-3000",
"Jack front and check tie rod ends for play. Inspect ball joint and rubber boot. Replace worn tie rod ends. Get wheel alignment after replacement.","Maruti Swift,Hyundai i20,Tata Nexon,Honda City"),

(["EPS warning light on electric power steering not working","electric steering suddenly heavy light on dash","power steering assist failed EPS motor fault"],
"Electric Power Steering Motor Failure","C0545",0.83,"High","P-102",3,"8000-15000",
"Read EPS fault codes. Check EPS motor and torque sensor. Check steering column connections. Replace EPS motor or ECU if faulty. Calibrate system.","Maruti Swift,Hyundai i20,Tata Altroz,Kia Sonet"),

(["steering wheel vibrating at highway speed","shimmy in steering wheel at 80 to 100 kmph","steering vibrating at certain speeds"],
"Wheel Balance Off or Worn Suspension","",0.78,"Low","",1,"500-1500",
"Check and balance all four wheels. Inspect for bent rim. Check tyre for flat spots or uneven wear. Inspect suspension components if vibration persists.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),

(["steering column making clicking noise when turning","clicking clunking from steering column area","steering intermediate shaft noise when turning"],
"Steering Column Universal Joint Wear","",0.79,"Medium","P-103",2,"2000-4000",
"Inspect steering column U-joint for play. Check intermediate shaft coupling. Replace worn joint. Lubricate if applicable. Check for binding.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["power steering fluid dirty dark color","steering becoming heavy and noisy in cold weather","power steering operation degraded"],
"Power Steering Fluid Contamination","",0.75,"Low","P-104",1,"1000-2000",
"Drain power steering fluid completely. Flush system with clean fluid. Replace power steering filter if equipped. Refill with manufacturer spec fluid.","Maruti Ertiga,Hyundai Creta,Toyota Innova,Mahindra XUV700"),

(["steering wheel not returning to center after turn","steering wheel stays turned needs manual correction","poor steering returnability after cornering"],
"Steering Geometry or Caster Problem","",0.76,"Medium","",1,"500-1500",
"Check four wheel alignment specifically caster angle. Inspect upper strut mounts. Adjust alignment to spec. Check for binding in steering linkage.","Maruti Swift,Hyundai i20,Honda City,Tata Altroz"),
]

AC_HVAC = [
(["AC not blowing cold air at all","car air conditioning stopped cooling","AC system not producing cold air compressor running"],
"AC Refrigerant Leak","",0.84,"Medium","P-105",2,"2000-4000",
"Check refrigerant pressure with gauges. Perform UV dye leak test. Repair leak at identified location. Vacuum and recharge system to spec.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),

(["AC compressor making clicking or grinding noise","loud noise from AC compressor when AC turned on","AC clutch engaging and disengaging rapidly with noise"],
"AC Compressor Failure","",0.85,"High","P-106",4,"8000-15000",
"Test compressor clutch engagement. Check compressor for seized bearing or internal damage. Replace compressor. Flush system. Replace receiver dryer. Recharge.","Maruti Swift,Hyundai i20,Honda City,Kia Seltos"),

(["AC blows cold then warm intermittently","air conditioning cooling on and off cycling","AC temperature fluctuating not consistent"],
"AC Expansion Valve Stuck","",0.80,"Medium","P-107",3,"3000-5000",
"Check expansion valve for proper operation. Inspect evaporator temperature. Replace expansion valve. Vacuum and recharge system.","Maruti Baleno,Hyundai Creta,Tata Nexon,Honda City"),

(["AC condenser damaged from road debris stone impact","AC not cooling after stone hit front bumper area","visible damage to AC condenser fins leaking"],
"AC Condenser Damage","",0.85,"High","P-108",3,"5000-9000",
"Inspect condenser for impact damage and leaks. Replace condenser. Replace receiver dryer. Vacuum and recharge AC system to manufacturer spec.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["foul musty smell from AC vents","bad odor when AC or heater turned on","mouldy smell coming from car ventilation system"],
"Evaporator Bacterial Growth","",0.82,"Low","P-109",1,"800-2000",
"Treat evaporator with anti-bacterial foam cleaner through drain hole. Clean cabin air filter. Replace cabin filter if heavily contaminated. Run AC on recirculate.","Maruti Swift,Hyundai Creta,Honda City,Kia Seltos"),

(["AC blower fan not working no air from vents","blower motor stopped working completely","no air coming from any vent when fan turned on"],
"Blower Motor Failure","",0.84,"Medium","P-110",1.5,"2000-4000",
"Test blower motor resistance and power supply. Check blower motor resistor. Replace blower motor if burnt. Replace resistor if speeds not working.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["AC blower only works on highest speed setting","fan only works on speed 4 not on 1 2 3","blower motor lower speeds not functioning"],
"Blower Motor Resistor Failure","",0.85,"Low","P-111",1,"800-1500",
"Locate blower motor resistor pack. Test resistance values. Replace resistor pack. Check connector for heat damage and repair if needed.","Maruti WagonR,Hyundai i10,Tata Tiago,Honda Amaze"),

(["AC belt broken no AC and battery light","serpentine belt for AC compressor snapped","AC stopped working after belt noise"],
"AC Drive Belt Failure","",0.83,"Medium","P-112",1,"600-1200",
"Inspect AC drive belt for breakage or wear. Replace belt with correct size. Check tensioner pulley. Check compressor clutch for seizure.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Tiago"),

(["heater not working inside car no hot air","car heater blowing only cold air in winter","heating system not producing warm air"],
"Heater Valve or Core Blocked","",0.79,"Medium","P-113",3,"2000-5000",
"Check coolant temperature reaching normal. Inspect heater valve operation. Flush heater core for blockage. Replace heater valve or core if needed.","Maruti Swift,Hyundai i20,Honda City,Mahindra Thar"),

(["AC system low on gas needs frequent recharging","AC loses cooling after few months needs regas","slow refrigerant leak needing annual recharge"],
"AC System Slow Leak","",0.78,"Medium","P-105",2,"1500-3000",
"Perform detailed leak test with electronic detector and UV dye. Check all joints hoses and seals. Repair leak location. Vacuum and recharge system.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),
]

BODY = [
(["power window regulator broken window dropped into door","window fell down inside door panel","window glass slipped down and wont come up"],
"Window Regulator Cable Broken","",0.85,"Medium","P-059",1.5,"2000-4000",
"Remove door panel. Retrieve glass and secure temporarily. Replace window regulator mechanism. Reinstall glass and test operation.","Maruti Swift,Hyundai i20,Honda City,Tata Nexon"),

(["door hinge sagging door dropping when opened","driver door not closing properly sagging hinge","door hinge worn door misaligned with body"],
"Door Hinge Wear","",0.80,"Medium","P-114",2,"1500-3000",
"Inspect door hinge pins and bushings for wear. Replace hinge pins and bushings. Adjust door alignment. Lubricate hinge mechanism.","Maruti Alto,Maruti WagonR,Hyundai i10,Tata Indica"),

(["side mirror motor not working mirror stuck","electrically adjustable mirror not responding","ORVM mirror not folding or adjusting electrically"],
"ORVM Mirror Motor Failure","",0.80,"Low","P-115",1,"1500-3000",
"Test mirror motor with direct power. Check mirror switch and wiring. Replace mirror motor assembly. Program if auto-folding type.","Maruti Baleno,Hyundai Creta,Kia Seltos,Honda City"),

(["boot or dickey lock not opening","trunk lock mechanism jammed cannot open boot","boot lid latch stuck car boot wont open"],
"Boot Lock Mechanism Failure","",0.79,"Low","P-116",1,"1000-2500",
"Access boot through rear seat fold-down. Inspect lock mechanism. Replace lock actuator or latch. Check release cable and switch.","Maruti Swift,Hyundai i20,Honda Amaze,Tata Tigor"),

(["sunroof leaking water inside car when raining","water dripping from sunroof area onto headliner","sunroof drain blocked water coming inside"],
"Sunroof Drain Blockage","",0.81,"Medium","P-117",1.5,"1000-2500",
"Clear sunroof drain tubes with compressed air or thin wire. Check drain tube routing. Seal sunroof rubber gasket if cracked. Clean drain trough.","Hyundai Creta,Kia Seltos,Tata Harrier,Mahindra XUV700"),

(["windshield crack spreading from chip","front glass cracked needs replacement","stone chip on windshield that has cracked across"],
"Windshield Damage","",0.90,"Medium","P-118",2,"3000-8000",
"Assess crack size and location. If small chip attempt resin repair. If cracked replace windshield with OEM or equivalent glass. Cure adhesive before driving.","Maruti Swift,Hyundai Creta,Honda City,Tata Nexon"),
]

BIKE = [
(["bike chain loose and making noise","chain sprocket worn and slipping","motorcycle chain needs adjustment keeps loosening"],
"Chain Sprocket Kit Worn","",0.86,"Medium","P-119,P-120",1.5,"1500-3000",
"Check chain tension and stretch. Inspect sprocket teeth for hooking. Replace chain and both sprockets as set. Adjust tension and lubricate.","Hero Splendor,Bajaj Pulsar,TVS Apache,Honda Shine"),

(["bike not starting kick and self start both failing","motorcycle wont start no response from starter","bike cranks slowly and wont fire up"],
"Battery Weak or CDI Failure","",0.80,"High","P-121,P-122",1,"1500-3500",
"Test battery voltage. If battery OK test CDI unit with multimeter. Check ignition coil. Replace failed component. Check charging system output.","Hero Splendor,Honda Activa,Bajaj Pulsar,TVS Jupiter"),

(["bike carburetor running rich poor mileage","motorcycle carburetor needs cleaning fuel dripping","carb overflow fuel leaking from carburetor"],
"Carburetor Float Valve Stuck","",0.82,"Medium","P-123",1,"500-1500",
"Remove carburetor. Disassemble and clean all jets and passages. Replace float valve and gaskets. Adjust float height. Reinstall and tune mixture.","Hero Splendor,Bajaj CT,Royal Enfield Classic,TVS Star City"),

(["bike clutch plates worn clutch slipping","motorcycle clutch not gripping properly under load","clutch plates glazed bike losing power on acceleration"],
"Clutch Plate Worn (Motorcycle)","",0.85,"Medium","P-124",1.5,"1200-2500",
"Drain engine oil. Remove clutch cover. Inspect friction and steel plates. Replace clutch plate set. Adjust clutch cable free play. Refill oil.","Bajaj Pulsar,Honda Shine,TVS Apache,Royal Enfield Classic"),

(["bike self start motor not engaging","self start button pressed motor spins but engine doesnt crank","starter motor gear not meshing with flywheel"],
"Self Start Motor Bendix Failure","",0.81,"Medium","P-125",1.5,"1500-3000",
"Remove starter motor. Inspect bendix gear for wear. Replace starter motor assembly. Check starter relay. Test operation after assembly.","Honda Activa,TVS Jupiter,Hero Pleasure,Suzuki Access"),

(["bike front fork leaking oil","front suspension oil dripping from fork tubes","motorcycle front forks feel bouncy and leaking"],
"Front Fork Oil Seal Leak","",0.84,"Medium","P-126",2,"1500-3000",
"Remove front forks from motorcycle. Replace fork oil seals and dust seals. Refill with correct weight fork oil. Reassemble and test.","Bajaj Pulsar,TVS Apache,Yamaha FZ,KTM Duke"),

(["bike throttle cable stuck not returning","throttle grip not snapping back freely","motorcycle throttle sticking partially open"],
"Throttle Cable Issue (Motorcycle)","",0.82,"Medium","P-127",0.5,"300-800",
"Inspect throttle cable routing for kinks. Lubricate cable with cable lube. Replace cable if frayed or damaged. Adjust free play at handlebar.","Hero Splendor,Honda Shine,Bajaj Pulsar,TVS Star City"),

(["Royal Enfield engine making noise from right side","bullet engine tappet noise at idle","RE classic tapping noise that changes with RPM"],
"Tappet Clearance Incorrect (RE)","",0.80,"Low","",0.5,"300-600",
"Remove tappet covers. Measure tappet clearance with feeler gauge. Adjust intake and exhaust tappets to manufacturer spec. Reassemble.","Royal Enfield Classic,Royal Enfield Bullet,Royal Enfield Meteor,Royal Enfield Hunter"),

(["bike brake shoe worn rear brake not effective","rear drum brake not stopping properly","motorcycle rear brake needs more lever pressure"],
"Rear Brake Shoe Worn (Motorcycle)","",0.84,"Medium","P-128",0.5,"400-800",
"Remove rear wheel. Inspect brake shoes for lining thickness. Replace shoes if below minimum. Clean drum surface. Adjust brake lever.","Hero Splendor,Honda Activa,Bajaj CT,TVS Star City"),

(["bike speedometer cable broken speedo not working","speedometer needle not moving cable noise","motorcycle speedometer stopped showing speed"],
"Speedometer Cable Failure (Motorcycle)","",0.80,"Low","P-129",0.5,"300-600",
"Inspect cable at both ends. Replace speedometer cable. Lubricate new cable before installation. Check speedometer drive gear at wheel hub.","Hero Splendor,Hero HF,Bajaj Pulsar,Honda Shine"),

(["bike kick starter jammed wont move","kick lever stuck in one position","motorcycle kick start mechanism broken"],
"Kick Starter Mechanism Failure","",0.81,"Medium","P-130",1.5,"800-2000",
"Remove right side engine cover. Inspect kick starter gear, return spring, and ratchet. Replace broken spring or worn gear. Reassemble.","Hero Splendor,Bajaj CT,TVS Star City,Honda Shine"),

(["scooter CVT belt making noise and slipping","automatic scooter losing acceleration belt worn","drive belt worn scooter sluggish and noisy"],
"CVT Drive Belt Worn (Scooter)","",0.83,"Medium","P-131",1.5,"1200-2500",
"Remove CVT cover. Inspect drive belt for wear cracks and glazing. Replace belt. Check roller weights and variator. Reassemble and test.","Honda Activa,TVS Jupiter,Suzuki Access,Hero Pleasure"),
]

TRUCK = [
(["truck air brake not building pressure","air pressure gauge not rising brake warning","commercial vehicle air brake system leaking"],
"Air Brake Compressor or Leak","",0.85,"Critical","P-132",4,"8000-15000",
"Check air compressor output. Inspect entire air system for leaks with soapy water. Replace leaking valves hoses or compressor. Test governor cut-in pressure.","Tata Ace,Mahindra Bolero Pickup,Ashok Leyland Dost,Eicher Light Truck"),

(["truck turbo whistling loudly losing power","heavy vehicle turbo making abnormal sound","commercial diesel turbo boost dropping"],
"Turbocharger Failure (Commercial)","P0299",0.84,"Critical","P-133",6,"20000-40000",
"Check boost pressure. Inspect turbo shaft for play. Check oil supply and return lines. Replace turbocharger. Replace oil feed pipe. Use new gaskets.","Tata 407,Ashok Leyland Dost,Eicher Pro,BharatBenz"),

(["truck leaf spring broken rear sagging","one leaf in spring pack cracked","commercial vehicle rear suspension spring broken"],
"Leaf Spring Failure","",0.86,"High","P-134",3,"3000-6000",
"Jack vehicle and support chassis. Remove U-bolts and spring assembly. Replace broken leaf or entire spring pack. Reassemble with new U-bolts.","Tata Ace,Mahindra Bolero,Ashok Leyland,Eicher"),

(["truck clutch plate heavy clutch burnt smell","commercial vehicle clutch slipping with burnt smell","heavy vehicle clutch not engaging properly under load"],
"Clutch Assembly Failure (Commercial)","",0.85,"High","P-135",6,"8000-15000",
"Remove gearbox from vehicle. Replace complete clutch assembly disc pressure plate and bearing. Resurface flywheel. Reassemble and adjust.","Tata 407,Mahindra Bolero,Ashok Leyland,Eicher"),

(["truck king pin worn steering loose and wandering","front axle king pin play excessive","commercial vehicle front wheel wobbling kingpin"],
"King Pin Wear (Commercial)","",0.83,"High","P-136",4,"4000-8000",
"Jack front axle and check king pin for vertical play. Replace king pin bushes and thrust bearings. Grease new pins. Get wheel alignment.","Tata 407,Ashok Leyland,Eicher Pro,BharatBenz"),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPARE PARTS DATA
# (part_id, name, category, compatible, price_inr, supplier_pn, min_stock, weight_kg)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PARTS_DATA = [
("P-001","Connecting Rod Bearing Set","Engine","Universal",1200,"CRB-STD-01",3,0.3),
("P-002","Oil Pan Gasket","Engine","Universal",350,"OPG-UNI-01",5,0.1),
("P-003","Piston Ring Set","Engine","Universal",2500,"PRS-STD-01",2,0.5),
("P-004","Cylinder Honing Service","Engine","Universal",3000,"CHS-SVC-01",0,0),
("P-005","Head Gasket","Engine","Maruti Swift,Hyundai i20,Honda City",800,"HG-SWF-01",3,0.2),
("P-006","Cylinder Head Bolt Set","Engine","Universal",600,"CHB-UNI-01",2,0.4),
("P-007","Vacuum Hose Kit","Engine","Universal",400,"VHK-UNI-01",5,0.1),
("P-008","Starter Motor Assembly","Engine","Maruti Swift,Hyundai i20",3500,"SM-MSI-01",2,3.5),
("P-009","Fuel Pump Assembly","Fuel","Maruti Swift,Hyundai Creta",4500,"FPA-UNI-01",2,1.2),
("P-010","Ignition Coil Pack","Engine","Universal",1800,"ICP-UNI-01",3,0.5),
("P-011","Spark Plug Set (4pc)","Engine","Universal",800,"SPK-NGK-01",5,0.3),
("P-012","Thermostat","Cooling","Universal",600,"TST-UNI-01",4,0.2),
("P-013","Timing Chain Kit","Engine","Maruti Swift,Hyundai i20",3500,"TCK-MSI-01",2,1.0),
("P-014","Timing Chain Tensioner","Engine","Universal",1200,"TCT-UNI-01",3,0.3),
("P-015","Valve Cover Gasket","Engine","Universal",450,"VCG-UNI-01",5,0.1),
("P-016","Hydraulic Lifter Set","Engine","Universal",2800,"HLS-UNI-01",2,0.6),
("P-017","Serpentine Belt","Engine","Universal",650,"SRB-UNI-01",4,0.3),
("P-018","Air Filter","Engine","Universal",250,"AFL-UNI-01",10,0.2),
("P-019","Engine Mount Front","Engine","Maruti Swift,Hyundai i20",1200,"EMF-MSI-01",3,1.5),
("P-020","Engine Mount Rear","Engine","Maruti Swift,Hyundai i20",1000,"EMR-MSI-01",3,1.2),
("P-021","Crankshaft Position Sensor","Engine","Universal",1500,"CPS-UNI-01",3,0.1),
("P-022","Fuel Injector","Fuel","Universal",2000,"FIJ-UNI-01",4,0.2),
("P-023","Turbocharger Assembly","Engine","Hyundai Creta,Tata Nexon",18000,"TCA-UNI-01",1,8.0),
("P-024","Idle Air Control Valve","Engine","Universal",1800,"IAC-UNI-01",2,0.2),
("P-025","Oil Pump Assembly","Engine","Universal",3500,"OPA-UNI-01",1,1.5),
("P-026","Glow Plug Set (4pc)","Engine","Diesel",1200,"GPS-UNI-01",3,0.2),
("P-027","Alternator Assembly","Electrical","Universal",4500,"ALT-UNI-01",2,4.0),
("P-028","Water Pump","Cooling","Universal",2000,"WTP-UNI-01",3,1.0),
("P-029","Water Pump Gasket","Cooling","Universal",150,"WPG-UNI-01",5,0.05),
("P-030","EGR Valve","Exhaust","Diesel",3500,"EGR-UNI-01",2,0.8),
("P-031","VVT Solenoid","Engine","Universal",2200,"VVT-UNI-01",2,0.3),
("P-032","Clutch Disc","Transmission","Maruti Swift,Hyundai i20",1800,"CLD-MSI-01",3,1.5),
("P-033","Pressure Plate","Transmission","Maruti Swift,Hyundai i20",2200,"PPL-MSI-01",2,3.0),
("P-034","Release Bearing","Transmission","Universal",800,"RBR-UNI-01",3,0.3),
("P-035","Clutch Cable","Transmission","Maruti Alto,WagonR",350,"CCB-MSI-01",5,0.3),
("P-036","Synchronizer Ring Set","Transmission","Universal",3500,"SRS-UNI-01",1,0.5),
("P-037","Gear Fork","Transmission","Universal",2500,"GFK-UNI-01",1,0.4),
("P-038","Flywheel","Transmission","Universal",4000,"FLW-UNI-01",1,5.0),
("P-039","Gearbox Oil Seal","Transmission","Universal",350,"GOS-UNI-01",5,0.05),
("P-040","ATF Fluid (1L)","Transmission","Automatic",600,"ATF-UNI-01",5,1.0),
("P-041","CVT Fluid (1L)","Transmission","CVT",900,"CVF-UNI-01",3,1.0),
("P-042","Differential Bearing Set","Transmission","Universal",2500,"DBS-UNI-01",2,0.5),
("P-043","Universal Joint","Transmission","Universal",800,"UJT-UNI-01",4,0.3),
("P-044","Reverse Idler Gear","Transmission","Universal",1800,"RIG-UNI-01",1,0.4),
("P-045","Clutch Master Cylinder","Transmission","Hydraulic Clutch",2000,"CMC-UNI-01",2,0.5),
("P-046","Front Brake Pad Set","Brakes","Universal",1200,"FBP-UNI-01",5,0.8),
("P-047","Rear Brake Pad Set","Brakes","Universal",1000,"RBP-UNI-01",5,0.7),
("P-048","Brake Disc Front","Brakes","Universal",1800,"BDF-UNI-01",3,3.0),
("P-049","Brake Master Cylinder","Brakes","Universal",2500,"BMC-UNI-01",2,1.0),
("P-050","Brake Fluid DOT4 (500ml)","Brakes","Universal",250,"BFL-UNI-01",8,0.5),
("P-051","Brake Caliper Assembly","Brakes","Universal",3500,"BCA-UNI-01",2,2.5),
("P-052","ABS Wheel Speed Sensor","Brakes","Universal",2000,"AWS-UNI-01",3,0.1),
("P-053","Rear Wheel Cylinder","Brakes","Universal",600,"RWC-UNI-01",3,0.3),
("P-054","Handbrake Cable","Brakes","Universal",500,"HBC-UNI-01",3,0.3),
("P-055","Rear Brake Shoe Set","Brakes","Universal",800,"RBS-UNI-01",4,0.5),
("P-056","Brake Hose Flexible","Brakes","Universal",400,"BHF-UNI-01",4,0.2),
("P-057","Car Battery 12V 45Ah","Electrical","Universal",5000,"BAT-45-01",3,12.0),
("P-058","Alternator Assembly Reco","Electrical","Universal",4000,"ALR-UNI-01",2,4.0),
("P-059","Window Regulator Assembly","Body","Universal",2500,"WRA-UNI-01",2,1.0),
("P-060","Door Lock Actuator","Body","Universal",1200,"DLA-UNI-01",3,0.2),
("P-061","Electrical Wire Roll 10m","Electrical","Universal",300,"EWR-UNI-01",5,0.5),
("P-062","Instrument Cluster Repair","Electrical","Universal",3000,"ICR-UNI-01",0,0),
("P-063","Wiper Motor Assembly","Body","Universal",1800,"WMA-UNI-01",2,1.0),
("P-064","Horn Assembly","Electrical","Universal",400,"HRN-UNI-01",4,0.3),
("P-065","Immobilizer Key Transponder","Electrical","Universal",3000,"IKT-UNI-01",1,0.05),
("P-066","Oxygen Sensor","Electrical","Universal",2000,"OXS-UNI-01",3,0.15),
("P-067","MAF Sensor","Electrical","Universal",3000,"MAF-UNI-01",2,0.2),
("P-068","Camshaft Position Sensor","Electrical","Universal",1500,"CMS-UNI-01",3,0.1),
("P-069","Tail Lamp Bulb Set","Electrical","Universal",150,"TLB-UNI-01",10,0.05),
("P-070","Front Shock Absorber","Suspension","Universal",2500,"FSA-UNI-01",4,2.5),
("P-071","Rear Shock Absorber","Suspension","Universal",2000,"RSA-UNI-01",4,2.0),
("P-072","Ball Joint Lower","Suspension","Universal",800,"BJL-UNI-01",4,0.4),
("P-073","Wheel Bearing and Hub","Suspension","Universal",1800,"WBH-UNI-01",3,1.0),
("P-074","Suspension Bush Kit","Suspension","Universal",600,"SBK-UNI-01",4,0.3),
("P-075","Front Coil Spring","Suspension","Universal",1800,"FCS-UNI-01",2,2.0),
("P-076","Strut Top Mount","Suspension","Universal",1200,"STM-UNI-01",3,0.5),
("P-077","Anti Roll Bar Link","Suspension","Universal",600,"ARL-UNI-01",4,0.3),
("P-078","Rear Coil Spring","Suspension","Universal",1500,"RCS-UNI-01",2,1.8),
("P-079","Radiator Assembly","Cooling","Universal",5000,"RAD-UNI-01",2,4.0),
("P-080","Radiator Fan Motor","Cooling","Universal",2000,"RFM-UNI-01",2,1.5),
("P-081","Radiator Hose Set","Cooling","Universal",600,"RHS-UNI-01",4,0.3),
("P-082","Coolant Expansion Tank","Cooling","Universal",800,"CET-UNI-01",3,0.3),
("P-083","Heater Core","Cooling","Universal",3000,"HTC-UNI-01",1,1.5),
("P-084","Radiator Cap","Cooling","Universal",150,"RCP-UNI-01",8,0.05),
("P-085","Intercooler Assembly","Cooling","Diesel Turbo",5000,"ICA-UNI-01",1,3.0),
("P-086","Fuel Filter","Fuel","Universal",400,"FFL-UNI-01",6,0.2),
("P-087","Fuel Line Repair Kit","Fuel","Universal",600,"FLR-UNI-01",3,0.2),
("P-088","Fuel Pressure Regulator","Fuel","Universal",2000,"FPR-UNI-01",2,0.2),
("P-089","Fuel Level Sender","Fuel","Universal",1500,"FLS-UNI-01",2,0.3),
("P-090","Diesel Injection Pump Reco","Fuel","Diesel",18000,"DIP-UNI-01",1,6.0),
("P-091","Fuel Cap","Fuel","Universal",300,"FCP-UNI-01",5,0.1),
("P-092","CNG Reducer Kit","Fuel","CNG",3000,"CRK-UNI-01",1,1.5),
("P-093","Catalytic Converter","Exhaust","Universal",10000,"CAT-UNI-01",1,5.0),
("P-094","Silencer Muffler Assembly","Exhaust","Universal",2500,"SMA-UNI-01",2,4.0),
("P-095","Exhaust Manifold Gasket","Exhaust","Universal",400,"EMG-UNI-01",4,0.1),
("P-096","DPF Filter Assembly","Exhaust","Diesel",12000,"DPF-UNI-01",1,6.0),
("P-097","Exhaust Flex Pipe","Exhaust","Universal",1200,"EFP-UNI-01",3,0.5),
("P-098","Exhaust Hanger Rubber Set","Exhaust","Universal",300,"EHR-UNI-01",6,0.1),
("P-099","Steering Rack Assembly","Steering","Universal",7000,"SRA-UNI-01",1,5.0),
("P-100","Power Steering Pump","Steering","Universal",4500,"PSP-UNI-01",1,2.5),
("P-101","Tie Rod End","Steering","Universal",700,"TRE-UNI-01",4,0.3),
("P-102","EPS Motor Assembly","Steering","Universal",10000,"EPS-UNI-01",1,3.0),
("P-103","Steering Column U-Joint","Steering","Universal",1500,"SCU-UNI-01",2,0.4),
("P-104","Power Steering Fluid (1L)","Steering","Universal",400,"PSF-UNI-01",5,1.0),
("P-105","AC Refrigerant R134a (1kg)","AC","Universal",800,"ACR-UNI-01",5,1.0),
("P-106","AC Compressor Assembly","AC","Universal",10000,"ACC-UNI-01",1,6.0),
("P-107","AC Expansion Valve","AC","Universal",1500,"AEV-UNI-01",2,0.2),
("P-108","AC Condenser Assembly","AC","Universal",5000,"ACD-UNI-01",1,3.0),
("P-109","AC Evaporator Cleaner","AC","Universal",300,"AEC-UNI-01",8,0.3),
("P-110","Blower Motor Assembly","AC","Universal",2000,"BMA-UNI-01",2,1.0),
("P-111","Blower Motor Resistor","AC","Universal",500,"BMR-UNI-01",3,0.1),
("P-112","AC Compressor Belt","AC","Universal",450,"ACB-UNI-01",4,0.2),
("P-113","Heater Valve","AC","Universal",800,"HTV-UNI-01",2,0.2),
("P-114","Door Hinge Pin Set","Body","Universal",400,"DHP-UNI-01",4,0.2),
("P-115","ORVM Mirror Assembly","Body","Universal",2000,"ORM-UNI-01",2,0.5),
("P-116","Boot Lock Assembly","Body","Universal",1000,"BLA-UNI-01",2,0.3),
("P-117","Sunroof Seal Kit","Body","Universal",1200,"SSK-UNI-01",1,0.2),
("P-118","Windshield Glass","Body","Model Specific",4000,"WSG-UNI-01",1,8.0),
("P-119","Chain Kit (Bike)","Bike","Universal Bike",1200,"BCK-UNI-01",4,1.0),
("P-120","Sprocket Set (Bike)","Bike","Universal Bike",800,"BSS-UNI-01",4,0.8),
("P-121","Bike Battery 12V","Bike","Universal Bike",1200,"BBT-UNI-01",4,2.5),
("P-122","CDI Unit","Bike","Universal Bike",1500,"CDI-UNI-01",2,0.2),
("P-123","Carburetor Assembly (Bike)","Bike","Carb Bikes",2000,"CBA-UNI-01",2,0.8),
("P-124","Clutch Plate Set (Bike)","Bike","Universal Bike",600,"CPS-BK-01",4,0.3),
("P-125","Self Start Motor (Bike)","Bike","Universal Bike",1800,"SSM-UNI-01",2,1.0),
("P-126","Front Fork Seal Kit","Bike","Universal Bike",400,"FFS-UNI-01",4,0.1),
("P-127","Throttle Cable (Bike)","Bike","Universal Bike",200,"TCB-UNI-01",6,0.1),
("P-128","Rear Brake Shoe (Bike)","Bike","Universal Bike",250,"RBS-BK-01",6,0.2),
("P-129","Speedometer Cable (Bike)","Bike","Universal Bike",200,"SMC-UNI-01",4,0.1),
("P-130","Kick Starter Spring","Bike","Universal Bike",200,"KSS-UNI-01",4,0.1),
("P-131","CVT Belt (Scooter)","Bike","Scooter",900,"CVB-UNI-01",3,0.3),
("P-132","Air Brake Valve","Truck","Commercial",4000,"ABV-UNI-01",2,2.0),
("P-133","Turbo Assembly (Commercial)","Truck","Commercial",25000,"TAC-UNI-01",1,10.0),
("P-134","Leaf Spring Pack","Truck","Commercial",3000,"LSP-UNI-01",2,15.0),
("P-135","Clutch Assembly (Commercial)","Truck","Commercial",8000,"CAC-UNI-01",1,8.0),
("P-136","King Pin Kit","Truck","Commercial",2000,"KPK-UNI-01",3,1.5),
("P-137","Engine Oil 5W30 (4L)","Fluids","Universal",1800,"EO530-01",8,4.0),
("P-138","Engine Oil 5W40 (4L)","Fluids","Universal",2200,"EO540-01",6,4.0),
("P-139","Engine Oil 10W40 (4L)","Fluids","Universal",1500,"EO1040-01",6,4.0),
("P-140","Gear Oil 75W90 (1L)","Fluids","Universal",500,"GO7590-01",5,1.0),
("P-141","Coolant Concentrate (1L)","Fluids","Universal",400,"CCT-UNI-01",8,1.0),
("P-142","Cabin Air Filter","Filters","Universal",350,"CAF-UNI-01",6,0.1),
("P-143","Oil Filter","Filters","Universal",250,"OFL-UNI-01",10,0.2),
("P-144","Wheel Nut Set","Misc","Universal",300,"WNS-UNI-01",5,0.5),
("P-145","Tyre Tube (Bike)","Bike","Universal Bike",250,"TTB-UNI-01",6,0.3),
("P-146","Front Brake Disc (Bike)","Bike","Universal Bike",800,"FBD-BK-01",3,1.0),
("P-147","Headlight Bulb H4","Electrical","Universal",250,"HBH4-01",8,0.05),
("P-148","Side Indicator Bulb","Electrical","Universal",50,"SIB-UNI-01",10,0.02),
("P-149","Wiper Blade Set","Body","Universal",400,"WBS-UNI-01",5,0.2),
("P-150","Battery Terminal Set","Electrical","Universal",100,"BTS-UNI-01",10,0.1),
("P-151","Radiator Coolant Pre-mixed (1L)","Fluids","Universal",300,"RCM-UNI-01",8,1.0),
("P-152","Silicone Gasket Maker","Misc","Universal",200,"SGM-UNI-01",6,0.1),
("P-153","Thread Lock Medium","Misc","Universal",250,"TLM-UNI-01",4,0.05),
("P-154","Brake Cleaner Spray","Misc","Universal",200,"BCS-UNI-01",8,0.4),
("P-155","WD-40 Penetrant Spray","Misc","Universal",250,"WDP-UNI-01",6,0.4),
("P-156","Dielectric Grease","Misc","Universal",150,"DGR-UNI-01",4,0.1),
("P-157","Cable Ties Pack (100)","Misc","Universal",100,"CTP-UNI-01",5,0.2),
("P-158","Fuse Assortment Kit","Electrical","Universal",200,"FAK-UNI-01",3,0.1),
("P-159","Hose Clamp Assortment","Misc","Universal",300,"HCA-UNI-01",4,0.3),
("P-160","Exhaust Paste Sealant","Exhaust","Universal",150,"EPS-UNI-01",5,0.2),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VEHICLES DATABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VEHICLES_DATA = [
("V-01","Maruti","Swift","LXi,VXi,ZXi,ZXi+","2018-2025","Petrol",1197,"Timing chain noise,Suspension bush wear,AC compressor failure"),
("V-02","Maruti","Alto","STD,LXi,VXi","2015-2025","Petrol",796,"Starter motor issue,Clutch cable stretch,Wiper motor failure"),
("V-03","Maruti","Baleno","Sigma,Delta,Zeta,Alpha","2019-2025","Petrol",1197,"Ignition coil failure,MAF sensor issue,CVT judder"),
("V-04","Maruti","Brezza","LXi,VXi,ZXi,ZXi+","2022-2025","Petrol",1462,"Brake disc warp,Suspension noise,AC not cooling"),
("V-05","Maruti","Dzire","LXi,VXi,ZXi,ZXi+","2017-2025","Petrol",1197,"Starter motor wear,Alternator failure,Window regulator break"),
("V-06","Maruti","WagonR","LXi,VXi,ZXi","2019-2025","Petrol/CNG",1197,"CNG reducer issue,IAC valve fault,Rear spring sag"),
("V-07","Maruti","Ertiga","LXi,VXi,ZXi,ZXi+","2019-2025","Petrol/CNG",1462,"Engine mount wear,Power steering pump noise,Rear shock leak"),
("V-08","Hyundai","i20","Magna,Sportz,Asta","2020-2025","Petrol",1197,"Timing chain noise,Clutch judder,Ball joint wear"),
("V-09","Hyundai","Creta","E,EX,S,SX,SX(O)","2020-2025","Petrol/Diesel",1497,"Turbo failure diesel,Sunroof drain block,ABS sensor fault"),
("V-10","Hyundai","Venue","E,S,SX,SX+","2019-2025","Petrol",1197,"Clutch cable issue,Blower resistor fail,Fuel pump weak"),
("V-11","Hyundai","Verna","E,S,SX,SX(O)","2017-2025","Petrol/Diesel",1497,"Injector issue diesel,Alternator fault,Gear oil seal leak"),
("V-12","Hyundai","i10 Nios","Era,Magna,Sportz,Asta","2019-2025","Petrol/CNG",1197,"Spark plug wear,Horn failure,Door lock actuator"),
("V-13","Tata","Nexon","XE,XM,XZ,XZ+","2020-2025","Petrol/Diesel",1199,"Turbo hose leak diesel,Suspension bush noise,Clutch judder"),
("V-14","Tata","Punch","Pure,Adventure,Accomplished,Creative","2021-2025","Petrol",1199,"Engine mount vibration,Brake pad wear,AC gas leak"),
("V-15","Tata","Altroz","XE,XM,XZ,XZ+","2020-2025","Petrol/Diesel",1199,"Clutch plate wear,IAC valve,Brake caliper stick"),
("V-16","Tata","Tiago","XE,XM,XT,XZ+","2019-2025","Petrol/CNG",1199,"Wiper motor issue,CNG reducer,Drum brake shoe wear"),
("V-17","Tata","Harrier","XE,XM,XZ,XZ+","2019-2025","Diesel",1956,"DPF clogging,Turbo bearing,EGR carbon buildup"),
("V-18","Tata","Safari","XE,XM,XZ,XZ+,Adventure","2021-2025","Diesel",1956,"Differential noise,Leaf spring sag,AC condenser damage"),
("V-19","Honda","City","V,VX,ZX","2020-2025","Petrol",1498,"CVT judder,Ignition coil,Steering rack leak"),
("V-20","Honda","Amaze","E,S,VX","2018-2025","Petrol/Diesel",1199,"Starter motor,Brake master cylinder,Door hinge sag"),
("V-21","Honda","Elevate","SV,V,VX,ZX","2023-2025","Petrol",1498,"Ball joint wear,Window regulator,Engine mount"),
("V-22","Mahindra","XUV700","MX,AX3,AX5,AX7","2021-2025","Petrol/Diesel",1997,"Turbo actuator,EPS motor fault,Sunroof leak"),
("V-23","Mahindra","Scorpio-N","Z4,Z6,Z8,Z8L","2022-2025","Petrol/Diesel",1997,"Leaf spring break,King pin wear,Air filter clog"),
("V-24","Mahindra","Thar","AX,LX","2020-2025","Petrol/Diesel",1497,"Driveshaft vibration,Power steering leak,Heater valve stuck"),
("V-25","Mahindra","Bolero","B2,B4,B6","2015-2025","Diesel",1493,"Glow plug failure,Clutch heavy,Injector pump wear"),
("V-26","Mahindra","XUV300","W4,W6,W8","2019-2025","Petrol/Diesel",1197,"Turbo hose pop,Brake disc warp,Central locking fail"),
("V-27","Toyota","Innova Crysta","GX,VX,ZX","2016-2025","Petrol/Diesel",2393,"Water pump failure,Rear spring sag,AC compressor noise"),
("V-28","Toyota","Fortuner","4x2,4x4","2016-2025","Petrol/Diesel",2755,"DPF clog,Differential noise,Brake fade downhill"),
("V-29","Toyota","Glanza","E,S,G,V","2022-2025","Petrol",1197,"Same as Baleno platform,Timing chain,Serpentine belt"),
("V-30","Kia","Seltos","HTE,HTK,HTK+,HTX,GTX+","2019-2025","Petrol/Diesel",1497,"Clutch judder diesel,ABS sensor,MAF sensor fault"),
("V-31","Kia","Sonet","HTE,HTK,HTK+,HTX+,GTX+","2020-2025","Petrol/Diesel",1197,"Crankshaft sensor intermittent,Blower motor fail,Brake squeal"),
("V-32","Kia","Carens","Premium,Prestige,Luxury","2022-2025","Petrol/Diesel",1497,"Clutch master cylinder,Rear shock leak,Electrical fuse blow"),
("V-33","MG","Hector","Style,Super,Smart,Sharp","2019-2025","Petrol/Diesel",1451,"Turbocharger hose,Instrument cluster flicker,Panoramic sunroof leak"),
("V-34","MG","Astor","Style,Super,Smart,Sharp","2021-2025","Petrol",1349,"Engine mount vibration,Steering noise turning,AC expansion valve"),
("V-35","Skoda","Kushaq","Active,Ambition,Style","2021-2025","Petrol",999,"Timing chain rattle,DSG mechatronic,EPC light on"),
("V-36","VW","Taigun","Comfortline,Highline,Topline","2021-2025","Petrol",999,"Similar Kushaq platform,Turbo wastegate,DSG clutch"),
("V-37","Hero","Splendor Plus","Kick,Self,i3S","2015-2025","Petrol",97,"Chain sprocket worn,Carburetor overflow,Kick starter jam"),
("V-38","Honda","Activa 6G","STD,DLX","2020-2025","Petrol",109,"CVT belt wear,Self start motor,Battery drain"),
("V-39","Bajaj","Pulsar 150","Standard,Twin Disc","2018-2025","Petrol",149,"CDI failure,Front fork seal leak,Carburetor tuning"),
("V-40","TVS","Apache RTR 160","2V,4V","2018-2025","Petrol",159,"CDI unit fault,Clutch plate glazing,Chain tension"),
("V-41","Royal Enfield","Classic 350","Classic,Chrome,Signals","2021-2025","Petrol",349,"Tappet clearance,Engine oil leak,Rear brake shoe"),
("V-42","Yamaha","FZ-S","V3,V4","2019-2025","Petrol",149,"Throttle position sensor,Chain kit wear,Battery weak"),
("V-43","KTM","Duke 200","Standard","2020-2025","Petrol",199,"Radiator fan issue,Clutch slave cylinder,Fork seal"),
("V-44","Suzuki","Access 125","Standard,SE","2018-2025","Petrol",124,"CVT roller wear,Self start relay,Brake cable stretch"),
("V-45","TVS","Jupiter","Classic,ZX","2018-2025","Petrol",109,"Belt wear,Self start Bendix,Body panel rattle"),
("V-46","Hero","HF Deluxe","Kick,Self","2015-2025","Petrol",97,"Carburetor cleaning,Chain adjust,CDI failure"),
("V-47","Bajaj","Platina","H-Gear,Comfortec","2018-2025","Petrol",102,"Chain sprocket,Speedometer cable,Brake shoe"),
("V-48","Tata","Ace Gold","Petrol,Diesel,CNG","2018-2025","Multi",702,"Air brake leak,Clutch heavy,Leaf spring crack"),
("V-49","Ashok Leyland","Dost","Plus,Strong","2018-2025","Diesel",1478,"Turbo failure,Air compressor,King pin wear"),
("V-50","Eicher","Pro 2049","Standard","2018-2025","Diesel",2956,"Injector pump,Air brake valve,Differential seal"),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GENERATION FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_vehicle_type(vehicles_str):
    v = vehicles_str.lower()
    if any(k in v for k in ["hero","honda activa","bajaj","tvs","royal enfield","yamaha","ktm","suzuki access","suzuki gixxer"]):
        return "Bike"
    if any(k in v for k in ["tata ace","ashok leyland","eicher","bharat"]):
        return "Truck"
    if any(k in v for k in ["fortuner","scorpio","thar","safari","harrier","xuv700"]):
        return "SUV"
    return "Car"

def generate_vehicle_faults():
    """Generate the vehicle faults CSV with 500+ entries."""
    all_systems = [
        ("Engine", ENGINE), ("Transmission", TRANSMISSION), ("Brakes", BRAKES),
        ("Electrical", ELECTRICAL), ("Suspension", SUSPENSION), ("Cooling", COOLING),
        ("Fuel System", FUEL), ("Exhaust", EXHAUST), ("Steering", STEERING),
        ("AC/HVAC", AC_HVAC), ("Body", BODY), ("Bike", BIKE), ("Truck/Commercial", TRUCK)
    ]
    
    rows = []
    fid = 1
    
    for system_name, faults in all_systems:
        for fault_tuple in faults:
            symptoms, fault_name, obd, conf, severity, parts, time_hrs, cost, fix, vehicles = fault_tuple
            vtype = get_vehicle_type(vehicles)
            if system_name == "Bike":
                vtype = "Bike"
            elif system_name == "Truck/Commercial":
                vtype = "Truck"
            
            for symptom in symptoms:
                rows.append([
                    f"F{fid:04d}", vtype, system_name, symptom, fault_name,
                    obd, conf, severity, parts, time_hrs, cost, fix, vehicles
                ])
                fid += 1
    
    # Generate additional composite symptom entries for richer dataset
    composite_additions = [
        ("Car","Engine","car not starting and battery seems fine engine cranks slowly","Starter Motor Failure","",0.80,"High","P-008",2,"3000-5500","Test battery then starter motor. Replace starter if faulty.","Maruti Swift,Hyundai i20"),
        ("Car","Engine","smell of burning oil from engine bay with blue smoke","Valve Stem Seal Leak","",0.82,"High","P-003",6,"5000-10000","Replace valve stem seals. Check valve guides for wear.","Honda City,Hyundai Verna"),
        ("Car","Engine","engine misfiring in rain or wet weather","Ignition Lead Moisture","P0300",0.75,"Low","P-010",1,"1000-2000","Dry and replace ignition leads. Apply dielectric grease to connections.","Maruti WagonR,Hyundai i10"),
        ("Car","Engine","exhaust popping on deceleration with smell","Exhaust Valve Not Seating","P0300",0.78,"Medium","P-031",5,"5000-9000","Perform valve job. Lap or replace exhaust valves. Replace valve seals.","Maruti Swift,Honda City"),
        ("Car","Engine","engine overheating only in traffic not on highway","Radiator Fan Relay Failure","",0.81,"High","P-080",1,"1000-2500","Test fan relay. Replace relay. Check coolant temp sensor input.","Hyundai Creta,Tata Nexon"),
        ("Car","Brakes","brakes making noise only in morning first few stops","Brake Disc Surface Rust","",0.70,"Low","P-046",0,"0-0","Normal condition. Light surface rust cleared by first few brake applications. No action needed.","Universal"),
        ("Car","Brakes","brake pedal pulsating at low speed gentle braking","Brake Disc Thickness Variation","",0.79,"Medium","P-048",2,"2500-4500","Measure disc thickness variation DTV. Machine or replace discs if out of spec.","Maruti Swift,Hyundai Creta"),
        ("Car","Electrical","car accessories working but engine wont crank at all","Starter Relay or Ignition Switch Failure","",0.80,"Medium","P-008",1.5,"1500-3000","Test voltage at starter solenoid. Check ignition switch. Replace relay or switch.","Maruti Dzire,Tata Tigor"),
        ("Car","Electrical","battery draining when parked boot light or glove box light staying on","Interior Light Switch Faulty","",0.77,"Low","P-061",1,"500-1500","Check all courtesy lights. Replace faulty switch. Check boot pin switch.","Universal"),
        ("Car","Transmission","car jerking at low speed in first gear","Clutch Damper Spring Weak","",0.76,"Medium","P-032",4,"5000-9000","Replace clutch disc with fresh damper springs. Check flywheel surface.","Maruti Swift,Hyundai i20"),
        ("Car","Transmission","automatic car not moving in drive delayed engagement","Low ATF Causing Clutch Pack Slip","P0700",0.82,"High","P-040",2,"3000-6000","Check ATF level. Top up or change fluid and filter. Test line pressure.","Hyundai Creta AT,Kia Seltos AT"),
        ("Car","Suspension","car making rattling noise front end going over small bumps","Stabilizer Link Ball Joint Worn","",0.81,"Low","P-077",1,"1000-2000","Inspect sway bar links. Replace worn links in pairs.","Maruti Baleno,Kia Sonet"),
        ("Car","Cooling","engine temperature gauge fluctuating up and down","Thermostat Sticking Intermittent","P0128",0.78,"Medium","P-012",1.5,"1200-2500","Replace thermostat. Flush cooling system. Refill with fresh coolant.","Maruti Swift,Tata Nexon"),
        ("Car","Cooling","steam from under bonnet with sweet smell","Coolant Hose Pin Hole Leak","",0.83,"High","P-081",1,"800-1800","Pressure test system. Locate pinhole in hose. Replace damaged hose and clamps.","Hyundai i20,Honda City"),
        ("Car","Fuel System","car hesitating and surging during acceleration","Throttle Body Carbon Buildup","P0121,P0122",0.79,"Medium","P-024",1,"1000-2000","Remove and clean throttle body with carb cleaner. Reset idle relearn procedure.","Maruti Swift,Hyundai i20"),
        ("Car","Exhaust","rattling noise from underneath car exhaust heat shield","Exhaust Heat Shield Loose","",0.80,"Low","P-098",0.5,"300-800","Locate loose heat shield. Reattach with new clamps or worm drive bands.","Universal"),
        ("Car","Steering","steering wheel off center after hitting pothole","Wheel Alignment Disturbed","",0.82,"Low","",1,"500-1500","Perform 4 wheel alignment. Check for bent steering or suspension parts.","Universal"),
        ("Car","AC/HVAC","AC cooling reduces after 30 minutes of driving","AC Receiver Dryer Saturated","",0.77,"Medium","P-108",2,"2000-4000","Replace receiver dryer. Vacuum system. Recharge with correct refrigerant amount.","Maruti Swift,Hyundai Creta"),
        ("Car","AC/HVAC","water dripping on passenger feet from under dashboard","AC Drain Pipe Blocked","",0.83,"Low","P-109",0.5,"300-500","Locate and clear AC evaporator drain pipe with compressed air. Clean evaporator tray.","Universal"),
        ("Bike","Bike","bike chain making too much noise and vibration","Chain and Sprocket Kit Worn Beyond Limit","",0.85,"Medium","P-119,P-120",1.5,"1500-3000","Replace chain and both sprockets as set. Adjust tension. Lubricate chain.","Hero Splendor,Bajaj Pulsar"),
        ("Bike","Bike","scooter not starting electric start motor just whirring","Scooter Starter Clutch Failure","",0.80,"Medium","P-125",2,"2000-4000","Remove starter motor. Replace starter clutch assembly. Check starter gear teeth.","Honda Activa,TVS Jupiter"),
        ("Bike","Bike","bike stalling when coming to stop at traffic signal","Idle Jet Blocked in Carburetor","",0.79,"Medium","P-123",1,"500-1500","Remove and disassemble carburetor. Clean idle jet and pilot jet passages. Reassemble and tune.","Hero Splendor,Bajaj CT"),
        ("Bike","Bike","Royal Enfield making thud noise from engine","RE Engine Primary Chain Tensioner Wear","",0.81,"Medium","P-119",2,"2000-4000","Adjust or replace primary chain tensioner. Check primary chain stretch. Replace if needed.","Royal Enfield Classic,Royal Enfield Bullet"),
        ("Bike","Bike","bike headlight flickering while riding","Bike Voltage Regulator Rectifier Fault","",0.80,"Medium","P-122",1,"1000-2000","Test regulator rectifier output voltage. Replace if output erratic. Check stator coil also.","Bajaj Pulsar,Yamaha FZ,TVS Apache"),
        ("Car","Engine","diesel car producing white smoke on cold start then stops","Diesel Cold Start Normal or Glow Plug Slow","P0380",0.72,"Low","P-026",1,"1000-2000","Check glow plug operation and pre-heat time. Replace slow heating glow plugs. Check fuel quality.","Mahindra Bolero,Tata Nexon Diesel"),
        ("Car","Engine","engine making grinding noise from accessory belt area","Idler Pulley Bearing Failure","",0.80,"Medium","P-017",1,"800-1500","Identify noisy pulley by removing belt and spinning each. Replace failed idler or tensioner pulley.","Maruti Swift,Hyundai i20,Honda City"),
        ("Car","Electrical","reverse camera not working black screen when reversing","Reverse Camera Wiring or Unit Failure","",0.78,"Low","P-061",1,"1500-3000","Check camera power and video signal wiring. Replace camera unit if faulty. Check head unit input.","Hyundai Creta,Kia Seltos,Tata Nexon"),
        ("Car","Electrical","keyless entry not working remote not responding","Key Fob Battery Dead or Antenna Issue","",0.82,"Low","P-065",0.5,"200-1000","Replace key fob battery. If still not working check car antenna module. Re-pair key fob.","Hyundai Creta,Kia Seltos,Tata Harrier"),
        ("SUV","Suspension","rear end swaying on highway at high speed","Rear Shock Absorbers Worn on SUV","",0.82,"High","P-071",3,"4000-8000","Replace both rear shock absorbers. Check rear sway bar links. Test drive for stability.","Toyota Fortuner,Mahindra Scorpio,Tata Safari"),
        ("SUV","Steering","steering heavy at low speed parking","Power Steering Fluid Level Low","",0.78,"Low","P-104",0.5,"400-800","Check and top up power steering fluid. Inspect for leaks at pump hoses and rack.","Mahindra Scorpio,Toyota Innova"),
        ("Truck","Truck/Commercial","truck jake brake not working retarder fault","Engine Brake Solenoid Failure","",0.80,"Medium","P-132",3,"5000-10000","Test engine brake solenoid valves. Check ECU signal. Replace failed solenoid.","Ashok Leyland,Eicher Pro,BharatBenz"),
        ("Truck","Truck/Commercial","heavy vehicle air pressure building slowly","Air Compressor Governor Fault","",0.82,"High","P-132",3,"6000-12000","Test air governor cut-in and cut-out pressures. Replace governor if out of spec. Check compressor valves.","Tata 407,Ashok Leyland Dost"),
        ("Car","Body","wiper blades leaving streaks not clearing properly","Wiper Blade Rubber Worn","",0.88,"Low","P-149",0.25,"300-600","Replace wiper blade inserts or complete blade assembly. Clean windshield surface.","Universal"),
        ("Car","Body","door not closing properly latch not catching","Door Striker Plate Misaligned","",0.79,"Low","P-114",0.5,"300-800","Adjust door striker plate position. Tighten mounting bolts. Check door hinge condition.","Maruti Alto,Hyundai i10"),
        ("Car","Fuel System","petrol smell inside car cabin","Fuel Tank Breather or Charcoal Canister Issue","P0440",0.78,"Medium","P-091",2,"2000-4000","Check charcoal canister and purge valve. Inspect fuel tank breather line. Replace if saturated.","Maruti Swift,Hyundai i20"),
        ("Car","Engine","car failing emission test high CO or HC","Catalytic Converter Efficiency Low","P0420",0.82,"High","P-093",3,"8000-15000","Check catalyst efficiency. Replace catalytic converter. Also check O2 sensors and fuel system.","Maruti Swift,Honda City,Hyundai i20"),
        ("Car","Transmission","noise from gearbox in neutral that goes away with clutch pressed","Gearbox Input Shaft Bearing Noise","",0.79,"High","P-036",8,"8000-15000","Noise in neutral disappearing with clutch = input bearing. Remove gearbox. Replace bearing.","Maruti Swift,Hyundai i20"),
        ("Bike","Bike","motorcycle engine overheating in traffic","Bike Engine Oil Level Low or Degraded","",0.80,"Medium","P-139",0.5,"500-1000","Check and top up engine oil. If oil dark and old do full oil change. Check for oil leaks.","Bajaj Pulsar,TVS Apache,Yamaha FZ"),
        ("Bike","Bike","bike side stand sensor not allowing start","Side Stand Switch Malfunction","",0.82,"Low","P-061",0.5,"300-600","Check side stand switch connector. Clean or replace switch. Some bypass with jumper wire.","Bajaj Pulsar,KTM Duke,Yamaha R15"),
        ("Bike","Bike","bike exhaust making loud popping sound on deceleration","Exhaust Valve or Leak at Header","",0.76,"Low","P-094",1,"800-2000","Check exhaust header gasket and tighten clamps. If aftermarket exhaust check fitment.","Royal Enfield,KTM Duke,Bajaj Pulsar"),
    ]
    
    for entry in composite_additions:
        vtype, system, symptom, fault, obd, conf, sev, parts, time_h, cost, fix, vehicles = entry
        rows.append([f"F{fid:04d}", vtype, system, symptom, fault, obd, conf, sev, parts, time_h, cost, fix, vehicles])
        fid += 1
    
    # Write CSV
    filepath = os.path.join(DATA_DIR, "vehicle_faults.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FAULT_HEADERS)
        writer.writerows(rows)
    
    print(f"[OK] vehicle_faults.csv generated: {len(rows)} entries")
    return len(rows)

def generate_spare_parts():
    """Generate spare parts CSV."""
    headers = ["part_id","part_name","category","compatible_vehicles","unit_price","supplier_part_number","min_stock_level","weight_kg"]
    filepath = os.path.join(DATA_DIR, "spare_parts.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for p in PARTS_DATA:
            writer.writerow(list(p))
    print(f"[OK] spare_parts.csv generated: {len(PARTS_DATA)} entries")

def generate_vehicles_db():
    """Generate vehicles database CSV."""
    headers = ["vehicle_id","make","model","variant","year_range","engine_type","engine_cc","common_issues"]
    filepath = os.path.join(DATA_DIR, "vehicles_db.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for v in VEHICLES_DATA:
            writer.writerow(list(v))
    print(f"[OK] vehicles_db.csv generated: {len(VEHICLES_DATA)} entries")

def generate_template_csvs():
    """Create template CSVs for runtime data."""
    templates = {
        "mechanics.csv": ["mechanic_id","name","phone","specialization","status","current_jobs","skill_level","telegram_chat_id"],
        "dealers.csv": ["dealer_id","name","phone","email","parts_category","location","delivery_time_days","rating","telegram_chat_id"],
        "jobcards.csv": ["jobcard_id","vehicle_make","vehicle_model","vehicle_year","vehicle_reg","owner_name","owner_phone","complaint","diagnosis_fault","diagnosis_confidence","assigned_mechanic_id","assigned_mechanic_name","status","required_parts","estimated_time","estimated_cost","actual_cost","priority","bay_number","created_at","updated_at","completed_at"],
        "orders.csv": ["order_id","part_id","part_name","quantity","dealer_id","dealer_name","jobcard_id","status","order_date","expected_delivery","actual_delivery","total_cost"],
        "pipeline.csv": ["pipeline_id","mechanic_id","mechanic_name","jobcard_id","task_description","priority","status","start_time","estimated_end","actual_end"],
        "inventory.csv": ["part_id","part_name","category","current_stock","min_stock_level","unit_price","last_restocked","location_in_garage"],
    }
    
    for filename, headers in templates.items():
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            # Pre-populate inventory from parts
            if filename == "inventory.csv":
                for p in PARTS_DATA:
                    part_id, name, cat, _, price, _, min_stock, _ = p
                    stock = random.randint(max(0, min_stock - 1), min_stock + 5) if min_stock > 0 else 0
                    writer.writerow([part_id, name, cat, stock, min_stock, price, "2025-01-01", f"Rack-{cat[:3].upper()}"])
    
    print(f"[OK] Template CSVs generated: {', '.join(templates.keys())}")

if __name__ == "__main__":
    print("=" * 60)
    print("  Nova AI - Dataset Generator")
    print("=" * 60)
    total = generate_vehicle_faults()
    generate_spare_parts()
    generate_vehicles_db()
    generate_template_csvs()
    print("=" * 60)
    print(f"  All datasets generated successfully!")
    print(f"  Total fault entries: {total}")
    print(f"  Spare parts: {len(PARTS_DATA)}")
    print(f"  Vehicles: {len(VEHICLES_DATA)}")
    print(f"  Data directory: {DATA_DIR}")
    print("=" * 60)
