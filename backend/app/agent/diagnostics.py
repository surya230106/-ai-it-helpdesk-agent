"""Small, deterministic diagnostic trees. Each turn asks for one result and branches on it."""
import re

def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower()).strip()

def is_answer_to_check(message: str, state: dict) -> bool:
    return bool(state.get("active") and state.get("current_diagnostic_step"))

def _check(key: str, action: str, expected: str, choices: list[str]):
    return {"key": key, "action": action, "expected": expected, "choices": choices, "question": "Which result do you see?"}

def _sync_diagnostic_state(state: dict) -> dict:
    check = state.get("current_diagnostic_step") or {}
    state.update({
        "domain": state.get("issue_domain"), "issue": state.get("issue_type"),
        "possible_causes": state.get("likely_causes", []), "questions": check.get("choices", []),
        "current_step": check.get("action"), "expected_result": check.get("expected"),
        "next_step_if_yes": check.get("next_step_if_yes"), "next_step_if_no": check.get("next_step_if_no"),
        "steps_already_tried": list(dict.fromkeys(state.get("steps_already_tried", []) + state.get("failed_steps", []) + state.get("successful_steps", []))),
    })
    return state

def identify_hardware(text: str) -> str | None:
    profiles = [
        ("camera", ("camera", "webcam")), ("gpu", ("gpu", "graphics card", "nvidia", "amd graphics", "intel graphics")),
        ("bluetooth", ("bluetooth",)), ("microphone", ("microphone", "mic ")),
        ("audio", ("sound", "audio", "speaker", "headphone")), ("battery", ("battery", "charging", "charger")),
        ("touchpad", ("touchpad", "trackpad")), ("keyboard", ("keyboard",)), ("mouse", ("mouse",)),
        ("usb", ("usb",)), ("hdmi", ("hdmi", "external monitor")), ("display", ("screen", "display", "flicker", "black screen")),
        ("ethernet", ("ethernet", "network adapter")), ("fan", ("fan",)), ("ram", ("ram", "memory usage")),
        ("ssd", ("ssd", "hard drive", "disk usage", "drive not detected")),
    ]
    return next((name for name, terms in profiles if any(term in text for term in terms)), None)

def start_diagnostic(issue: str, domain: str) -> dict:
    text = issue.lower()
    hardware = identify_hardware(text)
    windows_version = "Windows 11" if "windows 11" in text else "Windows 10" if "windows 10" in text else None
    state = {"active": True, "issue_domain": domain, "issue_type": issue[:500], "device": "laptop" if "laptop" in text else "printer" if "printer" in text else "desktop" if "desktop" in text else None, "hardware": hardware, "platform": windows_version or ("Windows" if "windows" in text else None), "windows_version": windows_version, "symptoms": [issue[:300]], "likely_causes": [], "checked_conditions": {}, "failed_steps": [], "successful_steps": [], "steps_already_tried": [], "confidence": "low", "current_diagnostic_step": None, "next_best_action": None, "escalation_needed": False, "turn": 0}
    if hardware and not state["device"] and "desktop" not in text:
        state["device"] = "laptop"
    if domain == "Printer":
        state["likely_causes"] = ["stuck print job", "wrong printer selected", "printer status or error"]
        if any(x in text for x in ["connected", "online", "ready"]):
            state["current_diagnostic_step"] = _check("printer_queue", "Open Start > Settings > Bluetooth & devices > Printers & scanners. Select your printer, then Open print queue.", "You should see waiting documents, an empty list, or an error.", ["A. A document is waiting", "B. The list is empty", "C. There is an error"])
        else:
            state["current_diagnostic_step"] = _check("printer_status", "Open Start > Settings > Bluetooth & devices > Printers & scanners. Find your printer and read its status.", "It should say Ready, Offline, or show an error.", ["A. Ready", "B. Offline", "C. An error"])
    elif domain == "Network":
        state["likely_causes"] = ["a wider network outage", "a problem limited to this device", "a website or DNS lookup problem"]
        if any(x in text for x in ["adapter missing", "adapter not detected", "wifi adapter", "wi-fi adapter", "network adapter"]):
            key, action, choices = "network_adapter", "Right-click Start > Device Manager > Network adapters. Check whether the Wi-Fi adapter is listed and whether it has a yellow warning.", ["A. Listed with no warning", "B. Yellow warning", "C. Adapter is missing"]
        elif "vpn" in text:
            key, action, choices = "vpn_base_internet", "Disconnect the VPN for this check and open a familiar website.", ["A. The website opens", "B. It still does not open", "C. I cannot disconnect the VPN"]
        elif "dns" in text:
            key, action, choices = "dns_scope", "Try opening one other familiar website, such as your organization home page.", ["A. Other sites open", "B. No sites open", "C. I see an error"]
        elif "ethernet" in text:
            key, action, choices = "ethernet_scope", "Check whether another device on the same network can open a website.", ["A. It works", "B. It also fails", "C. No other device is available"]
        else:
            key, action, choices = "other_devices", "On a phone connected to the same Wi-Fi, try opening a familiar website.", ["A. It opens", "B. It does not open", "C. No other device is available"]
            if any(x in text for x in ["other devices work", "phone works", "only this laptop", "only my laptop"]):
                state["checked_conditions"]["other_devices"] = "User reports other devices work."
                key, action, choices = "this_device_sites", "On the affected computer, try opening two different familiar websites.", ["A. Both open", "B. Neither opens", "C. Only one opens"]
        state["current_diagnostic_step"] = _check(key, action, "This tells us whether the issue is shared by the network or limited to this device.", choices)
    elif domain == "Windows" and any(x in text for x in ["slow", "sluggish", "performance"]):
        state["likely_causes"] = ["an update still working in the background", "one app using too much computer power", "low free storage"]
        state["current_diagnostic_step"] = _check("task_manager", "Press Ctrl + Shift + Esc to open Task Manager. Look at CPU, Memory, and Disk.", "One number staying near 100% may show what is slowing the computer.", ["A. CPU is near 100%", "B. Memory is near 100%", "C. Disk is near 100%", "D. None is high", "E. Task Manager will not open"])
    elif domain == "Windows" and any(x in text for x in ["cpu", "disk usage", "memory usage", "ram high"]):
        state["likely_causes"] = ["an app or Windows task may be using too much of that resource", "the high use may be temporary"]
        state["current_diagnostic_step"] = _check("task_manager", "Press Ctrl + Shift + Esc to open Task Manager. Select Processes and click the CPU, Memory, or Disk heading that is high.", "The app or process using the most should move to the top of that list.", ["A. One app is at the top", "B. A Windows process is at the top", "C. No number is high now", "D. Task Manager will not open"])
    elif domain == "Windows" and any(x in text for x in ["not starting", "won't start", "will not start", "no power", "startup problem"]):
        state["likely_causes"] = ["the laptop may not be receiving power", "Windows may be failing to start", "a hardware problem is possible"]
        state["current_diagnostic_step"] = _check("startup_power", "Connect the charger to a known working outlet. Check for a power light and whether the screen shows a logo. Do not open the laptop.", "A power light or startup logo shows that the laptop is receiving power.", ["A. Power light and logo appear", "B. Power light but no picture", "C. No power light"])
    elif domain == "Windows" and any(x in text for x in ["restarting unexpectedly", "restarts unexpectedly", "unexpected restart", "shuts down unexpectedly"]):
        state["likely_causes"] = ["an update, app, or driver may be causing the restart", "overheating or a hardware problem is also possible"]
        state["current_diagnostic_step"] = _check("restart_pattern", "Note when it restarts, whether the laptop feels unusually hot, and any blue-screen stop code. Save work before using it again.", "The timing, heat, or stop code helps show whether Windows or hardware may be involved.", ["A. It shows a stop code", "B. It feels unusually hot", "C. It restarts without a message"])
    elif domain == "Windows" and any(x in text for x in ["driver", "device manager"]):
        state["likely_causes"] = ["Windows may report a problem with a device or its driver", "a recent update may have affected the device"]
        state["current_diagnostic_step"] = _check("driver_device", "Right-click Start > Device Manager. Find the affected device and check whether it has a yellow warning sign.", "The device should appear without a warning, show a warning, or be missing.", ["A. Listed with no warning", "B. Yellow warning", "C. Device is missing"])
    elif domain == "Windows" and "blue screen" in text:
        state["likely_causes"] = ["a driver or update problem", "a hardware fault"]
        state["current_diagnostic_step"] = _check("blue_screen_code", "If the blue screen appears again, write down the STOP CODE shown near the bottom. Do not force a restart while Windows is updating.", "The STOP CODE is a short label that helps IT identify what failed.", ["A. I have a stop code", "B. It restarted too quickly", "C. It has not happened again"])
    elif domain == "Windows" and "update" in text:
        state["likely_causes"] = ["Windows is still completing an update", "an update or driver caused a problem"]
        state["current_diagnostic_step"] = _check("windows_update_status", "Open Start > Settings > Windows Update and read the status. Do not turn off the computer while it says it is installing.", "It should say up to date, installing, or ask for a restart.", ["A. Still installing", "B. Restart required", "C. Up to date", "D. An error is shown"])
    elif domain == "Windows" and any(x in text for x in ["crash", "freez", "not opening", "application", "app "]):
        state["likely_causes"] = ["a problem limited to the app", "a recent app update or damaged file", "a wider Windows issue"]
        state["current_diagnostic_step"] = _check("app_scope", "Tell me the app name and whether it closes immediately or only after you choose a particular action.", "This tells us whether the app itself or one task is triggering the problem.", ["A. Closes as soon as it opens", "B. Closes after one action", "C. Several apps are affected", "D. There is an error message"])
    elif domain in {"Email"}:
        state["likely_causes"] = ["an Outlook app issue", "a connection or mail service issue", "a message stuck in Outbox"]
        state["current_diagnostic_step"] = _check("email_web", "Open your company email in a web browser and try to view your inbox. Do not send the same message again yet.", "If web email works, the problem is more likely limited to Outlook on this computer.", ["A. Web email works", "B. It also fails", "C. I see an error"])
    elif domain == "Browser":
        state["likely_causes"] = ["a browser extension or saved site data", "a problem with one website", "a wider network issue"]
        state["current_diagnostic_step"] = _check("browser_other", "Try opening one familiar website in a different browser, if one is installed.", "If it opens there, the issue is probably limited to the first browser.", ["A. It opens", "B. It also fails", "C. No other browser is available"])
    elif domain == "Login & Access":
        state["likely_causes"] = ["a sign-in error or account lock", "a network or VPN requirement", "access permission"]
        state["current_diagnostic_step"] = _check("login_error", "Read the sign-in message and tell me its wording. Do not send a password or MFA code.", "The message can show whether this is a connection, account, or permission problem.", ["A. Account locked", "B. Access denied", "C. Network/VPN message", "D. Another message"])
    elif domain == "Hardware":
        check = None
        if hardware == "camera":
            state["likely_causes"] = ["camera permission is off", "another app is using the camera", "the camera or its driver is not detected"]
            if any(x in text for x in ["permission is on", "access is on", "already on"]):
                state["current_diagnostic_step"] = _check("camera_app_test", "Close video-call apps you are not using. Open the Windows Camera app and check whether it shows a picture.", "A picture in Camera means the device works and the first app needs checking.", ["A. Camera app shows a picture", "B. Camera app has an error", "C. No picture"])
            else:
                state["current_diagnostic_step"] = _check("camera_permission", "Open Start > Settings > Privacy & security > Camera. Check that Camera access is on.", "Camera access should be on. Also check whether your app is allowed to use the camera.", ["A. Camera access is off", "B. It is on and allowed", "C. Camera is missing from settings"])
        elif hardware == "gpu":
            state["likely_causes"] = ["Windows may not be detecting the graphics card", "the driver may need attention", "the app may be using the built-in graphics"]
            state["current_diagnostic_step"] = _check("gpu_device", "Right-click Start > Device Manager > Display adapters. Read the names shown and look for a yellow warning sign.", "You may see NVIDIA/AMD/Intel graphics, only one graphics device, or a warning sign.", ["A. The expected graphics card is listed", "B. Only Intel or basic display is listed", "C. A yellow warning sign appears", "D. Display adapters is missing"])
        elif hardware == "bluetooth":
            state["likely_causes"] = ["Bluetooth may be off", "the accessory may need to connect again", "Windows may not see the Bluetooth device"]
            state["current_diagnostic_step"] = _check("bluetooth_status", "Open Start > Settings > Bluetooth & devices. Check whether Bluetooth is shown and turned on.", "You should see a Bluetooth switch and your accessory in the device list.", ["A. Bluetooth is on", "B. Bluetooth is off", "C. The Bluetooth option is missing"])
        elif hardware == "microphone":
            state["likely_causes"] = ["microphone access may be off", "the wrong microphone may be selected", "the microphone or its driver may need checking"]
            state["current_diagnostic_step"] = _check("microphone_privacy", "Open Start > Settings > Privacy & security > Microphone. Check that microphone access is on for the app.", "Microphone access should be on for both the device and the app.", ["A. Access was off", "B. Access is on", "C. The microphone is not listed"])
        elif hardware == "audio":
            state["likely_causes"] = ["sound may be muted", "Windows may be using a different speaker or headset", "the audio device may need checking"]
            state["current_diagnostic_step"] = _check("sound_output", "Click the speaker icon near the clock. Check mute, volume, and which speaker or headset is selected.", "The intended speaker or headset should be selected and not muted.", ["A. It was muted", "B. The wrong device was selected", "C. Settings look right", "D. No speaker is listed"])
        elif hardware == "battery":
            state["likely_causes"] = ["the charger or outlet may not be supplying power", "battery wear or a charging fault may be involved"]
            if any(x in text for x in ["drain", "short battery", "dies quickly", "battery life"]):
                state["current_diagnostic_step"] = _check("battery_drain", "Open Start > Settings > System > Power & battery and check Battery usage for an app using a lot of power.", "The page should show which apps used the most battery.", ["A. One app is using a lot", "B. No app stands out", "C. Battery usage is missing"])
            else:
                state["current_diagnostic_step"] = _check("battery_charge", "Check that the charger is firmly connected at both ends and try a different wall outlet. Stop if the battery looks swollen or smells unusual.", "The charging light or Windows battery icon should show charging. A swollen battery needs urgent support.", ["A. It is charging now", "B. Still not charging", "C. Battery looks swollen or smells unusual"])
        elif hardware in {"keyboard", "mouse", "touchpad"}:
            state["likely_causes"] = ["the device may be turned off or disconnected", "a setting or device driver may be involved", "the device may need repair"]
            if hardware == "touchpad":
                check = _check("touchpad_test", "Open Start > Settings > Bluetooth & devices > Touchpad and check whether the Touchpad switch is on.", "The Touchpad switch should be on. A separate mouse can help compare.", ["A. It was off", "B. It is on", "C. Touchpad is missing"])
            else:
                check = _check("input_test", f"If this is a separate {hardware}, reconnect it or check its battery. If it is built in, try a separate {hardware} if one is available.", "A separate device can show whether the problem is with the built-in part or Windows.", ["A. It works after reconnecting", "B. A separate device works", "C. Neither works", "D. I cannot test another"])
            state["current_diagnostic_step"] = check
        elif hardware in {"usb", "hdmi", "ethernet"}:
            state["likely_causes"] = ["the connection or accessory may be the cause", "the port or device driver may need checking"]
            what = "USB device" if hardware == "usb" else "HDMI cable and screen" if hardware == "hdmi" else "network cable"
            state["current_diagnostic_step"] = _check(f"{hardware}_connection", f"Disconnect and reconnect the {what}. If possible, try a different port or cable. Do not force the plug.", "The device should appear or work when the connection is good.", ["A. It works now", "B. Still not detected", "C. I cannot try another port or cable"])
        elif hardware == "ram":
            state["likely_causes"] = ["an app may be using much of the computer's memory", "several open apps may be using more memory than available"]
            state["current_diagnostic_step"] = _check("memory_usage", "Press Ctrl + Shift + Esc to open Task Manager. Select Processes, then click the Memory heading.", "The apps using the most memory should move to the top of the list.", ["A. One app is using most memory", "B. Several apps use a lot", "C. Memory is not high", "D. Task Manager will not open"])
        elif hardware == "fan":
            state["likely_causes"] = ["heavy app use may make the fan run faster", "blocked airflow or a cooling problem may be involved"]
            state["current_diagnostic_step"] = _check("heat_safety", "Place the laptop on a hard, flat surface with vents clear. Check whether it stays unusually hot or shuts down.", "It should stay on and cool down. Do not open the laptop.", ["A. Fan quiets and laptop cools", "B. Fan stays loud or laptop stays hot", "C. It shuts down"])
        elif hardware == "ssd":
            state["likely_causes"] = ["Windows may not be seeing the drive", "the drive may need attention", "a connection or hardware problem is possible"]
            state["current_diagnostic_step"] = _check("drive_visible", "Right-click Start > Disk Management. Look for the drive without changing or formatting anything.", "The drive may appear with a size and a status, or it may be missing.", ["A. The drive appears", "B. It is missing", "C. Windows asks to initialize or format it"])
        elif "overheat" in text or "hot" in text:
            state["likely_causes"] = ["blocked airflow", "heavy computer use", "a cooling or battery fault"]
            check = _check("heat_safety", "Place the laptop on a hard, flat surface with its vents clear. Check whether it remains very hot or shuts down.", "It should cool down and stay on. If it remains very hot or shuts down, stop using it and contact support.", ["A. It is cooling down", "B. Still very hot", "C. It shut down", "D. Battery looks swollen"])
            state["current_diagnostic_step"] = check
        elif hardware == "display" or any(x in text for x in ["screen", "display", "black"]):
            state["likely_causes"] = ["power or brightness", "a dock or external display", "a display or graphics fault"]
            check = _check("display_power", "Check that the laptop has power and turn brightness up. If a dock or external screen is connected, unplug it.", "The built-in screen should show an image or sign-in screen.", ["A. Picture returned", "B. I can see a startup logo only", "C. Still black", "D. No power light"])
            state["current_diagnostic_step"] = check
        else:
            state["likely_causes"] = ["a connection or battery issue", "a device or hardware fault"]
            check = _check("hardware_connection", "Reconnect the device or check its battery if it uses one. For a built-in laptop part, tell me whether an external one works.", "The device should respond after it is reconnected or powered.", ["A. It works now", "B. Still does not work", "C. No external device to test"])
            state["current_diagnostic_step"] = check
        if check and not state["current_diagnostic_step"]:
            state["current_diagnostic_step"] = check
    elif domain == "Storage":
        state["likely_causes"] = ["temporary files or personal files using most of the drive", "a drive that needs IT review"]
        if any(x in text for x in ["not detected", "missing", "not showing"]):
            state["current_diagnostic_step"] = _check("drive_visible", "Right-click Start > Disk Management. Look for the drive without changing or formatting anything.", "The drive may appear with a size and a status, or it may be missing.", ["A. The drive appears", "B. It is missing", "C. Windows asks to initialize or format it"])
        else:
            state["current_diagnostic_step"] = _check("storage_space", "Open Start > Settings > System > Storage and check how much free space is shown.", "You should see how many GB are free and which part of the drive is using space. Do not delete system folders.", ["A. Less than 1 GB free", "B. 1-10 GB free", "C. More than 10 GB free", "D. Settings will not open"])
    elif domain == "Security":
        state["likely_causes"] = ["a suspicious message or file may put the account or device at risk"]
        state["current_diagnostic_step"] = _check("security_exposure", "Do not open the link or file again. Tell me only whether you clicked it or entered a password. Never send the password or an MFA code.", "Knowing whether anything was opened helps IT choose a safe response.", ["A. I did not click it", "B. I clicked or opened it", "C. I entered a password", "D. Not sure"])
    elif domain == "Software":
        state["likely_causes"] = ["the file may need a different app", "the app may not support this file", "the file may be damaged"]
        if "install" in text:
            check = _check("software_install", "Read the installer error and tell me its exact wording. Do not turn off security or download the installer from an unknown site.", "The exact message may identify a missing requirement or permission.", ["A. Permission message", "B. Missing requirement", "C. Another error", "D. No message"])
        else:
            check = _check("file_open", "Look at the file name ending, such as .pdf or .docx, and tell me which app you are using to open it.", "The file ending shows what kind of file it is and which app should open it.", ["A. PDF", "B. Word document", "C. Another type", "D. I cannot see the ending"])
        state["current_diagnostic_step"] = check
    else:
        state["likely_causes"] = ["an app, setting, or device-specific problem"]
        state["current_diagnostic_step"] = _check("scope", "Tell me whether this affects one app/device or more than one, and share the exact error if there is one.", "This helps separate a local problem from a wider service issue.", ["A. One app or device", "B. Several apps or devices", "C. There is an error message"])
    state["next_best_action"] = state["current_diagnostic_step"]["action"]
    return _sync_diagnostic_state(state)

def diagnose_network_issue(issue: str) -> dict: return start_diagnostic(issue, "Network")
def diagnose_printer_issue(issue: str) -> dict: return start_diagnostic(issue, "Printer")
def diagnose_windows_performance(issue: str) -> dict: return start_diagnostic(issue, "Windows")
def diagnose_login_issue(issue: str) -> dict: return start_diagnostic(issue, "Login & Access")
def diagnose_browser_issue(issue: str) -> dict: return start_diagnostic(issue, "Browser")
def diagnose_email_issue(issue: str) -> dict: return start_diagnostic(issue, "Email")
def diagnose_hardware_issue(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_wifi(issue: str) -> dict: return start_diagnostic(issue, "Network")
def diagnose_bluetooth(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_camera(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_gpu(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_storage(issue: str) -> dict: return start_diagnostic(issue, "Storage")
def diagnose_battery(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_audio(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_display(issue: str) -> dict: return start_diagnostic(issue, "Hardware")
def diagnose_windows(issue: str) -> dict: return start_diagnostic(issue, "Windows")
def diagnose_printer(issue: str) -> dict: return start_diagnostic(issue, "Printer")
DIAGNOSTIC_TOOLS = {
    "diagnose_network_issue": diagnose_network_issue,
    "diagnose_printer_issue": diagnose_printer_issue,
    "diagnose_windows_performance": diagnose_windows_performance,
    "diagnose_login_issue": diagnose_login_issue,
    "diagnose_browser_issue": diagnose_browser_issue,
    "diagnose_email_issue": diagnose_email_issue,
    "diagnose_hardware_issue": diagnose_hardware_issue,
    "diagnose_wifi": diagnose_wifi,
    "diagnose_bluetooth": diagnose_bluetooth,
    "diagnose_camera": diagnose_camera,
    "diagnose_gpu": diagnose_gpu,
    "diagnose_storage": diagnose_storage,
    "diagnose_battery": diagnose_battery,
    "diagnose_audio": diagnose_audio,
    "diagnose_display": diagnose_display,
    "diagnose_windows": diagnose_windows,
    "diagnose_printer": diagnose_printer,
    "diagnose_issue": start_diagnostic,
}

def _selected_answer(message: str, check: dict | None = None) -> str:
    answer = re.match(r"^\s*([a-e])(?:[.)\s]|$)", message.lower())
    t = normalize(message)
    if (len(t) == 1 and t in "abcde" or answer) and check:
        label = answer.group(1) if answer else t
        selected = next((choice[3:].strip() for choice in check.get("choices", []) if choice[:1].lower() == label), "")
        return selected or message
    return message

def _result(message: str, check: dict | None = None) -> str:
    t = normalize(_selected_answer(message, check))
    if any(x in t for x in ["does not work", "doesn t work", "not work", "also fails", "still black", "still hot", "still does not", "still doesn t"]): return "no"
    if any(x in t for x in ["ready", "works", "opens", "cooling", "picture returned", "it was muted", "selected", "disappeared", "printed", "charging light is on"]): return "yes"
    if any(x in t for x in ["offline", "error", "locked", "access denied", "100", "near 100"]): return "error"
    if any(x in t for x in ["empty", "no document", "nothing waiting"]): return "empty"
    if any(x in t for x in ["stuck", "waiting", "queued"]): return "stuck"
    if t in {"a", "yes", "yep", "yeah", "no", "nope"}: return "yes" if t in {"a", "yes", "yep", "yeah"} else "no"
    return t

def continue_diagnostic(state: dict, message: str) -> tuple[dict, dict]:
    """Record the answer to the current check, then return a diagnosis and next single action."""
    check = state.get("current_diagnostic_step") or {}
    key = check.get("key", "unknown")
    result = _result(message, check)
    facts = state.setdefault("checked_conditions", {})
    facts[key] = message[:300]
    state.setdefault("steps_already_tried", []).append(key)
    state["turn"] = state.get("turn", 0) + 1
    if result == "no": state.setdefault("failed_steps", []).append(key)
    if result == "yes": state.setdefault("successful_steps", []).append(key)
    message = _selected_answer(message, check)

    domain = state.get("issue_domain")
    if any(x in normalize(message) for x in ["fixed", "working now", "it works now", "solved"]):
        state["active"] = False
        state["current_diagnostic_step"] = None
        _sync_diagnostic_state(state)
        return state, {"likely_cause": "The issue appears to be fixed", "confidence": "high", "explanation": "You confirmed it is working now.", "next_check": None, "expected": "The problem should remain resolved."}

    if domain == "Printer":
        if key == "printer_status":
            if "offline" in normalize(message) or result in {"error", "no"}:
                cause = "The printer is offline or showing an error, so print jobs may not be reaching it."
                action = "Check the printer display for its exact message and confirm it is powered on."
                choices = ["A. It now says Ready", "B. Still Offline", "C. There is an error message"]
                next_check = _check("printer_error", action, "A Ready status means it can receive print jobs.", choices)
            else:
                cause = "The printer says Ready, so it can receive jobs. A waiting print job may be blocking new work."
                next_check = _check("printer_queue", "Open Start > Settings > Bluetooth & devices > Printers & scanners. Select your printer, then Open print queue.", "You should see either waiting documents, an empty list, or an error.", ["A. A document is waiting", "B. The list is empty", "C. There is an error"])
        elif key in {"printer_queue", "printer_queue_result"}:
            if result == "stuck" or any(x in normalize(message) for x in ["waiting", "stuck", "queued"]):
                cause = "A print job is waiting in the queue and may be holding up the others."
                next_check = _check("cancel_stuck_job", "In the queue, select only the document you recognize as stuck and choose Cancel.", "That one document should disappear from the queue. Then we can test printing once.", ["A. It disappeared", "B. It will not cancel", "C. I do not recognize the document"])
            elif result == "empty" or "empty" in normalize(message):
                cause = "The printer queue is empty, so a stuck job is unlikely. Windows may be sending the document to another printer."
                next_check = _check("selected_printer", "Open the document's Print window and read the printer name shown before you print.", "The selected name should match the printer you are standing near.", ["A. The name matches", "B. It is a different printer", "C. I cannot find the name"])
            elif result == "yes" or "ready" in normalize(message):
                cause = "Ready means the printer can receive jobs, but it does not tell us whether a document is waiting in the queue."
                next_check = _check("printer_queue", "Open the printer's queue and look at the documents listed there.", "You should see a waiting document, an empty list, or an error.", ["A. A document is waiting", "B. The list is empty", "C. There is an error"])
            else:
                cause = "The queue shows an error. Its wording will tell us whether the printer or a job needs attention."
                next_check = _check("printer_error_text", "Read the queue or printer message and share its wording. Do not include private document contents.", "The exact message should point to the next safe check.", ["A. I can share the message", "B. No message is shown"])
        elif key == "cancel_stuck_job":
            if result == "yes" or "disappeared" in normalize(message):
                cause = "The stuck document is gone, so it was blocking the queue. A test page will confirm the printer can print again."
                next_check = _check("test_page", "Open the printer's queue window and choose Printer > Print Test Page.", "A test page should come out without using the app or document that first failed.", ["A. Test page printed", "B. It did not print", "C. There is an error"])
            else:
                cause = "The stuck document could not be removed, so the queue may need help from IT. Do not cancel documents you do not recognize."
                state["escalation_needed"] = True; next_check = None
        elif key == "test_page":
            if result == "yes" or "printed" in normalize(message):
                cause = "The test page printed, so the printer and its connection work. The original app or printer selection is now more likely."
                next_check = _check("original_print", "Try printing the original document once, after confirming the correct printer is selected.", "The document should print now.", ["A. It printed", "B. It is still waiting", "C. There is an error"])
            else:
                cause = "The test page did not print, so this is not limited to the original document or app. The printer or its connection may need support."
                state["escalation_needed"] = True
                next_check = _check("escalate_printer", "Note the printer model, its exact status message, and whether another person can print to it.", "These details help IT decide whether the printer or computer needs repair.", ["A. Other people can print", "B. Nobody can print", "C. Hardware error is shown"])
        elif key == "selected_printer":
            if any(x in normalize(message) for x in ["different", "wrong"]):
                cause = "The document was set to a different printer, which explains why nothing came out of the nearby printer."
                next_check = _check("select_correct_printer", "In the Print window, select the printer you are standing near and print one page.", "The page should come out of that printer.", ["A. It printed", "B. Still did not print", "C. Printer is not listed"])
            else:
                cause = "The selected name appears to match. A test page can tell whether the printer itself can print."
                next_check = _check("test_page", "Open the printer's queue window and choose Printer > Print Test Page.", "A test page should come out without using the original document.", ["A. Test page printed", "B. It did not print", "C. There is an error"])
        else:
            cause = "The printer is not completing a basic test, so its status or connection needs a closer check."
            next_check = _check("escalate_printer", "Please note the printer model, its exact display message, and whether another person can print to it.", "These details let support tell whether this is a printer fault or a computer setup issue.", ["A. Other people can print", "B. Nobody can print", "C. Hardware error is shown"])
    elif domain == "Network":
        if key == "network_adapter":
            t = normalize(message)
            if "warning" in t or "yellow" in t:
                cause = "The Wi-Fi adapter is listed with a warning, so Windows sees a device or driver problem."
                next_check = _check("network_adapter_status", "Open the Wi-Fi adapter's Properties in Device Manager and read Device status. Do not uninstall it.", "The status should say the adapter is working or show an error code.", ["A. It is working", "B. Error code shown", "C. I cannot find status"])
            elif "missing" in t or "not listed" in t:
                cause = "The Wi-Fi adapter is not listed, so Windows may not be detecting it. It could be disabled, missing a driver, or have a hardware problem."
                next_check = _check("network_adapter_hidden", "In Device Manager, open View > Show hidden devices and check Network adapters again.", "The adapter may appear faintly, appear normally, or remain missing.", ["A. It appeared", "B. Still missing", "C. I see a warning"])
            else:
                cause = "Windows lists the adapter without a warning, so its connection setting or wireless network may be involved."
                next_check = _check("wifi_status", "Click the network icon near the clock and check whether Wi-Fi is turned on and connected to your network.", "Wi-Fi should be on and show the network name.", ["A. Connected", "B. Wi-Fi is off", "C. A warning is shown"])
        elif key in {"network_adapter_status", "network_adapter_hidden"}:
            if any(x in normalize(message) for x in ["warning", "error", "missing", "still missing"]):
                cause = "Windows still reports a Wi-Fi adapter problem, so IT should check its driver and hardware."
                state["escalation_needed"] = True; next_check = None
            else:
                cause = "The adapter is listed without a warning, so check that Wi-Fi is on and connected before checking internet access."
                next_check = _check("wifi_status", "Click the network icon near the clock and check whether Wi-Fi is on and connected.", "Wi-Fi should be on and show the network name.", ["A. Connected", "B. Wi-Fi is off", "C. A warning is shown"])
        elif key == "wifi_status":
            t = normalize(message)
            if "off" in t or "disconnected" in t:
                cause = "Wi-Fi is off or disconnected, which explains why the laptop cannot reach the network."
                next_check = _check("wifi_turn_on", "Turn Wi-Fi on and select your usual network. Enter the password only in Windows, never in this chat.", "The network should show Connected.", ["A. Connected now", "B. It will not connect", "C. My network is missing"])
            else:
                cause = "Wi-Fi shows connected, but we still need to check whether internet access works."
                next_check = _check("other_devices", "On a phone connected to the same Wi-Fi, try opening a familiar website.", "This tells us whether the problem affects the whole network or only this laptop.", ["A. It opens", "B. It does not open", "C. No other device is available"])
        elif key == "other_devices":
            if result == "yes" or "opens" in normalize(message) or "works" in normalize(message):
                cause = "Another device can get online, so the router and internet service are less likely to be the cause. The problem may be limited to this computer."
                next_check = _check("this_device_sites", "On the affected computer, try opening two different familiar websites.", "If both fail, we will check the computer's network settings. If only one fails, that site may be the problem.", ["A. Both open", "B. Neither opens", "C. Only one opens"])
            elif result == "no" or "does not" in normalize(message) or "also" in normalize(message):
                cause = "Other devices also cannot get online, so this is more likely a shared Wi-Fi, router, or internet service problem than a laptop fault."
                next_check = _check("shared_network", "Check whether the router shows an Internet warning light. Do not reset it yet.", "A warning light or outage message supports a shared network problem.", ["A. Warning light or outage", "B. No warning", "C. I cannot check"])
            elif "no other device" in normalize(message):
                cause = "We cannot compare another device, so we will check what the affected computer reports directly."
                next_check = _check("wifi_status", "Click the network icon near the clock and read whether Wi-Fi says Connected or shows a warning.", "Connected means the computer joined Wi-Fi; a warning may explain why it cannot get online.", ["A. Connected", "B. Disconnected", "C. A warning is shown"])
            else:
                cause = "We still need to tell whether the issue affects the whole Wi-Fi network or only this computer."
                next_check = _check("other_devices", "Try one other device on the same Wi-Fi and tell me whether a website opens.", "This separates a shared network issue from a computer-specific one.", ["A. It opens", "B. It does not", "C. No other device"])
        elif key == "this_device_sites":
            if result == "no" or "neither" in normalize(message):
                cause = "Other devices work but websites fail on this computer, which points to a computer-specific setting such as DNS or VPN."
                next_check = _check("vpn_proxy", "If a work VPN is connected, disconnect it briefly if your workplace allows that, then try one website.", "If the site opens, the VPN connection is involved. If not, we will check name lookup next.", ["A. It opens now", "B. Still fails", "C. I cannot disconnect VPN"])
            else:
                cause = "At least one website opens, so the connection works. The trouble may be limited to one website or app."
                next_check = _check("one_site", "Try the website that failed in a different browser.", "If it opens there, the first browser is likely the cause.", ["A. It opens", "B. Still fails"])
        elif key == "dns_scope":
            if result == "yes" or "other sites open" in normalize(message):
                cause = "Other websites open, so the internet connection works. The first website or its saved address may be the problem."
                next_check = _check("dns_one_site", "Try opening the same site on another device on this network.", "If it fails there too, the website may be the cause. If it works, the issue is on this device.", ["A. Works on other device", "B. Fails on other device", "C. No other device"])
            else:
                cause = "No websites open on this device, so we need to compare it with another device before assuming DNS is the cause."
                next_check = _check("other_devices", "Try opening a familiar website on another device on the same network.", "If that device works, the issue is limited to this computer.", ["A. It works", "B. It also fails"])
        elif key == "vpn_base_internet":
            cause = "This check compares normal internet with the VPN connection."
            next_check = _check("vpn_error", "Reconnect the VPN once and read the exact error, if one appears. Never share a password or MFA code.", "The error should tell us whether this is sign-in or service connectivity.", ["A. It connected", "B. Sign-in error", "C. Connection error"])
        else:
            cause = "We need one more result to tell whether this is a device setting or shared network issue."
            next_check = _check("other_devices", "Try a website on another device using the same Wi-Fi.", "If that device works, we will focus on this computer.", ["A. Works", "B. Fails"])
    elif domain == "Windows" and key == "driver_device":
        t = normalize(message)
        if "warning" in t or "yellow" in t:
            cause = "A yellow warning means Windows has found a device or driver problem. The device status message will give more detail."
            next_check = _check("driver_status", "Open that device's Properties in Device Manager and read Device status. Do not uninstall the driver.", "The status should say the device is working or show an error code.", ["A. Device is working", "B. Error code is shown", "C. I cannot find the status"])
        elif "missing" in t:
            cause = "The device is missing from Device Manager, so Windows is not currently seeing it. It may be disabled, disconnected, or have a hardware issue."
            next_check = _check("driver_hidden", "In Device Manager, open View > Show hidden devices and check that device group again.", "The device may appear faintly, appear normally, or remain missing.", ["A. It appeared", "B. Still missing", "C. I see a warning"])
        else:
            cause = "The device is listed without a warning, so the issue may be in its setting or the app using it."
            next_check = _check("driver_app_scope", "Test the device in one other approved app or Windows setting.", "If it works there, the first app is more likely the cause.", ["A. Works elsewhere", "B. Fails everywhere"])
    elif domain == "Windows" and key in {"restart_pattern", "restart_update", "heat_safety"}:
        t = normalize(message)
        if "hot" in t or "shut down" in t:
            cause = "The laptop feels unusually hot, so overheating may be causing the shutdown. Stop using it if it is very hot."
            next_check = _check("restart_heat_check", "Place it on a hard surface with vents clear. If it stays very hot or shuts down, turn it off and contact IT.", "It should cool down and stay on.", ["A. It cools down", "B. Still very hot", "C. It shuts down"])
            if "still very hot" in t or "shut down" in t:
                state["escalation_needed"] = True; next_check = None
        elif "stop code" in t or "blue screen" in t:
            cause = "The stop code shows Windows hit a serious error. The code and time will help IT identify what failed."
            state["escalation_needed"] = True; next_check = None
        elif "update" in t or "matches the date" in t:
            cause = "The restart began after an update, so the update may be related. IT should review the update and device status before any rollback."
            state["escalation_needed"] = True; next_check = None
        else:
            cause = "The restart has no visible error, so update history and timing may help find whether Windows or an app started it."
            next_check = _check("restart_update", "Open Settings > Windows Update > Update history and note whether an update was installed just before restarts began.", "A recent update may match when the restarts started.", ["A. An update matches the date", "B. No recent update", "C. I cannot open Update history"])
    elif domain == "Windows" and key == "startup_power":
        t = normalize(message)
        if "no power" in t or "no power light" in t:
            cause = "There is no power light with the charger connected, so the outlet, charger, or laptop power hardware may need checking."
            next_check = _check("startup_adapter", "Try one other known-working wall outlet and check the charger light. Do not open the laptop or force the connector.", "A charger light or laptop power light should come on if power is reaching it.", ["A. A light comes on", "B. Still no light"])
        elif "no picture" in t or "power light but" in t:
            cause = "The laptop has power but no picture, so the display or Windows startup may be involved."
            next_check = _check("startup_display", "Press the brightness-up key a few times and disconnect any dock or external display. Check whether the built-in screen shows a logo.", "A startup logo means the screen works before Windows loads.", ["A. Logo appears", "B. Still black"])
        else:
            cause = "The laptop receives power and shows a logo, so Windows may be having trouble starting."
            next_check = _check("startup_windows", "Wait a minute at the logo or sign-in screen. If an update message is shown, let it finish and do not force power off.", "Windows should reach the sign-in screen or show an error message.", ["A. Sign-in screen appears", "B. It stays on the logo", "C. An error appears"])
    elif domain == "Windows" and key in {"driver_status", "driver_hidden", "driver_app_scope"}:
        t = normalize(message)
        if "warning" in t or "error" in t or "missing" in t or "still missing" in t:
            cause = "Windows still reports a device or driver problem, so IT should review the device status and recent changes."
            state["escalation_needed"] = True; next_check = None
        else:
            cause = "The device is listed without a warning, so the original app or its setting is more likely than a missing driver."
            next_check = _check("driver_app_test", "Test the device once in the app or Windows setting where the problem started.", "It should work there if the issue was temporary.", ["A. It works now", "B. It still fails"])
    elif domain == "Windows" and key == "task_manager":
        if result == "yes" or "100" in normalize(message):
            resource = "CPU" if "cpu" in normalize(message) else "Memory" if "memory" in normalize(message) else "Disk"
            cause = f"{resource} use is very high, which can make Windows feel slow. A program or background update may be using it."
            next_check = _check("high_resource_app", f"In Task Manager, click the {resource} heading once to sort by highest use. Read the name at the top.", "The busiest app or process should appear at the top of that column.", ["A. A familiar app is at the top", "B. Windows Update is at the top", "C. An unfamiliar item is at the top"])
        elif result == "no" or "none" in normalize(message):
            cause = "No resource is obviously maxed out, so low storage or background activity may explain the slowdown."
            next_check = _check("update_status", "Open Settings > Windows Update and see whether it says it is still installing or asks for a restart.", "A pending update or restart could help explain the slowdown.", ["A. Update is still working", "B. Restart required", "C. Up to date"])
        else:
            cause = "We need to see which part of the computer is busy before choosing a fix."
            next_check = state["current_diagnostic_step"]
    elif domain == "Email" and key == "email_web":
        if result == "yes" or "works" in normalize(message):
            cause = "Web email works, so your account and mail service are probably okay. Outlook on this computer is the more likely cause."
            next_check = _check("outlook_outbox", "In Outlook, check whether the message is still in Outbox and note any error shown at the top.", "A message still in Outbox or an error points to an Outlook sending problem.", ["A. Message is in Outbox", "B. No message there", "C. There is an error"])
        else:
            cause = "Web email also fails, so this may involve the account, network, or mail service rather than only Outlook."
            next_check = _check("email_error", "Read the web email error message. Do not share your password or MFA code.", "The message can show whether to check sign-in or contact the mail administrator.", ["A. Sign-in error", "B. Service error", "C. No error shown"])
    elif domain == "Browser" and key == "browser_other":
        if result == "yes" or "opens" in normalize(message):
            cause = "The site opens in another browser, so the network works and the first browser is more likely involved."
            next_check = _check("browser_private", "In the browser that fails, open a Private or Incognito window and try the same site.", "If it works there, an extension or saved site data is likely involved.", ["A. It opens", "B. Still fails"])
        else:
            cause = "The site also fails in another browser, so this may be a network or website problem rather than one browser."
            next_check = _check("browser_scope", "Try one different website in either browser.", "If other sites open, the original website may be having a problem.", ["A. Other sites open", "B. No sites open"])
    elif domain == "Login & Access" and key == "login_error":
        t = normalize(message)
        if any(x in t for x in ["locked", "account locked"]):
            cause = "The account is locked, so the password may be correct but sign-in is blocked. An administrator must unlock it."
            state["escalation_needed"] = True; next_check = None
        elif "denied" in t or "permission" in t:
            cause = "Access is being denied by the service. This usually needs an administrator to check your permission."
            state["escalation_needed"] = True; next_check = None
        elif "network" in t or "vpn" in t:
            cause = "The message points to a network or VPN requirement rather than a wrong password."
            next_check = _check("login_vpn", "Connect to your organization's VPN if required, then try the portal once more.", "The sign-in page should load without the network warning.", ["A. Page loads", "B. Same warning", "C. New error"])
        else:
            cause = "The wording of the sign-in error is needed to tell whether this is an account or service issue."
            next_check = _check("login_exact_error", "Copy the error wording without including any password or MFA code.", "The message should identify the next safe check.", ["A. Account message", "B. Network message", "C. Other message"])
    elif domain == "Security" and key == "security_exposure":
        if any(x in normalize(message) for x in ["entered a password", "entered password", "clicked", "opened it"]):
            cause = "A suspicious link or file was opened, so IT should review the device or account promptly. Do not enter more information on that page."
            state["escalation_needed"] = True; next_check = None
        else:
            cause = "You did not open the suspicious item, which lowers the immediate risk. It should still be reported using your organization's reporting button."
            next_check = _check("security_report", "Use your organization's Report Phishing button or forward the message to its security team.", "You should see a confirmation that the message was reported.", ["A. Reported", "B. I cannot find the report option"])
    elif domain == "Windows" and key == "windows_update_status":
        t = normalize(message)
        if "install" in t or "restart" in t:
            cause = "Windows is still finishing an update or waiting for a restart, which can temporarily slow the computer."
            next_check = _check("update_finish", "Save your work. If Windows asks for a restart, restart once and let it finish without turning the computer off.", "After the update completes, the computer should return to the sign-in screen.", ["A. Update completed and speed improved", "B. Still slow", "C. Update shows an error"])
        else:
            cause = "Windows reports it is up to date, so an update still running is less likely. A busy app or low storage may be involved."
            next_check = _check("task_manager", "Press Ctrl + Shift + Esc and check whether CPU, Memory, or Disk stays near 100%.", "A high number can point to what is slowing the computer.", ["A. CPU high", "B. Memory high", "C. Disk high", "D. None high"])
    elif domain == "Hardware" and key == "camera_permission":
        t = normalize(message)
        if "missing" in t or "not listed" in t:
            cause = "Camera access is not listed in Settings, so Windows may not be seeing the camera or its driver."
            next_check = _check("camera_device", "Right-click Start > Device Manager and look under Cameras. Tell me whether the camera is listed or has a yellow warning.", "The camera should appear by name, or Windows may show a warning or no camera.", ["A. Camera is listed", "B. Yellow warning", "C. No camera listed"])
        elif "off" in t:
            cause = "Camera access was off, which can stop Windows apps from using the camera."
            next_check = _check("camera_toggle", "Turn Camera access on, then make sure access is allowed for the app you use. Open that app and test the camera once.", "The app should show a picture from the camera.", ["A. Camera works", "B. Still does not work", "C. App is not listed"])
        else:
            cause = "Camera access is on, so the app permission, another app, or the camera itself may be involved."
            next_check = _check("camera_app_test", "Close video-call apps you are not using. Open the Windows Camera app and check whether it shows a picture.", "A picture in Camera means the device works and the first app needs checking.", ["A. Camera app shows a picture", "B. Camera app has an error", "C. No picture"])
    elif domain == "Hardware" and key == "camera_device":
        t = normalize(message)
        if "warning" in t:
            cause = "The camera appears with a warning, which makes a driver or device problem more likely."
            next_check = _check("camera_warning", "Open the camera entry in Device Manager and read the Device status message. Do not uninstall it.", "The status should give an error message or say the device is working properly.", ["A. It says device is working", "B. It shows an error", "C. I cannot find the status"])
        elif "no camera" in t or "missing" in t:
            cause = "Windows does not list the camera, so it may be disabled, disconnected, or not detected. A built-in camera may need IT service."
            state["escalation_needed"] = True; next_check = None
        else:
            cause = "Windows lists the camera, so checking its status will show whether a driver error is present."
            next_check = _check("camera_warning", "Open the camera entry in Device Manager and read the Device status message. Do not uninstall it.", "The status should say the device is working or show an error.", ["A. It is working", "B. There is an error"])
    elif domain == "Hardware" and key == "gpu_device":
        t = normalize(message)
        if "yellow" in t or "warning" in t:
            cause = "The graphics card is listed with a warning, so Windows has detected a problem with it or its driver."
            next_check = _check("gpu_warning", "Open the graphics card entry in Device Manager and read the Device status message. Do not uninstall the driver.", "The status message should show whether Windows reports an error.", ["A. Device is working", "B. An error is shown", "C. I cannot find status"])
        elif "only intel" in t or "basic display" in t or "missing" in t:
            cause = "The expected graphics card is not listed by name. Windows may not be detecting it, or its driver may be missing."
            next_check = _check("gpu_hidden", "In Device Manager, open View > Show hidden devices and look under Display adapters again.", "The graphics card may appear faintly, appear normally, or remain missing.", ["A. It appeared", "B. Still missing", "C. I see a warning"])
        else:
            cause = "Windows lists the graphics card, so we can check whether the app is using it before suspecting a fault."
            next_check = _check("gpu_task_manager", "Open Task Manager > Performance while the affected app is running. Look for GPU activity under the graphics card name.", "GPU activity should rise while the app is doing graphics work.", ["A. The expected GPU is active", "B. Another GPU is active", "C. No GPU activity shown"])
    elif domain == "Hardware" and key == "battery_drain":
        if "one app" in normalize(message):
            cause = "One app is using much of the battery, which may explain the fast drain."
            next_check = _check("battery_app", "Save your work, then close that app if you do not need it and check whether battery use slows.", "The battery percentage should fall more slowly during light use.", ["A. It drains more slowly", "B. Still drains quickly"])
        else:
            cause = "No single app explains the drain, so battery health or background Windows work may be involved."
            next_check = _check("battery_health", "Search Start for Windows Security or your laptop maker's support app and check for a battery health report. Do not install an unknown tool.", "The report may show whether battery capacity has worn down.", ["A. Report says battery is healthy", "B. Report shows a problem", "C. No report is available"])
    elif domain == "Hardware" and key in {"bluetooth_status", "microphone_privacy", "sound_output", "battery_charge", "touchpad_test", "input_test", "usb_connection", "hdmi_connection", "ethernet_connection", "memory_usage", "drive_visible", "gpu_warning", "gpu_hidden", "gpu_task_manager", "camera_toggle", "camera_app_test", "camera_warning", "microphone_test", "sound_test", "input_followup", "storage_drive_followup"}:
        t = normalize(message)
        if key == "bluetooth_status":
            if "off" in t:
                cause = "Bluetooth was off, which stops wireless accessories from connecting."
                next_check = _check("bluetooth_turn_on", "Turn Bluetooth on in Settings > Bluetooth & devices, then try connecting the accessory once.", "The accessory should show as connected.", ["A. It connected", "B. It is on but will not connect", "C. Bluetooth will not turn on"])
            elif "missing" in t or "not shown" in t:
                cause = "Bluetooth is missing from Settings, so Windows may not be seeing its adapter or driver."
                next_check = _check("bluetooth_device", "Right-click Start > Device Manager. Look under Bluetooth and note whether an adapter or warning is shown.", "You should see an adapter, a warning, or no Bluetooth section.", ["A. Adapter is listed", "B. Yellow warning", "C. Bluetooth is missing"])
            else:
                cause = "Bluetooth is on, so the accessory pairing or its battery may be the cause."
                next_check = _check("bluetooth_pair", "Check that the accessory is charged and shown in Settings > Bluetooth & devices. Select it and choose Connect if available.", "The accessory should show Connected.", ["A. It connected", "B. It is not listed", "C. It still will not connect"])
        elif key == "microphone_privacy":
            if "off" in t:
                cause = "Microphone access was off, so Windows was blocking apps from using it."
                next_check = _check("microphone_toggle", "Turn microphone access on for the device and the app, then make a short test recording.", "The test should show a moving sound level or play back your voice.", ["A. Test works", "B. Still no sound", "C. Microphone is missing"])
            elif "missing" in t:
                cause = "The microphone is not listed in Settings, so Windows may not be detecting its device or driver."
                state["escalation_needed"] = True; next_check = None
            else:
                cause = "Microphone access is on, so the selected input or the app may be the cause."
                next_check = _check("microphone_test", "Open Settings > System > Sound > Input and speak. Check whether the input level moves.", "The input level should move when you speak.", ["A. Level moves", "B. No movement", "C. No microphone listed"])
        elif key == "battery_charge":
            if any(x in t for x in ["swollen", "smell", "unusual"]):
                cause = "A swollen battery or unusual smell can signal a dangerous battery fault. Stop using and charging the laptop."
                state["escalation_needed"] = True; next_check = None
            elif "charging now" in t or "charging" in t:
                cause = "The charging indicator is on, so power is reaching the laptop. Battery wear may explain fast drain."
                next_check = _check("battery_drain", "Unplug the charger briefly and check whether Windows shows the battery percentage falling very quickly during light use.", "A steady drop during light use may point to battery wear or a busy app.", ["A. It drops quickly", "B. It drops slowly", "C. I cannot check"])
            else:
                cause = "The laptop still is not charging after checking the connection, so the charger, port, or battery may need service."
                next_check = _check("charger_check", "If available, check whether the charger light is on and whether this charger works with another compatible laptop. Do not bend or force the plug.", "This can separate a power adapter issue from a laptop charging problem.", ["A. Charger light is off", "B. Charger works elsewhere", "C. No other laptop to test"])
        elif key == "sound_output":
            cause = "The sound is not explained by mute or the selected output, so an app setting, headset, or audio device may be involved."
            next_check = _check("sound_test", "Try a short sound through headphones, if available, then try the built-in speakers.", "Sound through headphones but not speakers points to the speakers; no sound on either points to Windows or the audio device.", ["A. Headphones work", "B. Speakers work", "C. Neither works", "D. No headphones available"])
        elif key == "touchpad_test":
            if "off" in t:
                cause = "The touchpad switch was off, which stops the built-in touchpad from responding."
                next_check = _check("touchpad_toggle", "Turn the Touchpad switch on and move one finger on the touchpad.", "The pointer should move.", ["A. Pointer moves", "B. Still does not move"])
            elif "missing" in t:
                cause = "The touchpad is missing from Settings, so Windows may not be detecting its driver or device."
                state["escalation_needed"] = True; next_check = None
            else:
                cause = "The touchpad setting is on, so comparing with an external mouse will help tell whether the issue is limited to the touchpad."
                next_check = _check("input_followup", "Connect a mouse if available and check whether its pointer moves.", "A working mouse with a failed touchpad points to the built-in touchpad or its driver.", ["A. Mouse works", "B. Mouse also fails", "C. No mouse available"])
        elif key in {"input_test", "input_followup"}:
            if "external" in t or "separate" in t or "mouse works" in t or "keyboard works" in t:
                cause = "The separate device works, so the problem is more likely with the built-in device or its setting."
                next_check = _check("input_device_manager", "Open Device Manager and look under Keyboards or Mice and other pointing devices for a yellow warning.", "The device should appear without a warning, or Windows may show a problem.", ["A. Listed with no warning", "B. Yellow warning", "C. Missing"])
            else:
                cause = "The device still does not respond after reconnecting, so its connection, setting, or driver may need checking."
                next_check = _check("input_device_manager", "Open Device Manager and look under Keyboards or Mice and other pointing devices for a yellow warning.", "The device should appear without a warning, or Windows may show a problem.", ["A. Listed with no warning", "B. Yellow warning", "C. Missing"])
        elif key in {"usb_connection", "hdmi_connection", "ethernet_connection"}:
            if "works" in t or "connected" in t:
                cause = "The connection works after reconnecting, so a loose connection or cable was likely involved."
                next_check = _check("connection_confirm", "Use it briefly in the same way as before and check whether it stays connected.", "It should remain connected without cutting out.", ["A. Stays connected", "B. Disconnects again"])
            else:
                cause = "The device is still not detected after reconnecting, so another cable/port or a Windows device check is needed."
                next_check = _check("connection_other_port", "If safe and available, try one other port or a known working cable. Do not force a connector.", "If it works there, the first port or cable may be the cause.", ["A. Works in another port", "B. Still fails", "C. No other port or cable"])
        elif key == "memory_usage":
            if "one app" in t:
                cause = "One app is using most of the memory, which can leave less room for other apps."
                next_check = _check("memory_app_name", "In Task Manager, note the name of the app at the top of the Memory list. Do not close work you have not saved.", "The app name identifies what is using the memory.", ["A. I can see the app name", "B. It is a Windows process", "C. I cannot tell"])
            else:
                cause = "Several apps or another resource may be using the computer's memory; we need the top app name to narrow it down."
                next_check = _check("memory_app_name", "In Task Manager, note the name of the app at the top of the Memory list.", "The top app is using the most memory at this moment.", ["A. I can see the app name", "B. It is a Windows process", "C. I cannot tell"])
        elif key == "drive_visible":
            if "initialize" in t or "format" in t:
                cause = "Windows is asking to initialize or format the drive. Doing that can erase access to its files, so do not choose either option."
                state["escalation_needed"] = True; next_check = None
            elif "missing" in t:
                cause = "Disk Management does not show the drive, so Windows is not detecting it. The drive, cable, or connection may need IT review."
                state["escalation_needed"] = True; next_check = None
            else:
                cause = "The drive appears in Disk Management, so its status can show whether it is healthy or needs attention."
                next_check = _check("storage_drive_followup", "Read the drive status shown there, but do not initialize, format, or change partitions.", "The status should say Online, Offline, or show an error.", ["A. Online", "B. Offline", "C. It shows an error"])
        elif key in {"gpu_warning", "gpu_hidden", "gpu_task_manager"}:
            if "warning" in t or "error" in t:
                cause = "Windows reports a graphics device warning, so a driver or graphics device issue is likely."
                state["escalation_needed"] = True; next_check = None
            elif "missing" in t:
                cause = "The expected graphics card is still missing, so Windows is not detecting it. IT should check the driver and hardware."
                state["escalation_needed"] = True; next_check = None
            elif "another gpu" in t:
                cause = "The app is using a different graphics device. This alone does not mean the NVIDIA/AMD card is broken."
                next_check = _check("gpu_app_setting", "Open Settings > System > Display > Graphics, select the app, and check its graphics preference without changing it yet.", "The current choice shows which graphics device Windows prefers for that app.", ["A. Power saving", "B. High performance", "C. App is not listed"])
            else:
                cause = "The graphics device appears available, so the next check can tell whether the app is choosing it."
                next_check = _check("gpu_task_manager", "Open Task Manager > Performance while the affected app is running. Look for GPU activity under the graphics card name.", "GPU activity should rise while the app is doing graphics work.", ["A. Expected GPU is active", "B. Another GPU is active", "C. No GPU activity shown"])
        elif key in {"camera_toggle", "camera_app_test", "camera_warning", "microphone_test", "sound_test", "charger_check", "battery_drain", "input_device_manager", "connection_confirm", "connection_other_port", "memory_app_name", "storage_drive_followup", "gpu_app_setting", "bluetooth_turn_on", "bluetooth_pair", "bluetooth_device", "microphone_toggle"}:
            if any(x in t for x in ["warning", "error", "missing", "still fails", "still does not", "will not turn on", "no movement", "neither"]):
                cause = "The safe check did not find a simple setting or connection fix, so a Windows driver or device problem is more likely."
                state["escalation_needed"] = True; next_check = None
            else:
                cause = "The latest check gives us a useful lead. Confirm the device works during normal use before we consider the issue fixed."
                next_check = _check("confirm_working", "Try the device once in the app or situation where the problem first happened.", "It should work as expected and stay connected.", ["A. It works now", "B. The problem remains"])
    elif domain == "Hardware" and key == "heat_safety":
        if result in {"no", "error"} or any(x in normalize(message) for x in ["very hot", "shut down", "swollen"]):
            cause = "The laptop remains too hot or has a possible hardware warning. Continuing to use it could make the problem worse."
            state["escalation_needed"] = True
            next_check = None
        else:
            cause = "Clearing the vents and using a hard surface is helping the laptop cool."
            next_check = _check("heat_repeat", "Leave it on the hard surface for a few minutes, then check whether it stays cool during normal use.", "It should stay on without becoming very hot.", ["A. Stays cool", "B. Gets hot again"])
    elif domain == "Hardware" and key == "sound_output":
        if result == "yes" or "muted" in normalize(message) or "wrong device" in normalize(message):
            cause = "The sound setting was muted or pointed at a different device, which explains why you heard nothing."
            next_check = _check("sound_test", "Play a short sound and check whether it comes from the selected speaker or headset.", "You should hear sound from that device.", ["A. Sound works", "B. Still silent"])
        else:
            cause = "Volume and output selection look correct, so the audio device or driver may need checking."
            next_check = _check("sound_other_app", "Try a short sound in a different app, such as a system notification or another approved app.", "If the other app works, the first app is the likely cause.", ["A. Other app has sound", "B. No sound in either"])
    elif domain == "Hardware" and key == "display_power":
        if result == "yes" or "picture" in normalize(message):
            cause = "The display came back after checking power or removing the dock, so the connection or brightness was likely involved."
            next_check = _check("display_confirm", "Use the laptop briefly without the dock and check whether the picture stays on.", "The picture should remain visible.", ["A. It stays on", "B. Goes black again"])
        else:
            cause = "The screen is still black after the safe power and display checks, so a display or graphics fault is possible."
            state["escalation_needed"] = True
            next_check = None
    else:
        cause = "This answer narrows the problem, but we need one more check before choosing a fix."
        next_check = None

    state["confidence"] = "high" if state["turn"] >= 2 and len(state["checked_conditions"]) >= 2 else "medium"
    state["likely_causes"] = [cause]
    state["current_diagnostic_step"] = next_check
    state["next_best_action"] = next_check["action"] if next_check else None
    _sync_diagnostic_state(state)
    return state, {"likely_cause": cause, "confidence": state["confidence"], "explanation": cause, "next_check": next_check, "expected": next_check["expected"] if next_check else None, "escalation": state["escalation_needed"]}

def first_diagnosis(state: dict) -> dict:
    check = state["current_diagnostic_step"]
    domain = state["issue_domain"]
    issue = state["issue_type"].lower()
    if domain == "Printer" and any(x in issue for x in ["connected", "online", "ready"]):
        cause = "Because the printer is connected, the connection is less likely to be the problem. A waiting print job or a different selected printer may be stopping it."
    elif domain == "Network":
        cause = "The device reports a Wi-Fi connection, but that does not confirm internet access. This check will tell us whether the whole network or only this device is affected."
    elif domain == "Windows" and "slow" in issue:
        cause = "Your computer is running slowly. A busy app, background task, or low free space may be the reason; checking CPU, memory, and disk use will help narrow it down."
    elif domain == "Browser":
        cause = "A browser setting or extension may be stopping it from opening. A second browser will tell us whether the problem is limited to this one app."
    elif domain == "Email":
        cause = "The cause may be Outlook on this computer or the mail service itself. Checking email in a browser will separate those two."
    elif domain == "Login & Access":
        cause = "A locked account, network requirement, or permission may be blocking sign-in. The exact message will tell us which is most likely."
    elif domain == "Storage":
        amount = re.search(r"\b(\d{1,3})\s*%(?=\s|$)", issue)
        if amount and int(amount.group(1)) >= 90:
            cause = f"Your drive is {amount.group(1)}% full, so files and temporary data are using much of its space. This may leave less room for Windows and apps to work."
        elif amount:
            cause = f"Your drive is {amount.group(1)}% full, so about {100-int(amount.group(1))}% is still free. That percentage alone does not show a problem; checking the free space in gigabytes will tell us more."
        else:
            cause = "You said your drive is almost full. Files or temporary data may be using most of its space, leaving less room for Windows and apps. Storage settings will show what is taking space before anything is removed."
    elif domain == "Hardware" and state.get("hardware") == "camera":
        cause = "The camera may be blocked by a privacy setting or app permission. The Windows Camera test will show whether Windows can use it."
    elif domain == "Hardware" and state.get("hardware") == "gpu":
        cause = "Windows may not be detecting the graphics card, or its driver may have a problem. Checking Display adapters will show what Windows sees."
    elif domain == "Hardware" and state.get("hardware") == "bluetooth":
        cause = "Bluetooth may be off or Windows may not see its adapter. The Bluetooth settings page will show whether it is available."
    elif domain == "Hardware" and state.get("hardware") in {"battery", "microphone", "touchpad", "keyboard", "mouse", "usb", "hdmi", "ethernet", "ram", "ssd"}:
        cause = f"The {state['hardware']} problem could come from a setting, connection, or device issue. This check will show which is more likely."
    elif domain == "Hardware" and ("overheat" in issue or "hot" in issue):
        cause = "Blocked airflow or heavy use can make a laptop hot. If it remains very hot or shuts down, a hardware problem is possible."
    elif domain == "Hardware" and any(x in issue for x in ["sound", "audio"]):
        cause = "Sound may be muted or sent to a different speaker. Checking the selected output is the quickest way to tell."
    elif domain == "Hardware":
        cause = "A loose connection, power setting, or hardware fault could explain this. The first check will separate a simple connection issue from a device problem."
    else:
        cause = f"There are a few possible reasons for this {domain.lower()} problem. I need one quick check before I can tell which is most likely."
    return {"likely_cause": cause, "confidence": "low", "explanation": cause, "next_check": check, "expected": check["expected"], "escalation": False}

def format_diagnostic(state: dict, diagnosis: dict) -> str:
    if not state.get("active") and not diagnosis.get("next_check"):
        return "Great, it sounds like the issue is fixed. If it happens again, tell me what you were doing just before it started."
    if diagnosis.get("escalation"):
        return ("WHY THIS IS HAPPENING:\n" + diagnosis["likely_cause"] + "\n\n" +
                "NEXT STEP:\nPlease stop troubleshooting and contact IT support. Tell them what happened and the check you already tried.")
    check = diagnosis.get("next_check") or state.get("current_diagnostic_step")
    if not check:
        return "I do not have enough information to choose a safe next step yet. Please share the exact message you see."
    choices = "\n".join(check["choices"])
    return ("WHY THIS IS HAPPENING:\n" + diagnosis["likely_cause"] + "\n\n" +
            "LET'S CHECK:\n" + check["action"] + "\n\nWHAT YOU SHOULD SEE:\n" + check["expected"] + "\n\n" +
            "TELL ME WHICH ONE:\n" + choices)
