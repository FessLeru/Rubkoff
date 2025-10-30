"""FSM states for the bot"""
from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    """States for user interaction"""
    # Initial state
    start = State()
    
    # House selection states
    area_input = State()
    floors_input = State()
    budget_input = State()
    preferences_input = State()
    confirmation = State()
    
    # Contact states
    contact_name = State()
    contact_phone = State()
    contact_email = State()

class SurveyStates(StatesGroup):
    """States for house selection survey"""
    waiting_for_start = State()
    in_progress = State()
    area_question = State()
    floors_question = State()
    budget_question = State()
    preferences_question = State()
    processing = State()
    showing_results = State()
    finished = State()

class BroadcastStates(StatesGroup):
    """States for admin broadcast"""
    waiting_for_content = State()
    confirmation = State()
    sending = State()

class CatalogStates(StatesGroup):
    """States for catalog management"""
    updating = State()
    confirming_update = State()
    viewing_house = State()
    editing_house = State() 