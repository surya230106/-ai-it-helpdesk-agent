from app.agent.diagnostics import start_diagnostic, continue_diagnostic, first_diagnosis, format_diagnostic
from app.agent.tools import classify_issue, detect_intent
from app.schemas.helpdesk import ChatIn


def test_printer_ready_and_empty_queue_branches_to_selected_printer():
    state = start_diagnostic("My printer is online but nothing prints", "Printer")
    assert state["current_diagnostic_step"]["key"] == "printer_queue"
    assert len(state["current_diagnostic_step"]["choices"]) <= 5
    state, diagnosis = continue_diagnostic(state, "B")
    assert "queue is empty" in diagnosis["likely_cause"].lower()
    assert state["current_diagnostic_step"]["key"] == "selected_printer"
    assert "print window" in diagnosis["next_check"]["action"].lower()


def test_printer_stuck_job_asks_to_cancel_only_that_job():
    state = start_diagnostic("Printer is not printing", "Printer")
    state, _ = continue_diagnostic(state, "Ready")
    state, diagnosis = continue_diagnostic(state, "A document is waiting")
    assert "waiting in the queue" in diagnosis["likely_cause"]
    assert state["current_diagnostic_step"]["key"] == "cancel_stuck_job"
    assert "only the document" in diagnosis["next_check"]["action"]


def test_ready_status_then_checks_queue_without_guessing_error():
    state = start_diagnostic("My printer is not printing", "Printer")
    state, diagnosis = continue_diagnostic(state, "Ready")
    assert state["current_diagnostic_step"]["key"] == "printer_queue"
    assert "says ready" in diagnosis["likely_cause"].lower()


def test_wifi_other_devices_work_narrows_to_one_device():
    state = start_diagnostic("My Wi-Fi is connected but websites do not load", "Network")
    state, diagnosis = continue_diagnostic(state, "A. It opens")
    assert "limited to this computer" in diagnosis["likely_cause"]
    assert state["current_diagnostic_step"]["key"] == "this_device_sites"


def test_wifi_other_devices_fail_changes_next_check_and_records_result():
    state = start_diagnostic("My Wi-Fi is connected but no internet", "Network")
    first_action = state["current_diagnostic_step"]["action"]
    state, diagnosis = continue_diagnostic(state, "B. It does not open")
    assert state["checked_conditions"]["other_devices"]
    assert state["current_diagnostic_step"]["key"] == "shared_network"
    assert state["current_diagnostic_step"]["action"] != first_action
    assert "shared" in diagnosis["likely_cause"].lower()


def test_printer_test_page_failure_recommends_escalation():
    state = start_diagnostic("Printer not printing", "Printer")
    state, _ = continue_diagnostic(state, "Ready")
    state, _ = continue_diagnostic(state, "A document is waiting")
    state, _ = continue_diagnostic(state, "A. It disappeared")
    state, diagnosis = continue_diagnostic(state, "B. It did not print")
    assert diagnosis["escalation"] is True
    assert state["escalation_needed"] is True


def test_diagnostic_reply_has_one_action_and_expected_result():
    state = start_diagnostic("Windows laptop became slow after update", "Windows")
    diagnosis = first_diagnosis(state)
    answer = format_diagnostic(state, diagnosis)
    assert "WHAT YOU SHOULD SEE" in answer
    assert answer.count("\nA.") <= 1
    assert "Ctrl + Shift + Esc" in answer


def test_diagnostic_scenarios_have_one_combined_explanation():
    cases = [
        ("My Wi-Fi is connected but there is no internet", "Network"),
        ("Printer is online but jobs are stuck in queue", "Printer"),
        ("My disk is almost full", "Storage"),
        ("Windows laptop became very slow after an update", "Windows"),
    ]
    for issue, domain in cases:
        state = start_diagnostic(issue, domain)
        answer = format_diagnostic(state, first_diagnosis(state))
        assert answer.count("WHY THIS IS HAPPENING:") == 1
        assert "WHAT IS HAPPENING?" not in answer
        assert "MOST LIKELY REASON:" not in answer
        assert "LET'S CHECK:" in answer
        assert "WHAT YOU SHOULD SEE:" in answer
        assert answer.count(first_diagnosis(state)["likely_cause"]) == 1
    storage = format_diagnostic(start_diagnostic("My drive is 75% full", "Storage"), first_diagnosis(start_diagnostic("My drive is 75% full", "Storage")))
    assert "75% full" in storage


def test_different_diagnostic_domains_and_intents():
    pairs = [
        ("My Wi-Fi has no internet", "Network"),
        ("My printer will not print", "Printer"),
        ("Outlook freezes when I send email", "Email"),
        ("Chrome will not open", "Browser"),
        ("My laptop has no sound", "Hardware"),
        ("My disk is almost full", "Storage"),
        ("I cannot sign in to the company portal", "Login & Access"),
    ]
    for question, domain in pairs:
        assert classify_issue(question) == domain
        state = start_diagnostic(question, domain)
        assert state["current_diagnostic_step"]["action"]
    assert detect_intent("Why is my printer not printing?") == "diagnosis"


def test_laptop_hardware_issue_matrix_has_specific_safe_first_checks():
    cases = [
        ("Wi-Fi not working", "Network", "other_devices"),
        ("Bluetooth not working", "Hardware", "bluetooth_status"),
        ("Camera not working", "Hardware", "camera_permission"),
        ("NVIDIA GPU not detected", "Hardware", "gpu_device"),
        ("Laptop overheating", "Hardware", "heat_safety"),
        ("Laptop slow", "Windows", "task_manager"),
        ("SSD almost full", "Storage", "storage_space"),
        ("RAM high usage", "Hardware", "memory_usage"),
        ("Battery draining fast", "Hardware", "battery_drain"),
        ("Battery not charging", "Hardware", "battery_charge"),
        ("Keyboard not working", "Hardware", "input_test"),
        ("Touchpad not working", "Hardware", "touchpad_test"),
        ("Mouse not working", "Hardware", "input_test"),
        ("USB not working", "Hardware", "usb_connection"),
        ("HDMI not working", "Hardware", "hdmi_connection"),
        ("Screen flickering", "Hardware", "display_power"),
        ("No sound", "Hardware", "sound_output"),
        ("Microphone not working", "Hardware", "microphone_privacy"),
        ("Windows Update problem", "Windows", "windows_update_status"),
        ("Driver problem", "Windows", "driver_device"),
        ("Application crashing", "Windows", "app_scope"),
        ("Blue Screen", "Windows", "blue_screen_code"),
        ("Printer not working", "Printer", "printer_status"),
        ("VPN not connecting", "Network", "vpn_base_internet"),
        ("Webcam not detected", "Hardware", "camera_permission"),
        ("AMD graphics card not showing", "Hardware", "gpu_device"),
        ("Laptop battery stuck at a percentage", "Hardware", "battery_charge"),
        ("Laptop shuts down on battery", "Hardware", "battery_charge"),
        ("Headphones not detected", "Hardware", "sound_output"),
        ("Ethernet adapter problem", "Network", "ethernet_scope"),
        ("External drive not detected", "Storage", "drive_visible"),
        ("Laptop freezing", "Windows", "app_scope"),
        ("Windows restarting unexpectedly", "Windows", "restart_pattern"),
        ("Laptop not starting", "Windows", "startup_power"),
        ("CPU usage at 100%", "Windows", "task_manager"),
        ("Disk usage at 100%", "Windows", "task_manager"),
        ("Wi-Fi adapter missing", "Network", "network_adapter"),
    ]
    for issue, domain, expected_key in cases:
        actual_domain = classify_issue(issue)
        assert actual_domain == domain, (issue, actual_domain)
        state = start_diagnostic(issue, domain)
        assert state["current_diagnostic_step"]["key"] == expected_key, issue
        assert state["domain"] == domain
        assert state["current_step"] == state["current_diagnostic_step"]["action"]
        reply = format_diagnostic(state, first_diagnosis(state))
        assert reply.count("WHY THIS IS HAPPENING:") == 1
        assert "LET'S CHECK:" in reply and "WHAT YOU SHOULD SEE:" in reply and "TELL ME WHICH ONE:" in reply


def test_camera_and_gpu_answers_change_the_next_check():
    state = start_diagnostic("Camera not working", "Hardware")
    state, diagnosis = continue_diagnostic(state, "Camera access is off")
    assert diagnosis["next_check"]["key"] == "camera_toggle"
    assert state["steps_already_tried"] == ["camera_permission"]

    state = start_diagnostic("NVIDIA GPU not detected", "Hardware")
    state, diagnosis = continue_diagnostic(state, "C")
    assert diagnosis["next_check"]["key"] == "gpu_warning"
    state, diagnosis = continue_diagnostic(state, "It shows error code 43")
    assert diagnosis["escalation"] is True


def test_unsafe_hardware_results_escalate_without_risky_instructions():
    state = start_diagnostic("Battery not charging", "Hardware")
    state, diagnosis = continue_diagnostic(state, "Battery looks swollen")
    answer = format_diagnostic(state, diagnosis)
    assert diagnosis["escalation"] is True
    assert "Stop using and charging" in answer

    state = start_diagnostic("External SSD not detected", "Hardware")
    state, diagnosis = continue_diagnostic(state, "Windows asks to initialize or format it")
    answer = format_diagnostic(state, diagnosis)
    assert diagnosis["escalation"] is True
    assert "do not choose either option" in answer


def test_wifi_adapter_and_startup_followups_use_their_observed_results():
    state = start_diagnostic("Wi-Fi adapter missing", "Network")
    state, diagnosis = continue_diagnostic(state, "B")
    assert diagnosis["next_check"]["key"] == "network_adapter_status"
    state, diagnosis = continue_diagnostic(state, "B")
    assert diagnosis["escalation"] is True

    state = start_diagnostic("Laptop not starting", "Windows")
    state, diagnosis = continue_diagnostic(state, "A")
    assert diagnosis["next_check"]["key"] == "startup_windows"


def test_75_percent_storage_is_not_labeled_as_full():
    state = start_diagnostic("My laptop storage is 75% full", "Storage")
    answer = format_diagnostic(state, first_diagnosis(state))
    assert "about 25% is still free" in answer
    assert "That percentage alone does not show a problem" in answer


def test_slow_windows_reason_does_not_assume_an_update_without_evidence():
    state = start_diagnostic("My Windows laptop is slow", "Windows")
    cause = first_diagnosis(state)["likely_cause"].lower()
    assert "after an update" not in cause
    assert "may be the reason" in cause


def test_chat_schema_accepts_single_letter_choice_answers():
    assert ChatIn(message="A").message == "A"
