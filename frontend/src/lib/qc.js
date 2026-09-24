export const QC_CHECKS = [
  "Battery", "Screen Touch", "Display", "Front Camera", "Back Camera", "Speaker",
  "Microphone", "Wi‑Fi", "Bluetooth", "Charging Port", "Power Button", "Volume Button",
  "Vibrator", "SIM Tray", "Face Sensor", "Copy Screen", "Physical Scratch", "Physical Dent",
];

export const QC_GRADES = [
  { value: "new", label: "Brand New", hi: "बिल्कुल नया" },
  { value: "excellent", label: "Excellent", hi: "बेहतरीन कंडीशन" },
  { value: "good", label: "Good", hi: "अच्छी कंडीशन" },
  { value: "fair", label: "Fair", hi: "ठीक-ठाक कंडीशन" },
];

export const gradeLabel = (value) => QC_GRADES.find((grade) => grade.value === value)?.label || "Brand New";
