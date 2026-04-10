; System Inputs Config -- Unified Input Remapping for Windows 11
;
; Remaps a 3-button Bluetooth ring and Logitech G305 mouse side buttons
; into a keyboard-free voice input, desktop navigation, and app control system.
;
; Ring must be in MUSIC MODE (hold Up+Down until 3 purple flashes).
; Mouse side buttons must be mapped to F16/F17 via G Hub onboard profile.
; G-Shift (DPI held) + side buttons must be mapped to F18/F19.
;
; Ring mapping (Music Mode):
;   Center (Play/Pause)    -> Toggle voice input (Wispr Flow / Ctrl+Win)
;   Up     (Prev Track)    -> Enter (submit prompts)
;   Down   (Next Track)    -> Ctrl+Space (pane manager toggle)
;
; Mouse mapping (F16/F17 via G Hub onboard profile):
;   Side 1 / F16:  Tap = desktop left, Double-tap = pane manager
;   Side 2 / F17:  Tap = desktop right, Double-tap = Enter, Hold = voice PTT
;
; G-Shift mapping (F18/F19 via G Hub onboard profile):
;   G-Shift + Side 1 / F18:  Pane manager toggle
;   G-Shift + Side 2 / F19:  Double-tap Alt
;
; ShareX relay (Windows blocks these combos at OS level):
;   Win+Shift+W -> F13 (capture active window)
;   Win+Shift+A -> F14 (capture region, copy path)
;   Win+Shift+D -> F15 (capture region, save as)

#Requires AutoHotkey v2.0
SendMode "Input"  ; Use SendInput for atomic key injection

; --- Debug logging (disable by setting DEBUG := false) ---
global DEBUG := true
global logFile := DEBUG ? FileOpen(A_ScriptDir "\remap-debug-log.txt", "w") : ""
DbgLog(msg) {
    global logFile, DEBUG
    if !DEBUG
        return
    logFile.Write(FormatTime(, "HH:mm:ss") . "." . Format("{:03}", Mod(A_TickCount, 1000)) . "  " . msg . "`n")
    logFile.Read(0)
}

; ========================================================================
; RING BUTTONS (Bluetooth ring in Music Mode -> media keys)
; ========================================================================

; Center button: MediaPlayPause -> Toggle voice input (e.g. Wispr Flow)
; First tap = double-tap Ctrl+Win (enter hands-free mode)
; Second tap = single tap Ctrl+Win (exit hands-free mode)
; Customize the key combo below for your voice input app.
global wisprActive := false
Media_Play_Pause::{
    global wisprActive
    if wisprActive {
        DbgLog("CENTER DOWN -> sending Ctrl+Win (exit voice input)")
        SendInput "{LCtrl down}{LWin down}{LWin up}{LCtrl up}"
        wisprActive := false
    } else {
        DbgLog("CENTER DOWN -> sending Ctrl+Win x2 (enter voice input)")
        SendInput "{LCtrl down}{LWin down}{LWin up}{LCtrl up}"
        Sleep 200
        SendInput "{LCtrl down}{LWin down}{LWin up}{LCtrl up}"
        wisprActive := true
    }
    KeyWait "Media_Play_Pause"
    DbgLog("CENTER KeyWait released")
}
Media_Play_Pause Up::{
    DbgLog("CENTER UP   -> swallowed")
}

; Swallow power/sleep events from long-press so ring doesn't turn off
*SC15E::return
*SC15E Up::return
*Browser_Home::return
*Browser_Home Up::return

; Up button: MediaPrevTrack -> Enter
Media_Prev::{
    DbgLog("UP DOWN     -> sending Enter")
    SendInput "{Enter}"
}
Media_Prev Up::{
    DbgLog("UP UP       -> swallowed")
}

; Down button: MediaNextTrack -> Ctrl+Space (pane manager toggle)
; Opens/closes pane manager without stealing focus
Media_Next::{
    DbgLog("DOWN DOWN   -> sending Ctrl+Space")
    isPaneMgr := WinActive("Pane Management")
    prevWin := WinGetID("A")
    SendInput "{Ctrl down}{Space}{Ctrl up}"
    if !isPaneMgr {
        Sleep 100
        try WinActivate(prevWin)
    }
}
Media_Next Up::{
    DbgLog("DOWN UP     -> swallowed")
}

; ========================================================================
; SHAREX HOTKEY RELAY
; Windows blocks Win+Shift combos at the OS level.
; AHK intercepts them and relays as virtual F-keys that ShareX listens for.
; F13-F15 have no physical key -- safe to use as relay targets.
; ========================================================================

#+w::SendInput "{F13}"   ; Win+Shift+W -> F13 -> Capture active window
#+a::SendInput "{F14}"   ; Win+Shift+A -> F14 -> Capture region, copy file path
#+d::SendInput "{F15}"   ; Win+Shift+D -> F15 -> Capture region, Save As dialog

; ========================================================================
; MOUSE SIDE BUTTONS (Logitech G305, mapped to F16/F17 via G Hub onboard)
; ========================================================================
;
; Tap/hold/double-tap detection pattern:
;   On press: 300ms KeyWait determines hold vs tap
;   On quick release: 200ms SetTimer window waits for second tap
;   Safe actions (desktop switch) on single tap
;   Deliberate actions (Enter, pane manager) on double-tap
;
; F16 (Side 1, further from thumb):
;   Tap = desktop left, Double-tap = pane manager, Hold = (available)
;
; F17 (Side 2, closer to thumb):
;   Tap = desktop right, Double-tap = Enter, Hold = voice PTT

global f16Held := false
global f17Held := false
global f16TapPending := false
global f17TapPending := false

F16::{
    global f16Held
    f16Held := false
    if !KeyWait("F16", "T0.3") {
        f16Held := true
        DbgLog("F16 HOLD    -> (empty)")
    }
}
F16 Up::{
    global f16Held, f16TapPending
    if f16Held {
        DbgLog("F16 RELEASE -> (empty)")
        f16Held := false
    } else if f16TapPending {
        ; Second tap within window -> double-tap -> Ctrl+Space (pane manager)
        f16TapPending := false
        DbgLog("F16 DOUBLE  -> Ctrl+Space (pane manager)")
        isPaneMgr := WinActive("Pane Management")
        prevWin := WinGetID("A")
        SendInput "{Ctrl down}{Space}{Ctrl up}"
        if !isPaneMgr {
            Sleep 100
            try WinActivate(prevWin)
        }
    } else {
        ; First tap -- wait 200ms for potential second tap
        f16TapPending := true
        SetTimer(F16TapTimeout, -200)
    }
}

F16TapTimeout() {
    global f16TapPending
    if f16TapPending {
        f16TapPending := false
        DbgLog("F16 TAP     -> desktop left")
        SendInput "{LCtrl down}{LWin down}{Left}{LWin up}{LCtrl up}"
    }
}

F17::{
    global f17Held
    f17Held := false
    if !KeyWait("F17", "T0.3") {
        f17Held := true
        DbgLog("F17 HOLD    -> Ctrl+Win down (voice PTT)")
        SendInput "{LCtrl down}{LWin down}"
    }
}
F17 Up::{
    global f17Held, f17TapPending
    if f17Held {
        DbgLog("F17 RELEASE -> Ctrl+Win up (voice PTT end)")
        SendInput "{LWin up}{LCtrl up}"
        f17Held := false
    } else if f17TapPending {
        f17TapPending := false
        DbgLog("F17 DOUBLE  -> Enter")
        SendInput "{Enter}"
    } else {
        f17TapPending := true
        SetTimer(F17TapTimeout, -200)
    }
}

F17TapTimeout() {
    global f17TapPending
    if f17TapPending {
        f17TapPending := false
        DbgLog("F17 TAP     -> desktop right")
        SendInput "{LCtrl down}{LWin down}{Right}{LWin up}{LCtrl up}"
    }
}

; ========================================================================
; G-SHIFT MOUSE BUTTONS (DPI held + side buttons -> F18/F19 via G Hub)
; ========================================================================

; F18: Ctrl+Space (pane manager toggle, with refocus)
F18::{
    DbgLog("F18 -> Ctrl+Space (pane manager)")
    isPaneMgr := WinActive("Pane Management")
    prevWin := WinGetID("A")
    SendInput "{Ctrl down}{Space}{Ctrl up}"
    if !isPaneMgr {
        Sleep 100
        try WinActivate(prevWin)
    }
}

; F19: Double-tap Alt
F19::{
    DbgLog("F19 -> double-tap Alt")
    SendInput "{Alt down}{Alt up}"
    Sleep 200
    SendInput "{Alt down}{Alt up}"
}
