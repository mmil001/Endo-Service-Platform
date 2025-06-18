problems_database = {
    "Contamination Detected 🧫": {
        "problem": "Contamination detected by liquid ingress in HS-50F",
        "causes": [
            "Liquid reflux from the patient's abdomen",
            "Insufflator placed below patient level",
            "Level sensor malfunction or fluid detection error"
        ],
        "repairs": [
            "Replace liquid inlet contamination spare parts",
            "Clear contamination mark via software (V1.0 or V2.0 as per section 6.5)",
            "Check and clean level sensor area",
            "Ensure correct equipment height and use of filters",
            "Cross-check with Mindray technical support"
        ]
    },
    "Communication Errors 🔵": {
        "problem": "Internal communication failure between modules",
        "causes": ["Loose cable", "Oxidized socket", "Failing IPC board"],
        "repairs": ["Check connectors", "Reconnect IPC cable", "Replace internal network board"]
    },
    "Heating Errors 🔥": {
        "problem": "Heating malfunction, sensor or plate issue",
        "causes": ["Heating cable disconnected", "Defective heating plate", "Insufflator heating tube failure", "Overtemperature or sensor error (ERR#14, ERR#15)"],
        "repairs": ["Reconnect or replace heating cable (Figure 5-2)", "Replace heating plate (Section 9.15)", "Replace heating insufflation tube", "Check for overtemperature alarm and clear if needed"]
    },
    "Insufflator Errors 🧪": {
        "problem": "Gas flow, valve or pressure sensor issue",
        "causes": ["Defective pinch valve", "Uncalibrated pressure sensor", "Loose tubing"],
        "repairs": ["Recalibrate sensor", "Replace flow valve", "Check CO2 supply and connections"]
    },
    "Insufflation / Flow Errors 🧪": {
        "problem": "Proportional valve, pressure sensor, or flow sensor issue",
        "causes": [
            "Proportional valve out of range or short-circuited",
            "Zero drift in high or low pressure sensor",
            "Mechanical failure of inflation valve",
            "ERR#04 to ERR#12 (flow, pressure, valve state mismatch)"
        ],
        "repairs": [
            "Replace pneumatic module (section 9.6)",
            "Zero calibration of pressure sensor (section 6.2)",
            "Replace main board if sensor faults persist",
            "Use diagnostic mode to verify valve heating or flow output"
        ]
    },
    "Power Supply Errors ⚡": {
        "problem": "Electrical failure or blown fuse",
        "causes": ["Defective AC/DC board", "Blown fuse", "Overload on power board"],
        "repairs": ["Replace fuse", "Check internal power supply", "Inspect power board circuitry"]
    },
    "Image Processor / Camera Errors 🎥": {
        "problem": "Video board failure or no image detected",
        "causes": [
            "CCU board fault",
            "Disconnected camera head",
            "Firmware mismatch",
            "Fault in video signal output module (e.g., HDMI, DVI, SDI)",
            "Abnormal camera configuration parameters"
        ],
        "repairs": [
            "Replace CCU module",
            "Verify camera/cable compatibility",
            "Update firmware (check with KOL)",
            "Use maintenance menu to reset video output settings",
            "Check output signal ports and reconfigure resolution if needed"
        ]
    },
    "Camera Head Errors 🎯": {
        "problem": "Camera head malfunction or improper connection",
        "causes": [
            "Optical coupler disconnected",
            "Camera head cable pin damaged",
            "Internal short-circuit or failed signal transmission"
        ],
        "repairs": [
            "Reconnect or replace the camera head",
            "Inspect cable integrity",
            "Check CCU log for camera detection errors",
            "Perform visual inspection per service manual section 5.3"
        ]
    },
    "Video Recording / USB Errors 💾": {
        "problem": "Failure to record or store images/videos",
        "causes": [
            "USB drive not recognized",
            "File system error",
            "Corrupted recorder board"
        ],
        "repairs": [
            "Use Mindray-approved USB drives",
            "Format USB to FAT32 before use",
            "Replace recording board if detection fails (section 5.3.3)"
        ]
    }
}

patterns = {
    "Contamination Detected 🧫": r"(contamin|liquid.*detected|inlet.*liquid|pollution.*mark|level sensor error|ERR#08)",
    "Communication Errors 🔵": r"(connect.*failed|network.*unreach|ipc.*fail|timeout|socket.*error)",
    "Heating Errors 🔥": r"(heat.*fail|temperature.*alarm|ERR#14|ERR#15|heating plate|tube.*fail)",
    "Insufflator Errors 🧪": r"(flow.*error|pressure.*fail|valve.*fail|ERR#04|gas leak|pinch.*valve)",
    "Insufflation / Flow Errors 🧪": r"(proportional valve|zero drift|ERR#0[4-9]|ERR#1[0-2])",
    "Power Supply Errors ⚡": r"(power.*fail|fuse.*blown|voltage.*error|ERR#06|no power)",
    "Image Processor / Camera Errors 🎥": r"(video.*lost|camera.*error|CCU.*fail|no signal|image.*not found|firmware.*error|hdmi|dvi|sdi.*fail)",
    "Camera Head Errors 🎯": r"(camera head.*error|optical.*fail|coupler|lens|focus.*fail|zoom.*fail|no.*camera.*input)",
    "Video Recording / USB Errors 💾": r"(usb.*fail|record.*error|video.*not saved|no.*recording|file.*system.*error)"
}