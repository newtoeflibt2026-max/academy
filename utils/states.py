from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name        = State()
    waiting_for_path        = State()
    waiting_for_target_band = State()
    waiting_for_days        = State()
    waiting_for_name_edit   = State()

class PlacementStates(StatesGroup):
    answering = State()

class LessonStates(StatesGroup):
    viewing_content = State()
    doing_exercise  = State()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()

class CorrectionStates(StatesGroup):
    waiting_for_essay    = State()
    waiting_for_speaking = State()
