import { toast } from "sonner";

const updateSignal = () => {
  window.dispatchEvent(new Event("mobilecart:live-update"));
  localStorage.setItem("mobilecart-live-update", String(Date.now()));
};

export const hindiFeedback = (message, { announce = true } = {}) => {
  if (navigator.vibrate) navigator.vibrate([22, 32, 22]);
  toast.success(message);
  if (announce && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const voice = new SpeechSynthesisUtterance(message);
    voice.lang = "hi-IN";
    voice.rate = 1.05;
    window.speechSynthesis.speak(voice);
  }
  updateSignal();
};

export const hindiError = (message) => {
  if (navigator.vibrate) navigator.vibrate([70, 40, 70]);
  toast.error(message);
};

// Lightweight Hindi voice + haptic feedback for customer-side clicks (no live-sync signal).
export const speakHindi = (message) => {
  if (navigator.vibrate) navigator.vibrate(24);
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const voice = new SpeechSynthesisUtterance(message);
    voice.lang = "hi-IN";
    voice.rate = 1.06;
    window.speechSynthesis.speak(voice);
  }
};