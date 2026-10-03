from app.agent.tools import classify_issue, estimate_priority, detect_intent
from app.agent.agent import _context_question

def test_classify_network():
    assert classify_issue('Wi-Fi is connected but internet is not working') == 'Network'

def test_high_priority():
    assert estimate_priority('All users cannot access the server') == 'high'

def test_domain_and_intent_are_question_specific():
    assert classify_issue('Chrome is not opening') == 'Browser'
    assert classify_issue('The disk is almost full') == 'Storage'
    assert classify_issue('The laptop screen is black') == 'Hardware'
    assert detect_intent('What is the difference between RAM and SSD?') == 'comparison'
    assert detect_intent('How do I clear DNS cache in Windows?') == 'instruction'

def test_followups_keep_last_substantive_issue():
    history = [
        {'role': 'user', 'text': 'My Wi-Fi is not working.'},
        {'role': 'assistant', 'text': 'Check the connection.'},
        {'role': 'user', 'text': 'Still not working.'},
    ]
    assert _context_question(history) == 'My Wi-Fi is not working.'
